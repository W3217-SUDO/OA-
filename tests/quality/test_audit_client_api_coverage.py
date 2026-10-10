import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "client_audit", Path(__file__).resolve().parents[2] / "scripts/audit-client-api-coverage.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class RouterSliceTests(unittest.TestCase):
    def test_client_calls_with_nested_types_are_scanned(self):
        source = 'api.get<Record<string, { id: number }>>("/records")'
        matches = list(AUDIT.CLIENT_CALL.finditer(source))
        self.assertEqual([match.group(3) for match in matches], ["/records"])

    def test_stacked_decorators_keep_registration_order(self):
        source = '''
@router.get(f"{settings.api_prefix}/tasks/{{task_id}}")
@router.api_route(f"{settings.api_prefix}/tasks", methods=["POST", "PUT"])
async def task():
    pass
'''
        self.assertEqual(AUDIT.area_route_entries(source), [
            (["post", "put"], "/tasks"), (["get"], "/tasks/{task_id}")
        ])

    def collect(self, start, stop):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = root / "areas" / "tp" / "router.py"
            router.parent.mkdir(parents=True)
            router.write_text('''
@router.get(f"{settings.api_prefix}/not-mounted")
def hidden(): pass
@router.post(f"{settings.api_prefix}/tasks")
def create(): pass
''', encoding="utf-8")
            source = f'''from app.areas.tp.router import router as task_router
include_route_slice(app, task_router, {start}, {stop})
'''
            return AUDIT.sliced_router_routes(root / "main.py", source)

    def test_only_mounted_slice_satisfies_client_call(self):
        self.assertEqual(self.collect(1, 2), {"post": ["/tasks"]})

    def test_invalid_slice_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Invalid task_router"):
            self.collect(0, 3)

    def test_unresolved_router_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Unresolved area router"):
            AUDIT.sliced_router_routes(Path("main.py"), "include_route_slice(app, unknown, 0, 1)")

    def test_unknown_dynamic_prefix_is_not_silently_ignored(self):
        with self.assertRaisesRegex(AssertionError, "Unsupported dynamic"):
            AUDIT.area_route_entries('@router.get(f"{unknown}/tasks")\ndef tasks(): pass')

    def test_optional_chaining_and_query_string(self):
        self.assertTrue(AUDIT.paths_compatible(
            "/clues/${detail?.id}/workspace?page=1", "/clues/{id}/workspace"
        ))

    def test_filename_suffix_is_preserved(self):
        self.assertTrue(AUDIT.paths_compatible("/pages/${page}.png", "/pages/{number}.png"))
        self.assertFalse(AUDIT.paths_compatible("/pages/${page}.jpg", "/pages/{number}.png"))
        self.assertFalse(AUDIT.paths_compatible("/pages/2.png", "/missing/{number}.png"))

    def test_factory_reexport_uses_only_requested_function(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "app"
            root.mkdir()
            (root / "main.py").write_text("from app.dependencies import make_router\n", encoding="utf-8")
            (root / "dependencies.py").write_text("from app.factory import create_router as make_router\n", encoding="utf-8")
            (root / "factory.py").write_text('''
def unused_router():
    return "must-not-match"
def create_router():
    @router.get("/mounted")
    def endpoint(): pass
    return router
''', encoding="utf-8")
            source = AUDIT.resolve_router_source(root / "main.py", "make_router")
            self.assertIn('/mounted', source)
            self.assertNotIn('must-not-match', source)

    def collect_helpers(self, modules):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "app"
            for name, source in modules.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, encoding="utf-8")
            return AUDIT.sliced_router_routes(root / "main.py", modules["main.py"])

    def test_called_helper_registers_router_alias_with_combined_prefix(self):
        server = self.collect_helpers({
            "main.py": "from app.gateway import install as mount_tools\nmount_tools(app)\n",
            "gateway.py": '''
from app.tools import router as pending_router
def install(application):
    application.include_router(pending_router, prefix=settings.api_prefix + "/gateway")
''',
            "tools.py": '''
router = APIRouter(prefix=settings.api_prefix + "/tools")
@router.get("/requests")
def requests(): pass
@router.get("/requests/{request_id}")
def request(): pass
@router.post("/requests/{request_id}/decision")
def decision(): pass
''',
        })
        self.assertEqual(server, {
            "get": ["/gateway/tools/requests", "/gateway/tools/requests/{request_id}"],
            "post": ["/gateway/tools/requests/{request_id}/decision"],
        })
        self.assertFalse(AUDIT.paths_compatible("/tools/requests", server["get"][0]))

    def test_nested_helper_reexport_relative_alias_and_keyword_application(self):
        server = self.collect_helpers({
            "main.py": "from app.dependencies import initialize as setup\nsetup(target=app)\n",
            "dependencies.py": "from .bootstrap import configure as initialize\n",
            "bootstrap.py": '''
from .gateway import install as mount_tools
def configure(target):
    mount_tools(application=target)
''',
            "gateway.py": '''
from .tools import router as tool_routes
def install(application):
    active = application
    active.include_router(router=tool_routes)
''',
            "tools.py": '''
router = APIRouter(prefix=f"{settings.api_prefix}/tools")
@router.api_route("/mounted", methods=["GET", "POST"])
def endpoint(): pass
''',
        })
        self.assertEqual(server, {"get": ["/tools/mounted"], "post": ["/tools/mounted"]})

    def test_uncalled_helpers_and_different_application_cannot_satisfy_routes(self):
        server = self.collect_helpers({
            "main.py": '''
from app.gateway import install, never_called
install(other_application)
''',
            "gateway.py": '''
from app.tools import router
def install(application):
    application.include_router(router)
def never_called(application):
    application.include_router(router)
''',
            "tools.py": '@router.get("/not-mounted")\ndef hidden(): pass\n',
        })
        self.assertEqual(server, {})

    def test_uncalled_nested_function_does_not_count_as_registration(self):
        server = self.collect_helpers({
            "main.py": "from app.gateway import install\ninstall(app)\n",
            "gateway.py": '''
from app.tools import router
def install(application):
    def unused():
        application.include_router(router)
''',
            "tools.py": '@router.get("/not-mounted")\ndef hidden(): pass\n',
        })
        self.assertEqual(server, {})

    def test_recursive_registration_helper_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Cyclic registration helper"):
            self.collect_helpers({
                "main.py": "from app.gateway import install\ninstall(app)\n",
                "gateway.py": "def install(application):\n    install(application)\n",
            })

    def test_unresolved_helper_router_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Unresolved router symbol"):
            self.collect_helpers({
                "main.py": "from app.gateway import install\ninstall(app)\n",
                "gateway.py": "def install(application):\n    application.include_router(unknown_router)\n",
            })

    def test_combined_dynamic_prefix_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "Missing or unsupported area route"):
            AUDIT.route_path(ast.parse('settings.api_prefix + unknown_prefix').body[0].value)


if __name__ == "__main__":
    unittest.main()

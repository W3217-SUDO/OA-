import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "client_audit", Path(__file__).with_name("audit-client-api-coverage.py")
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class RouterSliceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

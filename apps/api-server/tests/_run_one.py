"""在独立进程中执行没有脚本入口的 unittest 文件。"""

import importlib.util
import inspect
import json
import os
import sys
import unittest
from asyncio import run
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1]).resolve()
    api_root = Path(__file__).resolve().parents[1]
    for source_root in (api_root.parents[1], api_root):
        if str(source_root) not in sys.path:
            sys.path.insert(0, str(source_root))
    spec = importlib.util.spec_from_file_location(path.stem.replace(".", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载测试文件：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("test_") and function.__module__ == module.__name__:
            if inspect.signature(function).parameters:
                raise RuntimeError(f"顶层测试函数必须无参数：{path}:{name}")
            if inspect.iscoroutinefunction(function):
                suite.addTest(unittest.FunctionTestCase(lambda function=function: run(function()), description=name))
            else:
                suite.addTest(unittest.FunctionTestCase(function, description=name))
    excluded_names = set(json.loads(os.environ.get("OA_TEST_EXCLUDED_METHODS", "[]")))
    found: set[str] = set()

    def retain(test_suite: unittest.TestSuite) -> unittest.TestSuite:
        retained = unittest.TestSuite()
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                retained.addTest(retain(test))
                continue
            identifier = f"{type(test).__name__}.{test._testMethodName}" if isinstance(test, unittest.TestCase) else ""
            if identifier in excluded_names:
                found.add(identifier)
            else:
                retained.addTest(test)
        return retained

    suite = retain(suite)
    if found != excluded_names:
        raise RuntimeError(f"声明排除的方法与实际测试不一致：{sorted(excluded_names - found)}")
    if suite.countTestCases() == 0 and not found:
        raise RuntimeError(f"测试文件没有可执行用例：{path}")
    selected = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print("TEST_SELECTION_JSON=" + json.dumps({
        "excluded": sorted(found), "executed": selected - len(result.skipped),
        "skipped": len(result.skipped),
    }))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

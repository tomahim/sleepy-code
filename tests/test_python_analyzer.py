import unittest
from pathlib import Path

from deadcode import PythonAnalyzer


class TestPythonAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/fixtures/python")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def test_unused_standalone_function(self):
        code = """
def unused_function():
    pass

def used_function():
    pass

used_function()
"""
        self._write_test_file("test1.py", code)
        analyzer = PythonAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "test1::unused_function")

    def test_unused_class_method(self):
        code = """
class TestClass:
    def unused_method(self):
        pass

    def used_method(self):
        pass

    def call_method(self):
        self.used_method()
"""
        self._write_test_file("test2.py", code)
        analyzer = PythonAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "test2::TestClass::unused_method")

    def test_imported_function_usage(self):
        module_code = """
def helper_function():
    pass
"""
        usage_code = """
from module import helper_function

def use_helper():
    helper_function()
"""
        self._write_test_file("module.py", module_code)
        self._write_test_file("usage.py", usage_code)
        analyzer = PythonAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 0)

    def test_private_method_usage(self):
        code = """
class TestClass:
    def __init__(self):
        self._private_method()

    def _private_method(self):
        pass
"""
        self._write_test_file("test3.py", code)
        analyzer = PythonAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 0)

    def _write_test_file(self, filename: str, content: str):
        filepath = self.test_dir / filename
        filepath.write_text(content)

    def tearDown(self):
        for file in self.test_dir.glob("*.py"):
            file.unlink()
        self.test_dir.rmdir()


if __name__ == "__main__":
    unittest.main()

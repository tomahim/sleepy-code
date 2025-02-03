import unittest
from pathlib import Path
import os

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

    def test_property_detection(self):
        content = """
    class MyClass:
        @property
        def my_property(self):
            return 42
    """
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        elements = analyzer.analyze_file_content(content, "test.py")
        
        self.assertIn("test::MyClass::my_property", elements)
        self.assertEqual(elements["test::MyClass::my_property"]["type"], "property")

    def test_cached_property_detection(self):
        content = """
    class MyClass:
        @cached_property
        def cached_prop(self):
            return 42
    """
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        elements = analyzer.analyze_file_content(content, "test.py")
        
        self.assertIn("test::MyClass::cached_prop", elements)
        self.assertEqual(elements["test::MyClass::cached_prop"]["type"], "property")

    def test_property_usage_detection(self):
        content = """
    class MyClass:
        @property
        def my_property(self):
            return 42

    class OtherClass:
        def use_it(self):
            obj = MyClass()
            value = obj.my_property  # Property access without parentheses
    """
        filepath = os.path.join(self.test_dir, "test.py")
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        result = analyzer.check_usage(filepath, {
            "name": "test::MyClass::my_property",
            "type": "property",
            "base_name": "my_property"
        })
        
        self.assertIsNotNone(result)

    def test_validator_decorator_exclusion(self):
        content = """
    class MyClass:
        @validator
        def exact_validator(self):
            return 42

        @input_validator_stuff(model="test")
        def prefix_suffix(self):
            return True

        @validator_input
        def prefix(self):
            return True

        @suffix_validator
        def suffix(self):
            return True

        @field_validator("default_value_mode", mode="before")
        @classmethod
        def many_decorators(self):
            return True

        def normal_method(self):
            return 100
    """
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        elements = analyzer.analyze_file_content(content, "test.py")
        
        self.assertNotIn("test::MyClass::exact_validator", elements)
        self.assertNotIn("test::MyClass::prefix_suffix", elements)
        self.assertNotIn("test::MyClass::many_decorators", elements)
        self.assertNotIn("test::MyClass::prefix", elements)
        self.assertNotIn("test::MyClass::suffix", elements)
        self.assertIn("test::MyClass::normal_method", elements)

    def test_nested_function_usage(self):
        content = """
    def outer_function():
        def inner_function():
            return 42
        
        # Using inner function
        result = inner_function()
        return result

    def unused_function():
        def inner_unused():
            return 100
        return 0
    """
        filepath = os.path.join(self.test_dir, "test.py")
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        
        # Test inner_function usage detection
        result = analyzer.check_usage(filepath, {
            "name": "test::inner_function",
            "type": "function",
            "base_name": "inner_function"
        })
        self.assertIsNotNone(result)  # Should detect usage
        
        # Test inner_unused usage detection
        result = analyzer.check_usage(filepath, {
            "name": "test::inner_unused",
            "type": "function",
            "base_name": "inner_unused"
        })
        # import pdb; pdb.set_trace()
        self.assertIsNone(result)  # Should not detect usage

        # Test unused_outer usage detection
        result = analyzer.check_usage(filepath, {
            "name": "test::unused_outer",
            "type": "function",
            "base_name": "unused_outer"
        })
        self.assertIsNone(result)  # Should not detect usage

    def test_called_as_function_argument(self):
        content = """
    def _transform_string_to_datetime_utc(value):
        return value
    def _transform_string_to_datetime_local(value):
        return value
    def my_view():
        return None
    class MyClass:
        field = BeforeValidator(_transform_string_to_datetime_utc)
    class MyClass:
        field = BeforeValidator(_transform_string_to_datetime_local, True)
    path(
        "osv-project-tracking-infos",
        my_view,
        name="osv-project-tracking-infos",
    ),
    """
        filepath = os.path.join(self.test_dir, "test.py")
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        
        result = analyzer.check_usage(filepath, {
            "name": "test::_transform_string_to_datetime_utc",
            "type": "function",
            "base_name": "_transform_string_to_datetime_utc"
        })
        self.assertIsNotNone(result)  # Should detect usage

        result = analyzer.check_usage(filepath, {
            "name": "test::_transform_string_to_datetime_local",
            "type": "function",
            "base_name": "_transform_string_to_datetime_local"
        })
        self.assertIsNotNone(result)  # Should detect usage

        result = analyzer.check_usage(filepath, {
            "name": "test::my_view",
            "type": "function",
            "base_name": "my_view"
        })
        self.assertIsNotNone(result)  # Should detect usage     

    def _write_test_file(self, filename: str, content: str):
        filepath = self.test_dir / filename
        filepath.write_text(content)

    def test_function_call_through_variable(self):
        content = """
    def used_function():
        return 42

    def other_function():
        a_random_name = SomeClass()
        result = a_random_name.used_function()
        return result
    """
        filepath = os.path.join(self.test_dir, "test.py")
        self._write_test_file("test.py", content)
        analyzer = PythonAnalyzer(self.test_dir)
        
        result = analyzer.check_usage(filepath, {
            "name": "test::used_function",
            "type": "function",
            "base_name": "used_function"
        })
        self.assertIsNotNone(result)  # Should detect usage through variable

    def tearDown(self):
        # Clean up all files and subdirectories recursively
        if self.test_dir.exists():
            for file in self.test_dir.glob("**/*"):
                if file.is_file():
                    file.unlink()
            self.test_dir.rmdir()
            


if __name__ == "__main__":
    unittest.main()

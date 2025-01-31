import unittest
from pathlib import Path

from deadcode import PhpAnalyzer


class TestPhpAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/fixtures/php")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def test_unused_standalone_function(self):
        code = """<?php
function unused_function() {
    return true;
}

function used_function() {
    return false;
}

used_function();
"""
        self._write_test_file("test1.php", code)
        analyzer = PhpAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "unused_function")

    def test_unused_class_method(self):
        code = """<?php
class TestClass {
    public function unusedMethod() {
        return true;
    }

    public function usedMethod() {
        return false;
    }

    public function callMethod() {
        $this->usedMethod();
    }
}
"""
        self._write_test_file("test2.php", code)
        analyzer = PhpAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "TestClass::unusedMethod")

    def test_route_annotation(self):
        code = """<?php
class Controller {
    #[Route("/api/test")]
    public function apiEndpoint() {
        return true;
    }
}
"""
        self._write_test_file("test3.php", code)
        analyzer = PhpAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 0)

    def test_interface_implementation(self):
        code = """<?php
interface TestInterface {
    public function requiredMethod();
}

class Implementation implements TestInterface {
    public function requiredMethod() {
        return true;
    }
}
"""
        self._write_test_file("test4.php", code)
        analyzer = PhpAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 0)

    def test_static_attribute(self):
        code = """<?php
class TestClass {
    public static string $unusedAttr = 'test';
    public static string $usedAttr = 'test';

    public function someMethod() {
        return self::$usedAttr;
    }
}
"""
        self._write_test_file("test5.php", code)
        analyzer = PhpAnalyzer(str(self.test_dir))
        results = analyzer.analyze()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "TestClass::$unusedAttr")

    def _write_test_file(self, filename: str, content: str):
        filepath = self.test_dir / filename
        filepath.write_text(content)

    def tearDown(self):
        for file in self.test_dir.glob("*.php"):
            file.unlink()
        self.test_dir.rmdir()


if __name__ == "__main__":
    unittest.main()

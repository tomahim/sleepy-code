import unittest
import json
import os
import subprocess
from pathlib import Path

class TestSpecsParametrized(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs_dir = Path('specs')
        cls.collectors = []
        cls.rules = []
        
        # Discover all collector and rule files
        for lang_dir in cls.specs_dir.iterdir():
            if lang_dir.is_dir():
                for spec_file in lang_dir.glob('*.collector'):
                    cls.collectors.append((lang_dir.name, spec_file))
                for spec_file in lang_dir.glob('*.rule'):
                    cls.rules.append((lang_dir.name, spec_file))

    def assertJsonEqual(self, first, second):
        """Custom assertion to compare JSON lists regardless of order"""
        if isinstance(first, list) and isinstance(second, list):
            # Sort lists by converting dict items to strings for comparison
            first_sorted = sorted(first, key=lambda x: json.dumps(x, sort_keys=True))
            second_sorted = sorted(second, key=lambda x: json.dumps(x, sort_keys=True))
            self.assertEqual(first_sorted, second_sorted)
        else:
            self.assertEqual(first, second)

    def parse_spec_file(self, spec_file):
        with open(spec_file) as f:
            content = f.read()
            sections = content.split('###')
            
            # Parse file examples and expected JSON
            files = {}
            for section in sections:
                if section.strip().startswith('file:'):
                    lines = section.strip().split('\n')
                    filename = lines[0].replace('file:', '').strip()
                    code = '\n'.join(lines[1:])
                    files[filename] = code
                elif 'JSON output' in section:
                    expected_json = json.loads(section.split('JSON output\n')[1])
            
            return files, expected_json

    def create_temp_files(self, files, temp_dir):
        for filename, content in files.items():
            file_path = temp_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    def test_collectors(self):
        for lang, collector_file in self.collectors:
            with self.subTest(collector=collector_file.stem, language=lang):
                files, expected_json = self.parse_spec_file(collector_file)
                
                # Create temporary test files
                temp_dir = Path('temp_test_files')
                temp_dir.mkdir(exist_ok=True)
                self.create_temp_files(files, temp_dir)
                
                try:
                    result = subprocess.check_output(
                        ['deadcode', str(temp_dir), f'--{lang}', '-c', collector_file.stem, '--json'],
                        text=True
                    )
                    self.assertJsonEqual(json.loads(result), expected_json)
                finally:
                    # Cleanup temp files
                    for file in temp_dir.glob('**/*'):
                        if file.is_file():
                            file.unlink()
                    temp_dir.rmdir()

    def test_rules(self):
        for lang, rule_file in self.rules:
            with self.subTest(rule=rule_file.stem, language=lang):
                files, expected_json = self.parse_spec_file(rule_file)
                
                # Create temporary test files
                temp_dir = Path('temp_test_files')
                temp_dir.mkdir(exist_ok=True)
                self.create_temp_files(files, temp_dir)
                
                try:
                    result = subprocess.check_output(
                        ['deadcode', str(temp_dir), f'--{lang}', '-r', rule_file.stem, '--json'],
                        text=True
                    )
                    self.assertJsonEqual(json.loads(result), expected_json)
                finally:
                    # Cleanup temp files
                    for file in temp_dir.glob('**/*'):
                        if file.is_file():
                            file.unlink()
                    temp_dir.rmdir()

if __name__ == '__main__':
    unittest.main()

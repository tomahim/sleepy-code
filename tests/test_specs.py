import unittest
import json
import os
import subprocess
import tempfile
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
        if isinstance(first, list) and isinstance(second, list):
            first_sorted = sorted(first, key=lambda x: json.dumps(x, sort_keys=True))
            second_sorted = sorted(second, key=lambda x: json.dumps(x, sort_keys=True))
            self.assertEqual(first_sorted, second_sorted)
        else:
            self.assertEqual(first, second)

    def parse_spec_file(self, spec_file):
        with open(spec_file) as f:
            content = f.read()
            sections = content.split('###')
            
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
        created_files = []
        for filename, content in files.items():
            file_path = temp_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            created_files.append(str(file_path))
        return created_files

    def _run_spec_test(self, lang, spec_file, flag_type):
        """Common test logic for both collectors and rules"""
        with self.subTest(spec=spec_file.stem, language=lang):
            files, expected_json = self.parse_spec_file(spec_file)
            
            temp_dir = Path(tempfile.mkdtemp())
            try:
                self.create_temp_files(files, temp_dir)
                result = subprocess.check_output(
                    ['deadcode', str(temp_dir), f'--{lang}', flag_type, spec_file.stem, '--json'],
                    text=True
                )
                self.assertJsonEqual(json.loads(result), expected_json)
            finally:
                for file in temp_dir.glob('**/*'):
                    if file.is_file():
                        file.unlink()
                temp_dir.rmdir()

    def test_collectors(self):
        for lang, collector_file in self.collectors:
            self._run_spec_test(lang, collector_file, '-c')

    def test_rules(self):
        for lang, rule_file in self.rules:
            self._run_spec_test(lang, rule_file, '-r')
import unittest
import json
from pathlib import Path

class TestJsonValidity(unittest.TestCase):
    def validate_json_in_file(self, spec_file):
        with open(spec_file) as f:
            content = f.read()
            try:
                json_section = content.split('### JSON output\n')[1]
                json.loads(json_section)
            except json.JSONDecodeError as e:
                # Show the problematic JSON content with line numbers
                lines = json_section.split('\n')
                numbered_lines = [f"{i+1}: {line}" for i, line in enumerate(lines)]
                error_context = '\n'.join(numbered_lines)
                
                self.fail(f"\nJSON Error in {spec_file}:\n"
                         f"Error: {str(e)}\n"
                         f"JSON content:\n{error_context}")
            except IndexError:
                self.fail(f"No '### JSON output' section found in {spec_file}")

    def test_json_validity_in_specs(self):
        specs_dir = Path('specs')
        
        for lang_dir in specs_dir.iterdir():
            if lang_dir.is_dir():
                for spec_file in lang_dir.glob('*.collector'):
                    with self.subTest(file=spec_file):
                        self.validate_json_in_file(spec_file)
                
                for spec_file in lang_dir.glob('*.rule'):
                    with self.subTest(file=spec_file):
                        self.validate_json_in_file(spec_file)

if __name__ == '__main__':
    unittest.main()

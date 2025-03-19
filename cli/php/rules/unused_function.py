from typing import List, Dict
import re
from ..base_rule import BaseRule

class UnusedFunctionRule(BaseRule):
    def analyze(self) -> List[Dict]:
        violations = []
        used_functions = self._find_function_calls()
        
        for function in self.collector_results:
            # Check if function is used in any file
            if function["name"] not in used_functions:
                class_name = self._get_class_name(function["file"])
                violations.append({
                    "line": function["line"],
                    "name": function["name"],
                    "message": f"Unused function {class_name}::{function['name']}",
                    "rule": "unused-function",
                    "file": function["file"]
                })
        
        return violations

    def _find_function_calls(self) -> set:
        used_functions = set()
        
        for file in self.files:
            with open(file, 'r') as f:
                content = f.read()
            
            # Find method calls like $obj->method()
            method_calls = re.finditer(r'->(\w+)\s*\(', content)
            for match in method_calls:
                used_functions.add(match.group(1))
        
        return used_functions

    def _get_class_name(self, filename: str) -> str:
        # Find the matching file path from self.files
        full_path = next((f for f in self.files if f.endswith(filename)), None)
        if not full_path:
            return filename.replace('.php', '')
            
        with open(full_path, 'r') as f:
            content = f.read()
        
        class_match = re.search(r'class\s+(\w+)', content)
        return class_match.group(1) if class_match else ''
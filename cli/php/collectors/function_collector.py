import re
from typing import List, Dict
from ..base_collector import BaseCollector

class PhpFunctionCollector(BaseCollector):
    def collect(self) -> List[Dict]:
        functions = []
        
        for file in self.files:
            with open(file, 'r') as f:
                content = f.readlines()
                
            for line_number, line in enumerate(content, 1):
                # Match function definitions including public, private, static
                pattern = r'\s*(public|private|protected)?\s*(static)?\s*function\s+(\w+)\s*\('
                match = re.search(pattern, line)
                
                if match:
                    function_name = match.group(3)
                    functions.append({
                        "name": function_name,
                        "file": file.split('/')[-1],
                        "line": line_number
                    })
                    
        return functions

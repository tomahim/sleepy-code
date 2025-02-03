import argparse
import ast
import os
import re
import sys
from abc import ABC, abstractmethod
from functools import partial
from multiprocessing import Pool

from tqdm import tqdm


class HTMLReport:
    def generate(self, results, language):
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Analysis Report</title>
            <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css">
            <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/dataTables.bootstrap5.min.css">
            <script type="text/javascript" src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
            <script type="text/javascript" src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                td, th {{ padding: 12px; text-align: left; }}
                .usage-0 {{ color: red; font-weight: bold; }}
                h1 {{ color: #333; }}
                .false-positive {{ color: orange; }}
                .static-attr {{ color: purple; }}
                .controls {{ margin: 20px 0; }}
                .hidden {{ display: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Code Analysis Report</h1>
                <div class="controls">
                    <label>
                        <input type="checkbox" id="showFalsePositives"> Show potential false positives
                    </label>
                </div>
                <table id="codeTable" class="display">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Lines</th>
                            <th>Usage Count</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
            <script>
                $(document).ready(function() {{
                    $.fn.dataTable.ext.search.push(
                        function(settings, data, dataIndex) {{
                            if (!$('#showFalsePositives').is(':checked') && data[3].includes('potential false positive')) {{
                                return false;
                            }}
                            return true;
                        }}
                    );

                    var table = $('#codeTable').DataTable({{
                        order: [[1, 'desc']],
                        pageLength: 50
                    }});

                    $('#showFalsePositives').change(function() {{
                        table.draw();
                    }});
                }});
            </script>
        </body>
        </html>
        """

        rows = []
        for name, lines, usage, status in results:
            usage_class = "usage-0" if usage == 0 else ""
            status_class = (
                "false-positive"
                if "potential false positive" in status
                else "static-attr"
                if "static attribute" in status
                else ""
            )
            row = f"<tr><td>{name}</td><td>{lines}</td><td class='{usage_class}'>{usage}</td><td class='{status_class}'>{status}</td></tr>"
            rows.append(row)

        html_content = html_template.format(table_rows="\n".join(rows))
        output_file = "code_analysis.html"

        output_file = f"code_analysis_{language}.html"
        with open(output_file, "w") as f:
            f.write(html_content)

        print(f"\nReport generated: {output_file}")


class CodeAnalyzer(ABC):
    def __init__(self, directory):
        self.directory = directory
        self.found_usage = []

    @abstractmethod
    def get_files(self, for_analysis=True):
        pass

    @abstractmethod
    def analyze_file_content(self, content, filepath):
        pass

    @abstractmethod
    def check_usage(self, filepath, element_info):
        pass

    @staticmethod
    def read_file(filepath):
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
        for encoding in encodings:
            try:
                with open(filepath, encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None

    def analyze(self, limit=None):
        elements = {}
        source_files = self.get_files(for_analysis=True)
        test_files = self.get_files(for_analysis=False)

        print("\nCollecting code elements...")
        with tqdm(total=len(source_files), desc="Scanning files", position=0) as pbar:
            for filepath in source_files:
                content = self.read_file(filepath)
                if content:
                    elements.update(self.analyze_file_content(content, filepath))
                pbar.update(1)

        all_files = source_files + test_files

        print("\nAnalyzing usage...")
        with Pool() as pool:
            with tqdm(total=len(all_files), desc="Checking usage", position=0) as pbar:
                for filepath in all_files:
                    if limit and len(elements) - len(self.found_usage) <= limit:
                        break
                    remaining = [
                        e
                        for name, e in elements.items()
                        if name not in self.found_usage
                    ]
                    results = pool.map(partial(self.check_usage, filepath), remaining)
                    self.found_usage.extend([r for r in results if r])
                    pbar.update(1)

        results = []
        unused_count = 0

        for name, info in elements.items():
            if name not in self.found_usage:
                results.append((name, info["lines"], 0, info.get("status", "")))
                unused_count += 1
                if limit and unused_count >= limit:
                    break

        results.sort(key=lambda x: x[1], reverse=True)
        return results


class PhpAnalyzer(CodeAnalyzer):
    POTENTIAL_FALSE_POSITIVE_PATTERNS = [
        "Listener",
        "processNode",
        "Subscriber",
        "EventSubscriber",
        "Kernel",
        "onAuthenticationFailure",
        "onAuthenticationSuccess",
        "RequirementCollection",
        "getHelpHtml",
        "Command",
        "Handler",
        "onLogout",
        "__invoke",
        "teardown",
        "__toString",
        "getNodeType",
    ]

    def get_files(self, for_analysis=True):
        files = []
        for root, _, filenames in os.walk(self.directory):
            for filename in filenames:
                if filename.endswith(".php"):
                    if "vendor" not in root.split(os.sep) and "cache" not in root.split(
                        os.sep
                    ):
                        filepath = os.path.join(root, filename)
                        is_test = "test" in root.lower() or filename.endswith(
                            "Test.php"
                        )
                        if for_analysis != is_test:
                            files.append(filepath)
        return files

    def analyze_file_content(self, content, filepath):
        elements = {}

        # Analyze functions
        pattern = r"function\s+(\w+)\s*\("
        matches = re.finditer(pattern, content)

        for match in matches:
            # Check for Route annotation in previous 200 characters
            content_before = content[max(0, match.start() - 200) : match.start()]
            if "#[Route" in content_before:
                continue

            func_name = match.group(1)
            class_name = self.find_class_name(content, match.start())

            # Skip if method is from an interface
            if class_name:
                implements_pattern = rf"class\s+{class_name}\s+implements\s+([\w\s,]+)"
                implements_match = re.search(implements_pattern, content)
                if implements_match:
                    interfaces = [
                        i.strip() for i in implements_match.group(1).split(",")
                    ]
                    if any(
                        self.is_interface_method(func_name, interface, content)
                        for interface in interfaces
                    ):
                        continue

            full_name = f"{class_name}::{func_name}" if class_name else func_name

            if full_name not in elements:
                status = (
                    "potential false positive"
                    if any(
                        pattern in full_name
                        for pattern in self.POTENTIAL_FALSE_POSITIVE_PATTERNS
                    )
                    else ""
                )
                elements[full_name] = {
                    "name": full_name,
                    "lines": self.count_function_lines(content, match.end()),
                    "base_name": func_name,
                    "class_name": class_name,
                    "type": "function",
                    "status": status,
                }
        return elements

    def is_interface_method(self, method_name, interface_name, content):
        interface_pattern = rf"interface\s+{interface_name}\s*{{([^}}]+)}}"
        interface_match = re.search(interface_pattern, content)
        if interface_match:
            interface_body = interface_match.group(1)
            return bool(re.search(rf"function\s+{method_name}\s*\(", interface_body))
        return False

    def check_usage(self, filepath, element_info):
        if element_info["name"] in self.found_usage:
            return None

        content = self.read_file(filepath)
        if not content:
            return None

        if element_info["type"] == "function":
            patterns = [
                rf"(?<!function\s){element_info['base_name']}\s*\(",
                rf"\$this->{element_info['base_name']}\s*\(",
                rf"self::{element_info['base_name']}\s*\(",
                rf"static::{element_info['base_name']}\s*\(",
            ] 
        else:  # static attribute
            patterns = [
                rf"{element_info['class_name']}::\${element_info['base_name']}",
                rf"static::\${element_info['base_name']}",
                rf"self::\${element_info['base_name']}",
            ]

        total_usage = sum(len(re.findall(pattern, content)) for pattern in patterns)

        if total_usage > 0:
            return element_info["name"]
        return None

    def find_class_name(self, content, position):
        content_before = content[:position]
        content_before = re.sub(r"/\*.*?\*/", "", content_before, flags=re.DOTALL)
        content_before = re.sub(r"//.*?\n", "", content_before)
        class_pattern = r"(?:class|interface|abstract\s+class|trait|enum)\s+(\w+)(?:\s*:\s*\w+|\s+extends|\s+implements|\s*\{)"
        class_matches = list(re.finditer(class_pattern, content_before))
        return class_matches[-1].group(1) if class_matches else None

    def count_function_lines(self, content, start_pos):
        bracket_count = 0
        line_count = 1
        pos = start_pos

        while pos < len(content):
            if content[pos] == "{":
                bracket_count += 1
            elif content[pos] == "}":
                bracket_count -= 1
                if bracket_count == 0:
                    return line_count
            elif content[pos] == "\n":
                line_count += 1
            pos += 1
        return line_count


class PythonAnalyzer(CodeAnalyzer):
    POTENTIAL_FALSE_POSITIVE_PATTERNS = [
        "test_",
        "setup",
        "teardown",
        "__str__",
        "__call__",
        "__repr__",
        "__init__",
        "__post_init__",
        "__getitem__",
        "before_sentry_send"
    ]

    def get_files(self, for_analysis=True):
        files = []
        for root, _, filenames in os.walk(self.directory):
            for filename in filenames:
                if filename.endswith(".py"):
                    if "venv" not in root.split(
                        os.sep
                    ) and "__pycache__" not in root.split(os.sep):
                        filepath = os.path.join(root, filename)
                        is_test = (
                            "test" in root.lower()
                            or filename.startswith("test_")
                            or filename.endswith("_test.py")
                        )
                        if for_analysis != is_test:
                            files.append(filepath)
        return files

    def analyze_file_content(self, content, filepath):
        elements = {}
        filename = os.path.basename(filepath).replace(".py", "")

        # Find all decorators and their function names
        decorator_pattern = r'@(\w+(?:\.\w+)*)(?:\s*\([^)]*(?:"[^"]*"[^)]*)*\))?\s*\n\s*(?:@[^\n]+\n\s*)*(?:async\s+)?def\s+(\w+)\s*\('
        decorated_functions = {}
        property_functions = {}  # Store both function name and match position

        for match in re.finditer(decorator_pattern, content):
            decorator_name, func_name = match.groups()
            if func_name not in decorated_functions:
                decorated_functions[func_name] = []
            decorated_functions[func_name].append(decorator_name)
            
            # Track property decorated functions with their position
            if decorator_name in ('property', 'cached_property'):
                property_functions[func_name] = match.start()

        # Process properties
        for func_name, pos in property_functions.items():
            # Skip if function has validator decorator
            if any('validator' in d.lower() for d in decorated_functions[func_name]):
                continue
                
            class_name = self.find_class_name(content, pos)
            if class_name:
                full_name = f"{filename}::{class_name}::{func_name}"
                if full_name not in elements:
                    status = "potential false positive" if any(pattern in full_name for pattern in self.POTENTIAL_FALSE_POSITIVE_PATTERNS) else ""
                    elements[full_name] = {
                        "name": full_name,
                        "lines": self.count_function_lines(content, pos),
                        "base_name": func_name,
                        "class_name": class_name,
                        "type": "property",
                        "status": status
                    }

        # Find regular functions/methods
        function_pattern = r"(?:async\s+)?def\s+(\w+)\s*\("
        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            
            # Skip if function has validator decorator or is already processed as property
            if (func_name in decorated_functions and any('validator' in d.lower() for d in decorated_functions[func_name])) or \
            func_name in property_functions:
                continue
                
            class_name = self.find_class_name(content, match.start())
            full_name = f"{filename}::{class_name}::{func_name}" if class_name else f"{filename}::{func_name}"

            if full_name not in elements:
                status = "potential false positive" if any(pattern in full_name for pattern in self.POTENTIAL_FALSE_POSITIVE_PATTERNS) else ""
                elements[full_name] = {
                    "name": full_name,
                    "lines": self.count_function_lines(content, match.end()),
                    "base_name": func_name,
                    "class_name": class_name,
                    "type": "method" if class_name else "function",
                    "status": status
                }

        return elements

    def _get_patterns(self, element_info, is_same_file):
        """Get regex patterns for usage detection based on element type."""
        name_parts = element_info["name"].split("::")
        current_file = name_parts[0]
        func_name = name_parts[-1]
        
        base_patterns = {
            "property": [
                rf"self\.{func_name}\b(?!\s*\()",
                rf"\w+\.{func_name}\b(?!\s*\()",
                rf"super\(\)\.{func_name}\b(?!\s*\()",
                rf"\b{func_name}\b(?!\s*\()"  # Direct reference
            ],
            "method": [
                rf"self\.{func_name}\s*\(",
                rf"\w+\.{func_name}\s*\(",
                rf"super\(\)\.{func_name}\s*\(",
                rf"(?<!def\s)\b{func_name}\s*\("  # Direct reference
            ],
            "function": [
                rf"(?<!def\s)(?<!\.)\b{func_name}\s*\(",  # Simple function call
                rf"=\s*{func_name}\s*\(",
                rf"return\s+{func_name}\s*\(",
                rf"[,(]\s*{func_name}\s*\(",
                rf"\w+\([^)]*{func_name}[^)]*\)",  # Function as argument in any position
                rf"\w+\.{func_name}\s*\("  # Method-style call through variable
            ]
        }

        import_patterns = {
            "property": [rf"from\s+{current_file}\s+import\s+{func_name}"],
            "method": [rf"from\s+{current_file}\s+import\s+{func_name}"],
            "function": [
                rf"from\s+{current_file}\s+import\s+{func_name}",
                rf"import\s+{current_file}\.{func_name}"
            ]
        }

        patterns = base_patterns[element_info["type"]]
        if not is_same_file:
            patterns.extend(import_patterns[element_info["type"]])
        
        return patterns

    def check_usage(self, filepath, element_info):
        if element_info["name"] in self.found_usage:
            return None

        content = self.read_file(filepath)
        if not content:
            return None

        name_parts = element_info["name"].split("::")
        current_file_path = os.path.basename(filepath).replace(".py", "")
        is_same_file = name_parts[0] == current_file_path

        patterns = self._get_patterns(element_info, is_same_file)
        total_usage = sum(len(re.findall(pattern, content)) for pattern in patterns)

        if total_usage > 0:
            return element_info["name"]
        return None

    def find_class_name(self, content, position):
        content_before = content[:position]
        lines = content_before.split('\n')
        
        # Get indentation level of the function
        func_line_no = content_before.count('\n')
        func_indent = len(lines[-1]) - len(lines[-1].lstrip())
        
        # Find all class definitions
        class_pattern = r"^(\s*)class\s+(\w+)(?:\s*\([\w\s,]*\))?\s*:"
        class_matches = []
        
        for i, line in enumerate(lines):
            match = re.match(class_pattern, line)
            if match:
                indent = len(match.group(1))
                class_name = match.group(2)
                class_matches.append((i, indent, class_name))
        
        # Find the innermost class that contains our function
        current_class = None
        for line_no, indent, class_name in class_matches:
            if line_no < func_line_no and indent < func_indent:
                current_class = class_name
                
        return current_class

    def count_function_lines(self, content, start_pos):
        bracket_count = 0
        line_count = 1
        pos = start_pos

        while pos < len(content):
            if content[pos] == "{" or content[pos] == ":":
                bracket_count += 1
            elif content[pos] == "}" or (content[pos] == "\n" and content[pos-1] == "\n"):
                bracket_count -= 1
                if bracket_count == 0:
                    return line_count
            elif content[pos] == "\n":
                line_count += 1
            pos += 1
        return line_count


def main():
    parser = argparse.ArgumentParser(description="Analyze code for unused elements")
    parser.add_argument("directory", help="Directory path containing source files")
    parser.add_argument("--language", choices=["php", "python"], required=True)
    parser.add_argument("--limit", type=int, help="Limit the number of results")
    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="List functions sorted by line count",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a valid directory")
        sys.exit(1)

    analyzer = (
        PhpAnalyzer(args.directory)
        if args.language == "php"
        else PythonAnalyzer(args.directory)
    )

    if args.list_functions:
        elements = {}
        source_files = analyzer.get_files(for_analysis=True)
        for filepath in source_files:
            content = analyzer.read_file(filepath)
            if content:
                elements.update(analyzer.analyze_file_content(content, filepath))
        results = [(name, info["lines"], "-", "") for name, info in elements.items()]
        results.sort(key=lambda x: x[1], reverse=True)
    else:
        results = analyzer.analyze(limit=args.limit)

    report = HTMLReport()
    report.generate(results, args.language)


if __name__ == "__main__":
    main()

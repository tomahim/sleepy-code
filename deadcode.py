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
        try:
            tree = ast.parse(content)

            # First collect all functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not any(
                        isinstance(parent, ast.ClassDef)
                        and hasattr(parent, "body")
                        and node in parent.body
                        for parent in ast.walk(tree)
                    ):
                        full_name = f"{filename}::{node.name}"
                        elements[full_name] = {
                            "name": full_name,
                            "base_name": node.name,
                            "lines": node.end_lineno - node.lineno + 1,
                            "type": "function",
                        }
                elif isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            full_name = f"{filename}::{node.name}::{item.name}"
                            elements[full_name] = {
                                "name": full_name,
                                "base_name": item.name,
                                "lines": item.end_lineno - item.lineno + 1,
                                "type": "method",
                            }

            # Then check usage within the same file
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        used_name = f"{filename}::{node.func.id}"
                        if used_name in elements:
                            elements.pop(used_name)
                    elif isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "self"
                        ):
                            for key in list(elements.keys()):
                                if key.endswith(f"::{node.func.attr}"):
                                    elements.pop(key)

        except SyntaxError:
            print(f"Syntax error in file: {filepath}")

        return elements

    def check_usage(self, filepath, element_info):
        if element_info["name"] in self.found_usage:
            return None

        content = self.read_file(filepath)
        if not content:
            return None

        try:
            tree = ast.parse(content)
            imports = {}
            name_parts = element_info["name"].split("::")

            # Collect imports in this file
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports[name.asname or name.name] = name.name
                elif isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        imports[name.asname or name.name] = f"{node.module}.{name.name}"

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        # Check direct calls and imported function calls
                        if node.func.id == name_parts[-1] or node.func.id in imports:
                            return element_info["name"]
                    elif isinstance(node.func, ast.Attribute):
                        # Check method calls including through imports
                        if len(name_parts) > 2:  # Class method
                            if (
                                isinstance(node.func.value, ast.Name)
                                and (
                                    node.func.value.id == "self"
                                    or node.func.value.id in imports
                                )
                                and node.func.attr == name_parts[-1]
                            ):
                                return element_info["name"]
        except SyntaxError:
            pass

        return None


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

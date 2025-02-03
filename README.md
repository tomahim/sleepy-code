# 👻 Sleepy Code

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Find unused functions and methods in your PHP and Python codebases with style!

## ✨ Features

- 🔍 Detects unused functions, methods and static attributes
- 🎯 Smart detection of interface implementations
- 🚫 Excludes route-annotated methods in PHP
- 📊 Interactive HTML report with filtering capabilities
- 🔄 Multi-processing for fast analysis
- 🐍 Supports both PHP and Python codebases

## 🎯 TODO

- [ ] Add support for TS
- [ ] Detect unused classes (make them displayed in a new tab in the report)
- [ ] Detect unused variables and imports

## 🚀 Getting Started

### Setup Virtual Environment & requirements

```bash
python -m venv venv --without-pip
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 💻 Usage Examples

Analyze PHP codebase:

`python deadcode.py /path/to/php/project --language php`

Analyze Python codebase with result limit:

`python deadcode.py /path/to/python/project --language python --limit 50`

List all functions sorted by line count:

`python deadcode.py /path/to/project --language php --list-functions`

## 🧪 Testing

Run the test suite:
```bash
python -m unittest tests/test_python_analyzer.py
```

### 📊 Reports

The tool generates an interactive HTML report:

Sort by name, lines, or usage count
Toggle visibility of potential false positives
Search and filter results
Paginated results for easy navigation

Reports are generated as:

- code_analysis_php.html for PHP analysis
- code_analysis_python.html for Python analysis

- 🎨 Report Colors
- 🔴 Red: Unused functions
- 🟠 Orange: Potential false positives
- 🟣 Purple: Static attributes

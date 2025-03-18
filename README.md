# 👻 Sleepy Code

## Development Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install package in development mode:
```bash
pip install -e .
```

4. Command usage
```bash
deadcode --help
```

5. Run tests:
```bash
python -m unittest discover tests -v
```
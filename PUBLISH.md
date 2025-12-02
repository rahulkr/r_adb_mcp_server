# How to Publish to PyPI

## One-time Setup

1. **Create PyPI Account**
   - Go to https://pypi.org/account/register/
   - Verify your email

2. **Create API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create a token with "Entire account" scope
   - Save it securely (you'll only see it once)

3. **Install build tools**
   ```bash
   pip install build twine
   ```

## Before Publishing

1. **Update package name** in `pyproject.toml`:
   - Change `name = "adb-mcp-server"` to something unique like `adb-mcp-server-yourname`
   - Check if name is available: https://pypi.org/project/YOUR-NAME-HERE/

2. **Update author info** in `pyproject.toml`:
   ```toml
   authors = [
       {name = "Your Name", email = "your.email@example.com"}
   ]
   ```

3. **Update URLs** in `pyproject.toml` with your GitHub repo

4. **Update version** for each release:
   - In `pyproject.toml`: `version = "0.1.0"`
   - In `src/adb_mcp_server/__init__.py`: `__version__ = "0.1.0"`

## Publishing Steps

```bash
# 1. Clean old builds
rm -rf dist/ build/ *.egg-info

# 2. Build the package
python -m build

# 3. Check the build
twine check dist/*

# 4. Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# 5. Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ adb-mcp-server-yourname

# 6. If everything works, upload to real PyPI
twine upload dist/*
```

## After Publishing

Users can install with:
```bash
pip install adb-mcp-server-yourname

# Or run directly with uvx
uvx adb-mcp-server-yourname
```

## MCP Configuration for Users

After installing, users add to their Claude Desktop config:

```json
{
  "mcpServers": {
    "adb": {
      "command": "adb-mcp-server-yourname"
    }
  }
}
```

Or with uvx (no install needed):
```json
{
  "mcpServers": {
    "adb": {
      "command": "uvx",
      "args": ["adb-mcp-server-yourname"]
    }
  }
}
```

## Versioning

Follow semantic versioning:
- `0.1.0` → `0.1.1` for bug fixes
- `0.1.0` → `0.2.0` for new features
- `0.1.0` → `1.0.0` for major/breaking changes

## Updating

```bash
# Update version in pyproject.toml and __init__.py
# Then rebuild and upload
rm -rf dist/
python -m build
twine upload dist/*
```

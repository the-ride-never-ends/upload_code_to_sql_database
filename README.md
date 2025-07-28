# Code Upload System

A tool to consolidate and organize Python code from multiple projects into a searchable database.

## Overview

This tool scans Python projects to extract standalone functions and classes, generates unique content identifiers (CIDs), and stores them in a MySQL database. It's designed to help consolidate scattered code across multiple half-finished projects into a searchable, deduplicated repository.

The system only uploads "complete" code - standalone functions and classes that have docstrings. Methods, nested functions, and undocumented code are skipped to maintain quality standards.

## Usage

### Basic Commands

```bash
# Basic usage
python upload_code.py /path/to/project

# Recursive scan with custom exclusions
python upload_code.py /path/to/project --recursive --exclude "temp/*" "*.backup"

# Dry run to see what would be uploaded
python upload_code.py /path/to/project --recursive --dry-run

# With custom database configuration
python upload_code.py /path/to/project --db-config config/database.ini
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `directory` | Path to scan for Python files (required) |
| `--recursive` | Scan subdirectories recursively |
| `--dry-run` | Preview what would be uploaded without making changes |
| `--exclude PATTERN` | Add exclusion patterns (can be used multiple times) |
| `--db-config FILE` | Path to database configuration file |
| `--verbose` | Show detailed processing information |

## Default Exclusions

The following directories are always excluded:
- `__pycache__` (Python bytecode)
- `.git` (Version control)
- `venv`, `.venv` (Virtual environments)
- `node_modules` (JavaScript dependencies)
- `.pytest_cache` (Test framework cache)
- `build`, `dist` (Build artifacts)

## What Gets Uploaded

### ✅ Uploaded
- Top-level functions with docstrings
- Top-level classes with docstrings
- Async functions and generators (if standalone with docs)

### ❌ Skipped
- Functions/classes without docstrings
- Methods inside classes
- Nested functions
- Lambda expressions
- Files with syntax errors
- Duplicate code (same CID already in database)

## Database Requirements

Requires MySQL database with these tables:
- `codes`: Stores source code with CIDs
- `metadata`: Stores additional information and tags

The database schema must exist before running this tool. See computer_code schema documentation for table definitions.

## Deduplication

Each piece of code gets a unique Content Identifier (CID) based on its signature, docstring, and implementation. Identical code anywhere in your projects will have the same CID and won't be uploaded twice.

## Example Output

```
Scanning /home/user/projects...
Found 47 Python files

Processing: utils/file_helpers.py
    - Found: read_json_file (function)
    - Found: FileManager (class)
    - Skipped: _internal_helper (no docstring)
    - Skipped: FileManager.save (not standalone)

Processing: tests/test_utils.py
    - Found: test_file_operations (function)
        ✓ Successfully uploaded

==================================================
Upload Complete!
==================================================
Files scanned:            47
Callables found:          156
Skipped (not standalone): 89
Skipped (no docstring):   34
Valid callables:          33
New uploads:              28
Duplicates skipped:       5
Errors:                   0

Database now contains 1,247 code entries
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success: All eligible code uploaded successfully |
| 1 | Partial success: Some uploads succeeded, but errors occurred |
| 2 | Failure: Could not connect to database or critical error |

## Error Handling

- Syntax errors in Python files are logged and skipped
- Database connection errors cause immediate exit
- Upload errors are collected and shown in summary
- All errors include file paths for investigation

## Configuration File Format

If using `--db-config`, the file should contain:

```ini
[database]
DB_HOST = localhost
DB_USER = your_username
DB_PASSWORD = your_password
DB_NAME = computer_code
DB_PORT = 3306
```

If not specified, defaults to the contents of `sql_configs.yaml` in the current directory.

## Tips for Best Results

1. Add docstrings to functions you want to preserve
2. Use `--dry-run` first to preview what will be uploaded
3. Review the summary for any unexpected skips
4. Check parse errors if files are missing from results
5. Use `--exclude` to skip experimental or deprecated code

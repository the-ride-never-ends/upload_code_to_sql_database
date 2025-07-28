#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Upload System - Main entry point skeleton.

This module scans Python codebases, extracts standalone callables with docstrings,
generates CIDs, and stores them in the database.
"""
from pathlib import Path
import sys
from typing import Optional, Any, TypeVar
import rich


from callables.get_callables_from_file import get_callables_from_file
from callables.validate_callable import validate_callable
from cid.check_cid_exists import check_cid_exists
from code_entry.create_code_entry import create_code_entry, CodeEntry
from code_entry.upload_code_entry import upload_code_entry
from find_python_files import find_python_files
from generate_summary_report import generate_summary_report
from parse_arguments import parse_arguments
from start_database import start_database
from upload_stats import UploadStats


DatabaseConnection = TypeVar("DatabaseConnection")


def main() -> int:
    """
    Code Upload System - Consolidate and organize Python code from multiple projects.

    OVERVIEW
    --------
    This tool scans Python projects to extract standalone functions and classes,
    generates unique content identifiers (CIDs), and stores them in a MySQL database.
    It's designed to help consolidate scattered code across multiple half-finished
    projects into a searchable, deduplicated repository.

    The system only uploads "complete" code - standalone functions and classes that
    have docstrings. Methods, nested functions, and undocumented code are skipped
    to maintain quality standards.

    USAGE
    -----
    Basic usage:
        python upload_code.py /path/to/project

    Recursive scan with custom exclusions:
        python upload_code.py /path/to/project --recursive --exclude "temp/*" "*.backup"

    Dry run to see what would be uploaded:
        python upload_code.py /path/to/project --recursive --dry-run

    With custom database configuration:
        python upload_code.py /path/to/project --db-config config/database.ini

    COMMAND LINE OPTIONS
    --------------------
    directory               Path to scan for Python files (required)

    --recursive            Scan subdirectories recursively
                          Without this flag, only the top-level directory is scanned

    --dry-run             Preview what would be uploaded without making changes
                          Shows CID generation and duplicate detection
                          No database modifications are made

    --exclude PATTERN     Add exclusion patterns (can be used multiple times)
                          Examples: --exclude "test_*.py" --exclude "old/"
                          These are added to default exclusions

    --db-config FILE      Path to database configuration file
                          If not provided, uses default connection settings

    --verbose             Show detailed processing information
                          Displays decisions about each file and callable

    DEFAULT EXCLUSIONS
    -----------------
    The following directories are always excluded:
    - __pycache__     (Python bytecode)
    - .git            (Version control)
    - venv, .venv     (Virtual environments)
    - node_modules    (JavaScript dependencies)
    - .pytest_cache   (Test framework cache)
    - build, dist     (Build artifacts)

    WHAT GETS UPLOADED
    -----------------
    ✓ Uploaded:
      - Top-level functions with docstrings
      - Top-level classes with docstrings
      - Async functions and generators (if standalone with docs)

    ✗ Skipped:
      - Functions/classes without docstrings
      - Methods inside classes
      - Nested functions
      - Lambda expressions
      - Files with syntax errors
      - Duplicate code (same CID already in database)

    DATABASE REQUIREMENTS
    --------------------
    Requires MySQL database with these tables:
    - codes: Stores source code with CIDs
    - metadata: Stores additional information and tags

    The database schema must exist before running this tool.
    See computer_code schema documentation for table definitions.

    DEDUPLICATION
    -------------
    Each piece of code gets a unique Content Identifier (CID) based on its
    signature, docstring, and implementation. Identical code anywhere in your
    projects will have the same CID and won't be uploaded twice.

    EXAMPLE OUTPUT
    --------------
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

    EXIT CODES
    ----------
    0 - Success: All eligible code uploaded successfully
    1 - Partial success: Some uploads succeeded, but errors occurred
    2 - Failure: Could not connect to database or critical error

    ERROR HANDLING
    --------------
    - Syntax errors in Python files are logged and skipped
    - Database connection errors cause immediate exit
    - Upload errors are collected and shown in summary
    - All errors include file paths for investigation

    TIPS FOR BEST RESULTS
    --------------------
    1. Add docstrings to functions you want to preserve
    2. Use --dry-run first to preview what will be uploaded
    3. Review the summary for any unexpected skips
    4. Check parse errors if files are missing from results
    5. Use --exclude to skip experimental or deprecated code

    CONFIGURATION FILE FORMAT
    ------------------------
    If using --db-config, the file should contain:

    [database]
    host = localhost
    user = your_username
    password = your_password
    database = computer_code
    port = 3306

    Returns:
        int: Exit code indicating success (0), partial success (1), or failure (2)
    """
    try:
        # Initialize - Parse command line arguments
        args = parse_arguments()

        # Initialize statistics tracker
        stats = UploadStats()

        # Initialize database connection
        try:
            db_connection: DatabaseConnection = start_database(args.db_config)
        except Exception as e:
            import traceback

            print(f"Failed to connect to database: {e}\n{traceback.format_exc()}")
            return 2

        # File Discovery - Scan directories for Python files
        print(f"Scanning {args.directory}...")
        python_files: list[Path] = find_python_files(
            directory=args.directory,
            recursive=args.recursive,
            exclude_patterns=args.exclude,
        )

        if not python_files:
            print("No Python files found.")
            return 0

        print(f"Found {len(python_files)} Python files")
        stats.files_scanned = len(python_files)

        # Main Processing Loop - Process each file
        for file_path in python_files:
            print(f"\nProcessing: {file_path}")

            # File Processing - Parse file with AST
            try:
                callables: list[dict[str, Any]] = get_callables_from_file(file_path)
            except SyntaxError as e:
                print(f"  ✗ Syntax error: {e}")
                stats.parse_errors.append((file_path, str(e)))
                continue

            if not callables:
                print("  No top-level callables found")
                continue

            # Process each callable in the file
            for callable_info in callables:
                stats.callables_found += 1

                # Callable Validation - Check if meets criteria
                validation_result: Optional[str] = validate_callable(callable_info)

                match validation_result:
                    case "not_standalone":
                        print(f"  - Skipped: {callable_info['name']} (not standalone)")
                        stats.skipped_not_standalone += 1
                        continue
                    case "no_docstring":
                        print(f"  - Skipped: {callable_info['name']} (no docstring)")
                        stats.skipped_no_docstring += 1
                        continue

                print(f"  - Found: {callable_info['name']} ({callable_info['type']})")

                # CID Processing - Generate CID and check duplicates
                code_entry: CodeEntry = create_code_entry(callable_info, file_path)

                # Check for duplicates
                cid_exists: bool = check_cid_exists(
                    db_connection, code_entry.metadata["cid"]
                )

                if args.dry_run:
                    print(f"    [DRY RUN] Would generate CID: {code_entry.cid[:12]}...")
                    continue

                if cid_exists:
                    print(f"    Duplicate metadata CID found, skipping")
                    stats.skipped_duplicates += 1
                    continue

                # Database Operations - Insert into database
                try:
                    upload_code_entry(db_connection, code_entry)
                    print(f"    ✓ Successfully uploaded")
                    stats.new_uploads += 1
                except Exception as e:
                    print(f"    ✗ Upload failed: {e}")
                    stats.errors.append(
                        {
                            "file": str(file_path),
                            "callable": callable_info["name"],
                            "error": str(e),
                        }
                    )
                    continue

        # Reporting - Generate and display summary
        generate_summary_report(stats, db_connection)

        # Determine exit code based on results
        if stats.errors or stats.parse_errors:
            return 1 if stats.new_uploads > 0 else 2
        return 0

    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())

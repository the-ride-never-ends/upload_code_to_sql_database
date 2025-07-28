"""Command line argument parsing for code upload utility.

This module provides argument parsing functionality for a tool that uploads
code files to a SQL database. It handles directory paths, filtering options,
and database configuration.
"""

import argparse
from pathlib import Path


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments for the code upload system.

    Creates an ArgumentParser instance to handle user input from the command line,
    defining all necessary arguments for scanning directories and uploading Python
    code to the database. Converts directory paths to Path objects and ensures
    exclude patterns are always returned as a list.

    The function defines both required positional arguments and optional flags
    to control the upload behavior. Default exclusion patterns include common
    non-code directories that should be skipped during scanning.

    Command-line Arguments:
        directory (positional): Path to the directory to scan for Python files.
            Can be relative or absolute. Will be converted to a Path object.

        --recursive: Flag to enable recursive scanning of subdirectories.
            If not specified, only the top-level directory is scanned.

        --dry-run: Flag to simulate the upload process without making database
            changes. Useful for testing what would be uploaded.

        --exclude: List of file or directory patterns to exclude from scanning.
            Can be specified multiple times. Patterns are added to the default
            exclusion list which includes: __pycache__, .git, venv, .venv,
            node_modules, .pytest_cache, build, dist.

        --db-config: Optional path to a database configuration file.
            If not specified, the system will use default connection parameters.

        --verbose: Flag to enable detailed output during processing.
            Shows additional information about files being processed and
            decisions being made.

    Returns:
        argparse.Namespace: Parsed arguments with the following attributes:
            - directory (Path): Converted Path object for the target directory
            - recursive (bool): Whether to scan subdirectories
            - dry_run (bool): Whether to simulate without database writes
            - exclude (List[str]): Combined list of user and default exclusions
            - db_config (Optional[str]): Path to database config or None
            - verbose (bool): Whether to show detailed output

    Raises:
        SystemExit: If required arguments are missing or invalid. This is
            standard argparse behavior that prints usage information.

    Example:
        # Typical usage in main():
        args = parse_arguments()

        # Command line: python upload_code.py /path/to/project --recursive
        # Results in:
        #   args.directory = Path('/path/to/project')
        #   args.recursive = True
        #   args.dry_run = False
        #   args.exclude = ['__pycache__', '.git', 'venv', ...]

    Notes:
        - The function handles argument parsing but not validation of paths
        - Tilde expansion (~) in paths is handled by Path conversion
        - Multiple --exclude flags are accumulated into a single list
    """
    # Default exclusion patterns for common non-code directories and files
    default_exclude_patterns = [
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
    ]

    parser = argparse.ArgumentParser(
        description="Upload code files to SQL database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project
  %(prog)s . --recursive --dry-run
  %(prog)s /project --exclude "*.log" --db-config db.conf --verbose
        """,
    )

    # Required positional argument: directory to scan
    parser.add_argument(
        "directory", type=Path, help="Directory path to scan for code files"
    )

    # Optional flags and arguments
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=False,
        help="Scan directories recursively (default: False)",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        default=False,
        help="Perform a dry run without uploading to database (default: False)",
    )

    parser.add_argument(
        "--exclude",
        "-e",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Exclude files/directories matching pattern (can be used multiple times)",
    )

    parser.add_argument(
        "--db-config",
        type=str,
        default=None,
        metavar="CONFIG_FILE",
        help="Path to database configuration file (default: None)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose output (default: False)",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Combine user-provided exclude patterns with defaults
    # Start with defaults, then add user patterns to avoid duplicates
    combined_exclude = default_exclude_patterns.copy()
    for pattern in args.exclude:
        if pattern not in combined_exclude:
            combined_exclude.append(pattern)

    # Update the exclude list with combined patterns
    args.exclude = combined_exclude

    return args

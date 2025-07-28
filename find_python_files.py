from pathlib import Path
from typing import List


import pathspec


def find_python_files(
    directory: Path, recursive: bool, exclude_patterns: List[str]
) -> List[Path]:
    """
    Discover all Python source files in a directory, respecting exclusion rules.

    Traverses the specified directory to find all files with .py extension,
    optionally searching subdirectories recursively. Applies both default and
    user-specified exclusion patterns to filter out unwanted files and
    directories. Returns absolute paths sorted alphabetically for consistent
    processing order.

    The function handles various filesystem scenarios gracefully, including
    permission errors, symbolic links, and missing directories. It's designed
    to be robust against filesystem inconsistencies while gathering all
    accessible Python files.

    Args:
        directory: Path object pointing to the directory to scan. Can be
            relative or absolute; will be resolved to absolute internally.

        recursive: If True, searches all subdirectories recursively.
            If False, only searches the specified directory level.

        exclude_patterns: List of patterns to exclude from scanning. These are
            added to the default exclusions. Patterns can be:
            - Directory names (e.g., 'test', '__pycache__')
            - File patterns with wildcards (e.g., '*.backup', 'test_*')
            - Path fragments (excluded if pattern appears anywhere in path)

    Returns:
        List[Path]: Sorted list of absolute Path objects for discovered Python
            files. Each path:
            - Points to a file with .py extension (not .pyc, .pyx, etc.)
            - Is an absolute path for consistent handling
            - Is accessible for reading
            - Does not match any exclusion pattern
            Returns empty list if no files found or directory doesn't exist.

    Default Exclusions:
        The following directories are always excluded:
        - __pycache__ (Python bytecode cache)
        - .git (version control)
        - venv, .venv (virtual environments)
        - node_modules (JavaScript dependencies)
        - .pytest_cache (test framework cache)
        - build, dist (build artifacts)
        - .env* (environment directories)

    Example:
        # Scan single directory
        files = find_python_files(
            Path("src"),
            recursive=False,
            exclude_patterns=[]
        )

        # Recursive scan with custom exclusions
        files = find_python_files(
            Path("/home/user/project"),
            recursive=True,
            exclude_patterns=["*_test.py", "deprecated/"]
        )

        # Result might be:
        # [Path('/home/user/project/main.py'),
        #  Path('/home/user/project/utils/helpers.py')]

    Notes:
        - Only .py files are included; .pyc, .pyx, .pyi files are ignored
        - Symbolic links are followed; circular links are handled safely
        - Permission errors on subdirectories are silently skipped
        - File paths are sorted for deterministic processing order
        - Empty list is returned rather than None for "no files" case
    """
    # Convert to absolute path and check if directory exists
    try:
        abs_directory = Path(directory).resolve()
        if not abs_directory.exists() or not abs_directory.is_dir():
            return []
    except (OSError, RuntimeError):
        # Handle cases like broken symlinks or permission issues
        return []

    # Default exclusion patterns
    default_patterns = [
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
        ".env*",
        "python_embeded",
        "python_embedded",
        ".vscode",
        ".vs"
    ]

    # Combine default and custom patterns
    all_patterns = default_patterns + exclude_patterns

    # Create pathspec objects for each pattern
    pattern_specs = []
    for pattern in all_patterns:
        try:
            pattern_specs.append(pathspec.patterns.GitWildMatchPattern(pattern))
        except Exception:
            # Skip invalid patterns
            continue
    print(f"Using exclusion patterns: {all_patterns}")

    # Create pathspec object for pattern matching
    spec = pathspec.PathSpec(pattern_specs)

    python_files = []
    visited_dirs = set()  # Track visited directories to handle circular symlinks

    def _scan_directory(current_dir: Path, current_depth: int = 0):
        """Recursively scan directory for Python files."""
        try:
            # Resolve symlinks and check for circular references
            resolved_dir = current_dir.resolve()
            if resolved_dir in visited_dirs:
                return  # Skip circular symlinks
            visited_dirs.add(resolved_dir)

            # Check if current directory should be excluded
            relative_path = resolved_dir.relative_to(abs_directory)
            if spec.match_file(str(relative_path)):
                return

            # Get directory contents
            try:
                entries = list(current_dir.iterdir())
            except (PermissionError, OSError):
                # Skip directories we can't read
                return

            for entry in entries:
                try:
                    # Handle files
                    if entry.is_file() or entry.is_symlink():
                        # Check if it's a Python file
                        if entry.suffix == ".py":
                            # Check relative path against exclusion patterns
                            try:
                                if entry.is_symlink():
                                    # Resolve symlink to get actual file path
                                    entry_resolved = entry.readlink()
                                else:
                                    entry_resolved = entry.resolve()

                                if not entry_resolved.exists():
                                    continue

                                relative_entry_path = entry_resolved.relative_to(
                                    abs_directory
                                )

                                # Check if file matches exclusion patterns
                                if not spec.match_file(str(relative_entry_path)):
                                    python_files.append(entry_resolved)
                            except (ValueError, OSError):
                                # Skip files we can't process
                                continue

                    # Handle directories (if recursive)
                    elif entry.is_dir() and (recursive or current_depth == 0):
                        # Only recurse if recursive=True, or if we're at depth 0
                        # (to handle the initial directory scan)
                        if recursive or current_depth == 0:
                            _scan_directory(entry, current_depth + 1)
                    else:
                        print(f"Skipping non-file entry: {entry}")

                except (OSError, RuntimeError, RecursionError):
                    # Skip entries we can't access (broken symlinks, permission issues)
                    continue

        except (OSError, RuntimeError, RecursionError):
            # Skip directories we can't process
            return

    # Start scanning from the root directory
    if recursive:
        _scan_directory(abs_directory)
    else:
        # Non-recursive: only scan the immediate directory
        try:
            entries = list(abs_directory.iterdir())
            for entry in entries:
                try:
                    if entry.is_file() and entry.suffix == ".py":
                        # Check relative path against exclusion patterns
                        try:
                            entry_resolved = entry.resolve()
                            relative_entry_path = entry_resolved.relative_to(
                                abs_directory
                            )

                            # Check if file matches exclusion patterns
                            if not spec.match_file(str(relative_entry_path)):
                                python_files.append(entry_resolved)
                        except (ValueError, OSError):
                            continue
                except (OSError, RuntimeError, RecursionError):
                    continue
        except (PermissionError, OSError, RecursionError):
            # Can't read the directory
            return []

    # De-duplicate
    python_files = list(set(python_files))

    # Sort by full path string for consistent ordering
    python_files.sort(key=lambda p: str(p))

    return python_files

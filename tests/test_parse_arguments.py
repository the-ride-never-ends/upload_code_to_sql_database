import pytest


import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Import the function to test
from parse_arguments import parse_arguments


class TestParseArguments:
    """
    Test parse_arguments function for command line argument parsing.

    Test Methods:
    - test_parse_arguments_creates_argument_parser: ArgumentParser creation verification
    - test_parse_arguments_with_minimal_required_args: Required directory argument only
    - test_parse_arguments_with_recursive_flag: Recursive flag handling
    - test_parse_arguments_with_dry_run_flag: Dry run flag handling
    - test_parse_arguments_with_exclude_patterns: Multiple exclude patterns
    - test_parse_arguments_with_db_config: Database config file argument
    - test_parse_arguments_with_verbose_flag: Verbose flag handling
    - test_parse_arguments_with_all_options: All command line options combined
    - test_parse_arguments_directory_path_conversion: Path format conversion
    - test_parse_arguments_missing_required_directory: Missing required argument
    - test_parse_arguments_default_exclude_patterns: Default exclusion patterns
    """

    def test_parse_arguments_creates_argument_parser(self):
        """
        GIVEN parse_arguments function is called
        WHEN the function executes
        THEN expect:
            - ArgumentParser instance is created internally
            - Function does not raise any exceptions
        """
        with patch.object(sys, "argv", ["upload_code.py", "/test/path"]):
            result = parse_arguments()
            assert hasattr(result, "directory")
            assert hasattr(result, "recursive")
            assert hasattr(result, "dry_run")
            assert hasattr(result, "exclude")
            assert hasattr(result, "db_config")
            assert hasattr(result, "verbose")

    def test_parse_arguments_with_minimal_required_args(self):
        """
        GIVEN command line arguments contain only the required directory path
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path/to/scan']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.directory is a Path object pointing to '/path/to/scan'
            - namespace.recursive is False (default)
            - namespace.dry_run is False (default)
            - namespace.exclude is a list (default list of common non-code dirs)
            - namespace.db_config is None (default)
            - namespace.verbose is False (default)
        """
        with patch.object(sys, "argv", ["upload_code.py", "/path/to/scan"]):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path/to/scan")
            assert result.recursive is False
            assert result.dry_run is False
            assert isinstance(result.exclude, list)
            # Check that default exclusions are present
            expected_defaults = [
                "__pycache__",
                ".git",
                "venv",
                ".venv",
                "node_modules",
                ".pytest_cache",
                "build",
                "dist",
            ]
            for default in expected_defaults:
                assert default in result.exclude
            assert result.db_config is None
            assert result.verbose is False

    def test_parse_arguments_with_recursive_flag(self):
        """
        GIVEN command line arguments include --recursive flag
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path/to/scan', '--recursive']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.recursive is True
            - All other arguments have appropriate defaults
        """
        with patch.object(
            sys, "argv", ["upload_code.py", "/path/to/scan", "--recursive"]
        ):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path/to/scan")
            assert result.recursive is True
            assert result.dry_run is False
            assert isinstance(result.exclude, list)
            assert result.db_config is None
            assert result.verbose is False

    def test_parse_arguments_with_dry_run_flag(self):
        """
        GIVEN command line arguments include --dry-run flag
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path/to/scan', '--dry-run']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.dry_run is True
            - All other arguments have appropriate defaults
        """
        with patch.object(
            sys, "argv", ["upload_code.py", "/path/to/scan", "--dry-run"]
        ):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path/to/scan")
            assert result.recursive is False
            assert result.dry_run is True
            assert isinstance(result.exclude, list)
            assert result.db_config is None
            assert result.verbose is False

    def test_parse_arguments_with_exclude_patterns(self):
        """
        GIVEN command line arguments include --exclude with multiple patterns
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path', '--exclude', 'test_*', '*.bak']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.exclude is a list containing ['test_*', '*.bak'] plus default exclusions
            - Default exclusions include: __pycache__, .git, venv, .venv, node_modules, etc.
        """
        with patch.object(
            sys,
            "argv",
            ["upload_code.py", "/path", "--exclude", "test_*", "--exclude", "*.bak"],
        ):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path")
            assert isinstance(result.exclude, list)

            # Check user-provided exclusions are present
            assert "test_*" in result.exclude
            assert "*.bak" in result.exclude

            # Check default exclusions are still present
            expected_defaults = [
                "__pycache__",
                ".git",
                "venv",
                ".venv",
                "node_modules",
                ".pytest_cache",
                "build",
                "dist",
            ]
            for default in expected_defaults:
                assert default in result.exclude

    def test_parse_arguments_with_db_config(self):
        """
        GIVEN command line arguments include --db-config with a file path
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path', '--db-config', 'db.conf']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.db_config is 'db.conf' (string, not Path)
            - All other arguments have appropriate defaults
        """
        with patch.object(
            sys, "argv", ["upload_code.py", "/path", "--db-config", "db.conf"]
        ):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path")
            assert result.recursive is False
            assert result.dry_run is False
            assert isinstance(result.exclude, list)
            assert result.db_config == "db.conf"
            assert isinstance(result.db_config, str)
            assert result.verbose is False

    def test_parse_arguments_with_verbose_flag(self):
        """
        GIVEN command line arguments include --verbose flag
        WHEN parse_arguments is called with sys.argv = ['upload_code.py', '/path/to/scan', '--verbose']
        THEN expect:
            - Returns argparse.Namespace object
            - namespace.verbose is True
            - All other arguments have appropriate defaults
        """
        with patch.object(
            sys, "argv", ["upload_code.py", "/path/to/scan", "--verbose"]
        ):
            result = parse_arguments()

            assert isinstance(result.directory, Path)
            assert result.directory == Path("/path/to/scan")
            assert result.recursive is False
            assert result.dry_run is False
            assert isinstance(result.exclude, list)
            assert result.db_config is None
            assert result.verbose is True

    def test_parse_arguments_with_all_options(self):
        """
        GIVEN command line arguments include all possible options
        WHEN parse_arguments is called with all flags and options
        THEN expect:
            - Returns argparse.Namespace object with all options correctly set
            - directory is converted to Path object
            - All flags are boolean values
            - exclude is a list combining user patterns and defaults
        """
        argv = [
            "upload_code.py",
            "/project/path",
            "--recursive",
            "--dry-run",
            "--verbose",
            "--exclude",
            "temp_*",
            "--exclude",
            "*.log",
            "--db-config",
            "/etc/db.conf",
        ]

        with patch.object(sys, "argv", argv):
            result = parse_arguments()

            # Check directory conversion
            assert isinstance(result.directory, Path)
            assert result.directory == Path("/project/path")

            # Check all flags are boolean and set correctly
            assert result.recursive is True
            assert result.dry_run is True
            assert result.verbose is True

            # Check exclude list contains both user and default patterns
            assert isinstance(result.exclude, list)
            assert "temp_*" in result.exclude
            assert "*.log" in result.exclude
            expected_defaults = [
                "__pycache__",
                ".git",
                "venv",
                ".venv",
                "node_modules",
                ".pytest_cache",
                "build",
                "dist",
            ]
            for default in expected_defaults:
                assert default in result.exclude

            # Check db_config
            assert result.db_config == "/etc/db.conf"
            assert isinstance(result.db_config, str)

    def test_parse_arguments_directory_path_conversion(self):
        """
        GIVEN various directory path formats (relative, absolute, with ~)
        WHEN parse_arguments is called with different path formats
        THEN expect:
            - All paths are converted to Path objects
            - Relative paths remain relative
            - Absolute paths remain absolute
            - Tilde (~) expansion is handled if applicable
        """
        test_cases = [
            ("relative/path", "relative/path"),
            ("/absolute/path", "/absolute/path"),
            (
                "~/home/path",
                "~/home/path",
            ),  # Path object will handle tilde expansion when resolved
            (".", "."),
            ("..", ".."),
        ]

        for input_path, expected_str in test_cases:
            with patch.object(sys, "argv", ["upload_code.py", input_path]):
                result = parse_arguments()
                assert isinstance(result.directory, Path)
                assert str(result.directory) == expected_str

    def test_parse_arguments_missing_required_directory(self):
        """
        GIVEN command line arguments missing the required directory argument
        WHEN parse_arguments is called with sys.argv = ['upload_code.py']
        THEN expect:
            - SystemExit exception is raised (argparse behavior)
            - Error message indicates missing required argument
        """
        with patch.object(sys, "argv", ["upload_code.py"]):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()

            # SystemExit with code 2 typically indicates argument parsing error
            assert exc_info.value.code == 2

    def test_parse_arguments_default_exclude_patterns(self):
        """
        GIVEN no --exclude argument is provided
        WHEN parse_arguments is called
        THEN expect:
            - namespace.exclude contains default exclusion patterns
            - Default list includes at minimum: __pycache__, .git, venv, .venv,
              node_modules, .pytest_cache, build, dist
        """
        with patch.object(sys, "argv", ["upload_code.py", "/test/path"]):
            result = parse_arguments()

            assert isinstance(result.exclude, list)

            # Verify all expected default patterns are present
            expected_defaults = [
                "__pycache__",
                ".git",
                "venv",
                ".venv",
                "node_modules",
                ".pytest_cache",
                "build",
                "dist",
            ]

            for default_pattern in expected_defaults:
                assert (
                    default_pattern in result.exclude
                ), f"Expected default pattern '{default_pattern}' not found in exclude list"

            # Ensure it's actually a list and not empty
            assert len(result.exclude) >= len(expected_defaults)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

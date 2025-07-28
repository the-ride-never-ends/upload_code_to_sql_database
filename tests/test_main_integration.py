import pytest
from unittest.mock import Mock, patch
from argparse import Namespace
import mysql.connector
from pathlib import Path

from main import main
from upload_stats import UploadStats
from code_entry.create_code_entry import CodeEntry


class TestMainIntegrationSuccess:
    """
    Test successful end-to-end execution of main function.

    Test Methods:
    - test_main_successful_upload_workflow: Complete successful workflow
    - test_main_dry_run_workflow: Dry run mode execution
    - test_main_recursive_scan_with_exclusions: Recursive scanning with exclusions
    - test_main_duplicate_detection_workflow: Duplicate CID detection
    """

    @pytest.fixture
    def sample_python_files(self, tmp_path):
        """Create temporary Python files with documented callables."""
        # Create main project directory
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create utils module with documented function
        utils_py = project_dir / "utils.py"
        utils_py.write_text(
            '''
def process_data(items):
    """Process a list of items and return formatted results."""
    return [item.upper() for item in items]

class DataManager:
    """Manage data operations."""

    def __init__(self):
        self.data = []

    def add_item(self, item):
        """Add an item to the data store."""
        self.data.append(item)
'''
        )

        # Create helpers module
        helpers_py = project_dir / "helpers.py"
        helpers_py.write_text(
            '''
async def fetch_data(url):
    """Asynchronously fetch data from URL."""
    return f"Data from {url}"

def _private_helper():
    # No docstring - should be skipped
    pass
'''
        )

        return project_dir

    @pytest.fixture
    def mock_database_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock the count query for summary report
        mock_cursor.fetchone.return_value = (1250,)

        return mock_conn

    @pytest.fixture
    def expected_callables(self):
        """Expected callable information that would be extracted."""
        return [
            {
                "name": "process_data",
                "type": "function",
                "signature": "def process_data(items):",
                "docstring": "Process a list of items and return formatted results.",
                "source_code": 'def process_data(items):\n    """Process a list of items and return formatted results."""\n    return [item.upper() for item in items]',
                "line_number": 2,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "DataManager",
                "type": "class",
                "signature": "class DataManager:",
                "docstring": "Manage data operations.",
                "source_code": 'class DataManager:\n    """Manage data operations."""\n    \n    def __init__(self):\n        self.data = []\n        \n    def add_item(self, item):\n        """Add an item to the data store."""\n        self.data.append(item)',
                "line_number": 5,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "fetch_data",
                "type": "coroutine",
                "signature": "async def fetch_data(url):",
                "docstring": "Asynchronously fetch data from URL.",
                "source_code": 'async def fetch_data(url):\n    """Asynchronously fetch data from URL."""\n    return f"Data from {url}"',
                "line_number": 2,
                "is_async": True,
                "decorators": [],
            },
        ]

    def test_main_successful_upload_workflow(
        self,
        tmp_path,
        sample_python_files,
        mock_database_connection,
        expected_callables,
    ):
        """
        GIVEN a valid directory with Python files containing documented callables
        AND a working database connection
        AND valid command line arguments
        WHEN main() is executed
        THEN expect:
            - Arguments are parsed successfully
            - Database connection is established
            - Python files are discovered
            - Callables are extracted and validated
            - Code entries are created with CIDs
            - Duplicate checking is performed
            - Valid entries are uploaded to database
            - Summary report is generated
            - Return code is 0 (success)
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files), "--verbose"]

        expected_files = [
            sample_python_files / "utils.py",
            sample_python_files / "helpers.py",
        ]

        expected_code_entries = [
            CodeEntry(
                cid="bafkreicid1test",
                signature=callable_info["signature"],
                docstring=callable_info["docstring"],
                computer_code=callable_info["source_code"],
                metadata={
                    "cid": "bafkreimetadatacid1",  # metadata CID
                    "code_cid": "bafkreicid1test",
                    "code_name": callable_info["name"],
                    "code_type": callable_info["type"],
                    "is_test": False,
                    "file_path": "test_project/utils.py",
                    "tags": ["test_project"],
                },
            )
            for callable_info in expected_callables[:2]  # Only utils.py callables
        ]

        # Add helpers.py entry
        expected_code_entries.append(
            CodeEntry(
                cid="bafkreicid2test",
                signature=expected_callables[2]["signature"],
                docstring=expected_callables[2]["docstring"],
                computer_code=expected_callables[2]["source_code"],
                metadata={
                    "cid": "bafkreimetadatacid2",  # metadata CID
                    "code_cid": "bafkreicid2test",
                    "code_name": expected_callables[2]["name"],
                    "code_type": expected_callables[2]["type"],
                    "is_test": False,
                    "file_path": "test_project/helpers.py",
                    "tags": ["test_project"],
                },
            )
        )

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=True,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = expected_files

            # Mock callables extraction
            mock_get_callables.side_effect = [
                expected_callables[:2],  # utils.py
                expected_callables[2:],  # helpers.py
            ]

            # Mock validation - all callables are valid
            mock_validate.return_value = None

            # Mock CID creation
            mock_create_entry.side_effect = expected_code_entries

            # Mock CID checking - no duplicates
            mock_check_cid.return_value = False

            # Mock upload - no exceptions
            mock_upload.return_value = None

            # Act
            result = main()

            # Assert
            assert result == 0, "Main should return 0 for successful execution"

            # Verify argument parsing was called
            mock_parse_args.assert_called_once()

            # Verify database connection
            mock_start_db.assert_called_once_with(None)

            # Verify file discovery
            mock_find_files.assert_called_once_with(
                directory=sample_python_files, recursive=False, exclude_patterns=[]
            )

            # Verify callables extraction for each file
            assert mock_get_callables.call_count == 2
            mock_get_callables.assert_any_call(expected_files[0])
            mock_get_callables.assert_any_call(expected_files[1])

            # Verify validation calls
            assert mock_validate.call_count == 3  # 3 valid callables

            # Verify CID creation calls
            assert mock_create_entry.call_count == 3

            # Verify duplicate checking
            assert mock_check_cid.call_count == 3

            # Verify uploads
            assert mock_upload.call_count == 3

            # Verify summary report generation
            mock_summary.assert_called_once()
            summary_args = mock_summary.call_args[0]
            stats = summary_args[0]

            # Check statistics
            assert isinstance(stats, UploadStats)
            assert stats.files_scanned == 2
            assert stats.callables_found == 3
            assert stats.new_uploads == 3
            assert stats.skipped_duplicates == 0
            assert len(stats.errors) == 0

    def test_main_dry_run_workflow(
        self,
        tmp_path,
        sample_python_files,
        mock_database_connection,
        expected_callables,
    ):
        """
        GIVEN valid directory with Python files
        AND --dry-run flag is set
        WHEN main() is executed
        THEN expect:
            - All processing steps occur except database writes
            - CIDs are generated but not uploaded
            - Summary shows what would be uploaded
            - No database modifications are made
            - Return code is 0 (success)
        """
        # Arrange
        test_args = [
            "upload_code.py",
            str(sample_python_files),
            "--dry-run",
            "--verbose",
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=True,  # Key difference: dry run mode
                exclude=[],
                db_config=None,
                verbose=True,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [sample_python_files / "utils.py"]
            mock_get_callables.return_value = expected_callables[:1]
            mock_validate.return_value = None

            # Mock code entry creation
            mock_create_entry.return_value = CodeEntry(
                cid="bafkreitestcid",
                signature="def test_func():",
                docstring="Test function",
                computer_code="def test_func():\n    pass",
                metadata={
                    "cid": "bafkreimetadatacidtest",  # metadata CID
                    "code_cid": "bafkreitestcid",
                    "code_name": "test_func",
                    "code_type": "function",
                    "is_test": False,
                    "file_path": "test.py",
                    "tags": [],
                },
            )

            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Dry run should return 0 for success"

            # Verify processing occurred
            mock_parse_args.assert_called_once()
            mock_start_db.assert_called_once()
            mock_find_files.assert_called_once()
            mock_get_callables.assert_called_once()
            mock_validate.assert_called_once()
            mock_create_entry.assert_called_once()
            mock_check_cid.assert_called_once()

            # Verify NO actual uploads occurred in dry run
            mock_upload.assert_not_called()

            # Verify summary was generated
            mock_summary.assert_called_once()

    def test_main_recursive_scan_with_exclusions(
        self, tmp_path, mock_database_connection
    ):
        """
        GIVEN directory structure with subdirectories
        AND --recursive flag is set
        AND --exclude patterns are provided
        WHEN main() is executed
        THEN expect:
            - All subdirectories are scanned recursively
            - Files matching exclusion patterns are skipped
            - Only valid Python files are processed
            - Summary reflects recursive scan results
            - Return code is 0 (success)
        """
        # Arrange
        project_dir = tmp_path / "recursive_project"
        project_dir.mkdir()

        # Create nested structure
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()
        (project_dir / "excluded_dir").mkdir()

        # Create files in different directories
        (project_dir / "main.py").write_text(
            'def main():\n    """Main function."""\n    pass'
        )
        (project_dir / "src" / "utils.py").write_text(
            'def util():\n    """Utility function."""\n    pass'
        )
        (project_dir / "tests" / "test_main.py").write_text(
            'def test_main():\n    """Test main."""\n    pass'
        )
        (project_dir / "excluded_dir" / "exclude_me.py").write_text(
            'def excluded():\n    """Should be excluded."""\n    pass'
        )

        test_args = [
            "upload_code.py",
            str(project_dir),
            "--recursive",
            "--exclude",
            "excluded_dir/*",
            "--exclude",
            "*test*",
        ]

        expected_files = [project_dir / "main.py", project_dir / "src" / "utils.py"]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=project_dir,
                recursive=True,
                dry_run=False,
                exclude=["excluded_dir/*", "*test*"],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = expected_files
            mock_get_callables.return_value = [
                {
                    "name": "test_func",
                    "type": "function",
                    "signature": "def test_func():",
                    "docstring": "Test function",
                    "source_code": "def test_func():\n    pass",
                    "line_number": 1,
                    "is_async": False,
                    "decorators": [],
                }
            ]
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0

            # Verify recursive scanning with exclusions
            mock_find_files.assert_called_once_with(
                directory=project_dir,
                recursive=True,
                exclude_patterns=["excluded_dir/*", "*test*"],
            )

            # Verify files were processed (should be 2 files)
            assert mock_get_callables.call_count == len(expected_files)

    def test_main_duplicate_detection_workflow(
        self,
        tmp_path,
        sample_python_files,
        mock_database_connection,
        expected_callables,
    ):
        """
        GIVEN directory with Python files containing callables
        AND some callables already exist in database (same CID)
        WHEN main() is executed
        THEN expect:
            - Duplicate CIDs are detected
            - Duplicates are skipped from upload
            - Only new code entries are uploaded
            - Statistics show duplicate counts
            - Return code is 0 (success)
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files)]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [sample_python_files / "utils.py"]
            mock_get_callables.return_value = expected_callables[:2]  # 2 callables
            mock_validate.return_value = None

            # Mock code entries
            mock_entries = [Mock(), Mock()]
            mock_entries[0].cid = "bafkreiduplicate1"
            mock_entries[0].metadata = {"cid": "bafkreimetadata1"}
            mock_entries[1].cid = "bafkreinew1"
            mock_entries[1].metadata = {"cid": "bafkreimetadata2"}
            mock_create_entry.side_effect = mock_entries

            # First CID exists (duplicate), second is new
            mock_check_cid.side_effect = [True, False]

            # Act
            result = main()

            # Assert
            assert result == 0

            # Verify CID checking was done for both entries (checking metadata CIDs)
            assert mock_check_cid.call_count == 2
            mock_check_cid.assert_any_call(mock_database_connection, "bafkreimetadata1")
            mock_check_cid.assert_any_call(mock_database_connection, "bafkreimetadata2")

            # Verify only the new entry was uploaded
            mock_upload.assert_called_once_with(
                mock_database_connection, mock_entries[1]
            )

            # Verify statistics tracking
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            assert stats.skipped_duplicates == 1
            assert stats.new_uploads == 1


class TestMainIntegrationErrors:
    """
    Test error handling and failure scenarios in main function.

    Test Methods:
    - test_main_database_connection_failure: Database connection error handling
    - test_main_no_python_files_found: No Python files found scenario
    - test_main_syntax_errors_in_files: Syntax error handling in source files
    - test_main_upload_failures_mixed_results: Mixed upload success/failure results
    - test_main_keyboard_interrupt_handling: Keyboard interrupt handling
    """

    @pytest.fixture
    def sample_python_files(self, tmp_path):
        """Create temporary Python files for error testing."""
        project_dir = tmp_path / "error_project"
        project_dir.mkdir()

        # Create a valid file
        valid_py = project_dir / "valid.py"
        valid_py.write_text(
            '''
def valid_function():
    """A valid function with docstring."""
    return "valid"
'''
        )

        # Create a file with syntax errors
        syntax_error_py = project_dir / "syntax_error.py"
        syntax_error_py.write_text(
            '''
def invalid_syntax(
    """Missing closing parenthesis."""
    return "invalid"
'''
        )

        return project_dir

    @pytest.fixture
    def mock_valid_callables(self):
        """Mock valid callable data."""
        return [
            {
                "name": "valid_function",
                "type": "function",
                "signature": "def valid_function():",
                "docstring": "A valid function with docstring.",
                "source_code": 'def valid_function():\n    """A valid function with docstring."""\n    return "valid"',
                "line_number": 2,
                "is_async": False,
                "decorators": [],
            }
        ]

    def test_main_database_connection_failure(self, tmp_path, sample_python_files):
        """
        GIVEN valid command line arguments
        AND database connection fails
        WHEN main() is executed
        THEN expect:
            - Database connection error is caught
            - Error message is printed to stdout
            - Return code is 2 (failure)
            - No file processing occurs
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files)]

        database_error = mysql.connector.Error("Connection failed: Host unreachable")

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            # Database connection fails
            mock_start_db.side_effect = database_error

            # Act
            result = main()

            # Assert
            assert result == 2, "Should return 2 for database connection failure"

            # Verify database connection was attempted
            mock_start_db.assert_called_once_with(None)

            # Verify error message was printed
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            error_messages = [
                msg for msg in print_calls if "Connection failed" in str(msg)
            ]
            assert len(error_messages) > 0, "Should print database connection error"

            # Verify no file processing occurred
            mock_find_files.assert_not_called()

    def test_main_no_python_files_found(self, tmp_path, mock_valid_callables):
        """
        GIVEN valid directory that contains no Python files
        AND successful database connection
        WHEN main() is executed
        THEN expect:
            - File discovery returns empty list
            - "No Python files found" message is printed
            - Return code is 0 (success)
            - No database operations are performed
        """
        # Arrange
        empty_dir = tmp_path / "empty_project"
        empty_dir.mkdir()

        test_args = ["upload_code.py", str(empty_dir)]

        mock_database = Mock()

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=empty_dir,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database
            # No Python files found
            mock_find_files.return_value = []

            # Act
            result = main()

            # Assert
            assert (
                result == 0
            ), "Should return 0 for successful execution (even with no files)"

            # Verify file discovery was attempted
            mock_find_files.assert_called_once_with(
                directory=empty_dir, recursive=False, exclude_patterns=[]
            )

            # Verify "No Python files found" message
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            no_files_messages = [
                msg for msg in print_calls if "No Python files found" in str(msg)
            ]
            assert (
                len(no_files_messages) > 0
            ), "Should print 'No Python files found' message"

            # Verify no callable processing occurred
            mock_get_callables.assert_not_called()
            mock_upload.assert_not_called()

    def test_main_syntax_errors_in_files(
        self, tmp_path, sample_python_files, mock_valid_callables
    ):
        """
        GIVEN directory containing Python files with syntax errors
        AND some valid Python files
        WHEN main() is executed
        THEN expect:
            - Syntax errors are caught and logged
            - Valid files continue to be processed
            - Parse errors are included in statistics
            - Return code is 1 (partial success)
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files), "--verbose"]

        mock_database = Mock()

        # Files to process
        valid_file = sample_python_files / "valid.py"
        syntax_error_file = sample_python_files / "syntax_error.py"

        syntax_error = SyntaxError(
            "invalid syntax", ("syntax_error.py", 2, 1, "def invalid_syntax(")
        )

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=True,
            )

            mock_start_db.return_value = mock_database
            mock_find_files.return_value = [valid_file, syntax_error_file]

            # First file succeeds, second file has syntax error
            mock_get_callables.side_effect = [
                mock_valid_callables,  # valid.py
                syntax_error,  # syntax_error.py
            ]

            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreitestcid", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert (
                result == 1
            ), "Should return 1 for partial success (some errors occurred)"

            # Verify both files were attempted
            assert mock_get_callables.call_count == 2
            mock_get_callables.assert_any_call(valid_file)
            mock_get_callables.assert_any_call(syntax_error_file)

            # Verify valid file was processed successfully
            mock_validate.assert_called_once()
            mock_create_entry.assert_called_once()
            mock_upload.assert_called_once()

            # Verify summary includes parse error
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            assert stats.files_scanned == 2
            assert len(stats.parse_errors) == 1
            assert stats.parse_errors[0][0] == syntax_error_file
            assert "invalid syntax" in stats.parse_errors[0][1]

    def test_main_upload_failures_mixed_results(
        self, tmp_path, sample_python_files, mock_valid_callables
    ):
        """
        GIVEN directory with valid Python files
        AND database connection works for some uploads but fails for others
        WHEN main() is executed
        THEN expect:
            - Some uploads succeed
            - Some uploads fail with logged errors
            - Error details are collected in statistics
            - Return code is 1 (partial success)
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files)]

        mock_database = Mock()
        valid_file = sample_python_files / "valid.py"

        # Create multiple callables to test mixed upload results
        multiple_callables = [
            {
                "name": "success_function",
                "type": "function",
                "signature": "def success_function():",
                "docstring": "This will upload successfully.",
                "source_code": "def success_function():\n    pass",
                "line_number": 1,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "failure_function",
                "type": "function",
                "signature": "def failure_function():",
                "docstring": "This will fail to upload.",
                "source_code": "def failure_function():\n    pass",
                "line_number": 5,
                "is_async": False,
                "decorators": [],
            },
        ]

        upload_error = mysql.connector.DataError(
            "Data too long for column 'computer_code'"
        )

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database
            mock_find_files.return_value = [valid_file]
            mock_get_callables.return_value = multiple_callables
            mock_validate.return_value = None

            # Mock code entries
            mock_entries = [Mock(), Mock()]
            mock_entries[0].cid = "bafkreisuccess1"
            mock_entries[0].metadata = {"cid": "bafkreimetadata1"}
            mock_entries[1].cid = "bafkreifailure1"
            mock_entries[1].metadata = {"cid": "bafkreimetadata2"}
            mock_create_entry.side_effect = mock_entries

            mock_check_cid.return_value = False

            # First upload succeeds, second fails
            mock_upload.side_effect = [None, upload_error]

            # Act
            result = main()

            # Assert
            assert (
                result == 1
            ), "Should return 1 for partial success (some uploads failed)"

            # Verify both uploads were attempted
            assert mock_upload.call_count == 2

            # Verify summary includes upload error
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            assert stats.new_uploads == 1  # One succeeded
            assert len(stats.errors) == 1  # One failed
            assert stats.errors[0]["callable"] == "failure_function"
            assert "Data too long" in stats.errors[0]["error"]

    def test_main_keyboard_interrupt_handling(self, tmp_path, sample_python_files):
        """
        GIVEN main() is executing
        WHEN KeyboardInterrupt is raised during processing
        THEN expect:
            - Interrupt is caught at module level
            - "Process interrupted by user" message is printed
            - Return code is 1
            - Clean exit without traceback
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_python_files)]

        mock_database = Mock()

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_python_files,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database

            # Simulate KeyboardInterrupt during file discovery
            mock_find_files.side_effect = KeyboardInterrupt()

            # Act
            result = main()

            # Assert
            assert result == 1, "Should return 1 for keyboard interrupt"

            # Verify interrupt message was printed
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            interrupt_messages = [
                msg for msg in print_calls if "interrupted" in str(msg).lower()
            ]
            assert len(interrupt_messages) > 0, "Should print interruption message"


class TestMainIntegrationEdgeCases:
    """
    Test edge cases and boundary conditions in main function.

    Test Methods:
    - test_main_all_callables_skipped: All callables skipped during validation
    - test_main_all_duplicates_scenario: All callables are duplicates
    - test_main_empty_directory: Completely empty directory
    - test_main_custom_database_config: Custom database configuration usage
    """

    @pytest.fixture
    def mock_database_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1000,)
        return mock_conn

    def test_main_all_callables_skipped(self, tmp_path, mock_database_connection):
        """
        GIVEN directory with Python files containing only callables without docstrings
        OR only methods/nested functions
        WHEN main() is executed
        THEN expect:
            - All callables are found but skipped during validation
            - No uploads occur
            - Statistics show all skipped categories
            - Return code is 0 (success)
        """
        # Arrange
        project_dir = tmp_path / "skip_all_project"
        project_dir.mkdir()

        # Create file with undocumented callables and methods
        skip_file = project_dir / "skip_all.py"
        skip_file.write_text(
            '''
def no_docstring_function():
    return "no docs"

class TestClass:
    def method_function(self):
        """This is a method, should be skipped."""
        return "method"

    def _private_method(self):
        return "private"

def nested_container():
    def nested_function():
        """Nested function should be skipped."""
        return "nested"
    return nested_function
'''
        )

        test_args = ["upload_code.py", str(project_dir)]

        # Mock callables that will all be skipped
        all_skipped_callables = [
            {
                "name": "no_docstring_function",
                "type": "function",
                "signature": "def no_docstring_function():",
                "docstring": None,  # No docstring
                "source_code": 'def no_docstring_function():\n    return "no docs"',
                "line_number": 2,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "TestClass",
                "type": "class",
                "signature": "class TestClass:",
                "docstring": None,  # No docstring
                "source_code": "class TestClass:\n    def method_function(self):\n        ...",
                "line_number": 4,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "nested_container",
                "type": "function",
                "signature": "def nested_container():",
                "docstring": None,  # No docstring
                "source_code": "def nested_container():\n    def nested_function():\n        ...",
                "line_number": 11,
                "is_async": False,
                "decorators": [],
            },
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=project_dir,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [skip_file]
            mock_get_callables.return_value = all_skipped_callables

            # All callables will be skipped for various reasons
            mock_validate.side_effect = [
                "no_docstring",  # First callable: no docstring
                "no_docstring",  # Second callable: no docstring
                "no_docstring",  # Third callable: no docstring
            ]

            # Act
            result = main()

            # Assert
            assert (
                result == 0
            ), "Should return 0 for success even when all callables skipped"

            # Verify all callables were found and validated
            assert mock_validate.call_count == 3

            # Verify no code entries were created or uploaded
            mock_create_entry.assert_not_called()
            mock_upload.assert_not_called()

            # Verify statistics show all skips
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            assert stats.files_scanned == 1
            assert stats.callables_found == 3
            assert stats.skipped_no_docstring == 3
            assert stats.new_uploads == 0

    def test_main_all_duplicates_scenario(self, tmp_path, mock_database_connection):
        """
        GIVEN directory with Python files containing valid callables
        AND all callables already exist in database (all duplicates)
        WHEN main() is executed
        THEN expect:
            - All CIDs are found to exist in database
            - No new uploads occur
            - Statistics show all as duplicates
            - Return code is 0 (success)
        """
        # Arrange
        project_dir = tmp_path / "all_duplicates_project"
        project_dir.mkdir()

        duplicates_file = project_dir / "duplicates.py"
        duplicates_file.write_text(
            '''
def existing_function():
    """This function already exists in database."""
    return "duplicate"

class ExistingClass:
    """This class already exists in database."""
    pass
'''
        )

        test_args = ["upload_code.py", str(project_dir)]

        duplicate_callables = [
            {
                "name": "existing_function",
                "type": "function",
                "signature": "def existing_function():",
                "docstring": "This function already exists in database.",
                "source_code": 'def existing_function():\n    """This function already exists in database."""\n    return "duplicate"',
                "line_number": 2,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "ExistingClass",
                "type": "class",
                "signature": "class ExistingClass:",
                "docstring": "This class already exists in database.",
                "source_code": 'class ExistingClass:\n    """This class already exists in database."""\n    pass',
                "line_number": 6,
                "is_async": False,
                "decorators": [],
            },
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=project_dir,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [duplicates_file]
            mock_get_callables.return_value = duplicate_callables
            mock_validate.return_value = None  # All are valid

            # Mock code entries
            mock_entries = [Mock(), Mock()]
            mock_entries[0].cid = "bafkreiexisting1"
            mock_entries[0].metadata = {"cid": "bafkreiexistingmeta1"}
            mock_entries[1].cid = "bafkreiexisting2"
            mock_entries[1].metadata = {"cid": "bafkreiexistingmeta2"}
            mock_create_entry.side_effect = mock_entries

            # All CIDs already exist in database
            mock_check_cid.return_value = True

            # Act
            result = main()

            # Assert
            assert (
                result == 0
            ), "Should return 0 for success even when all are duplicates"

            # Verify CID checking for all entries
            assert mock_check_cid.call_count == 2

            # Verify no uploads occurred (all duplicates)
            mock_upload.assert_not_called()

            # Verify statistics show all duplicates
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            assert stats.callables_found == 2
            assert stats.skipped_duplicates == 2
            assert stats.new_uploads == 0

    def test_main_empty_directory(self, tmp_path, mock_database_connection):
        """
        GIVEN completely empty directory
        WHEN main() is executed
        THEN expect:
            - File discovery returns empty list
            - "No Python files found" message is displayed
            - Return code is 0 (success)
            - No database operations occur
        """
        # Arrange
        empty_dir = tmp_path / "completely_empty"
        empty_dir.mkdir()

        test_args = ["upload_code.py", str(empty_dir)]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=empty_dir,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = []  # No files found

            # Act
            result = main()

            # Assert
            assert (
                result == 0
            ), "Should return 0 for success (empty directory is not an error)"

            # Verify file discovery was attempted
            mock_find_files.assert_called_once_with(
                directory=empty_dir, recursive=False, exclude_patterns=[]
            )

            # Verify no callables processing occurred
            mock_get_callables.assert_not_called()
            mock_upload.assert_not_called()

            # Verify empty directory message
            mock_print.assert_called()
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            no_files_messages = [
                msg for msg in print_calls if "No Python files found" in str(msg)
            ]
            assert (
                len(no_files_messages) > 0
            ), "Should print 'No Python files found' message"

    def test_main_custom_database_config(self, tmp_path, mock_database_connection):
        """
        GIVEN custom database configuration file path in arguments
        AND configuration file exists and is valid
        WHEN main() is executed
        THEN expect:
            - Custom config is passed to start_database()
            - Database connection uses custom settings
            - Normal workflow continues with custom connection
            - Return code is 0 (success)
        """
        # Arrange
        project_dir = tmp_path / "config_project"
        project_dir.mkdir()

        # Create config file
        config_file = tmp_path / "custom_db.ini"
        config_file.write_text(
            """
[database]
host = custom_host
user = custom_user
password = custom_pass
database = custom_db
port = 3307
"""
        )

        # Create simple Python file
        simple_py = project_dir / "simple.py"
        simple_py.write_text(
            '''
def simple_function():
    """A simple function for config testing."""
    return "simple"
'''
        )

        test_args = [
            "upload_code.py",
            str(project_dir),
            "--db-config",
            str(config_file),
        ]

        simple_callable = [
            {
                "name": "simple_function",
                "type": "function",
                "signature": "def simple_function():",
                "docstring": "A simple function for config testing.",
                "source_code": 'def simple_function():\n    """A simple function for config testing."""\n    return "simple"',
                "line_number": 2,
                "is_async": False,
                "decorators": [],
            }
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=project_dir,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=str(config_file),  # Custom config path
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [simple_py]
            mock_get_callables.return_value = simple_callable
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreicustomtest", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for success with custom config"

            # Verify custom config was passed to start_database
            mock_start_db.assert_called_once_with(str(config_file))

            # Verify normal workflow continued
            mock_find_files.assert_called_once()
            mock_get_callables.assert_called_once()
            mock_upload.assert_called_once()
            mock_summary.assert_called_once()


class TestMainIntegrationStatistics:
    """
    Test statistics tracking and reporting in main function.

    Test Methods:
    - test_main_statistics_accumulation: Statistics collection across mixed scenarios
    - test_main_verbose_output_integration: Verbose mode output verification
    """

    @pytest.fixture
    def complex_project(self, tmp_path):
        """Create a complex project structure with mixed content."""
        project_dir = tmp_path / "complex_project"
        project_dir.mkdir()

        # Valid file with documented callables
        valid_py = project_dir / "valid.py"
        valid_py.write_text(
            '''
def documented_function():
    """A properly documented function."""
    return "documented"

class DocumentedClass:
    """A properly documented class."""

    def method(self):
        """This method should be skipped (not standalone)."""
        return "method"
'''
        )

        # File with syntax errors
        syntax_error_py = project_dir / "syntax_error.py"
        syntax_error_py.write_text(
            '''
def broken_function(
    """Missing closing parenthesis."""
    return "broken"
'''
        )

        # File with undocumented callables
        undocumented_py = project_dir / "undocumented.py"
        undocumented_py.write_text(
            '''
def no_docs():
    return "no documentation"

class AlsoNoDocs:
    pass

def has_docs():
    """This one has documentation."""
    return "documented"
'''
        )

        return project_dir

    @pytest.fixture
    def mock_database_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1500,)  # Total count in database
        return mock_conn

    @pytest.fixture
    def expected_complex_callables(self):
        """Expected callables from complex project."""
        return {
            "valid.py": [
                {
                    "name": "documented_function",
                    "type": "function",
                    "signature": "def documented_function():",
                    "docstring": "A properly documented function.",
                    "source_code": 'def documented_function():\n    """A properly documented function."""\n    return "documented"',
                    "line_number": 2,
                    "is_async": False,
                    "decorators": [],
                },
                {
                    "name": "DocumentedClass",
                    "type": "class",
                    "signature": "class DocumentedClass:",
                    "docstring": "A properly documented class.",
                    "source_code": 'class DocumentedClass:\n    """A properly documented class."""\n    \n    def method(self):\n        """This method should be skipped (not standalone)."""\n        return "method"',
                    "line_number": 5,
                    "is_async": False,
                    "decorators": [],
                },
            ],
            "undocumented.py": [
                {
                    "name": "no_docs",
                    "type": "function",
                    "signature": "def no_docs():",
                    "docstring": None,
                    "source_code": 'def no_docs():\n    return "no documentation"',
                    "line_number": 2,
                    "is_async": False,
                    "decorators": [],
                },
                {
                    "name": "AlsoNoDocs",
                    "type": "class",
                    "signature": "class AlsoNoDocs:",
                    "docstring": None,
                    "source_code": "class AlsoNoDocs:\n    pass",
                    "line_number": 5,
                    "is_async": False,
                    "decorators": [],
                },
                {
                    "name": "has_docs",
                    "type": "function",
                    "signature": "def has_docs():",
                    "docstring": "This one has documentation.",
                    "source_code": 'def has_docs():\n    """This one has documentation."""\n    return "documented"',
                    "line_number": 8,
                    "is_async": False,
                    "decorators": [],
                },
            ],
        }

    def test_main_statistics_accumulation(
        self,
        tmp_path,
        complex_project,
        mock_database_connection,
        expected_complex_callables,
    ):
        """
        GIVEN directory with mixed content (valid files, syntax errors, various callable types)
        WHEN main() is executed
        THEN expect:
            - UploadStats tracks all categories correctly
            - files_scanned matches discovered file count
            - callables_found includes all found callables
            - Skip categories sum correctly
            - Error counts match actual errors
            - Statistics are passed to generate_summary_report()
        """
        # Arrange
        test_args = ["upload_code.py", str(complex_project), "--verbose"]

        files_to_process = [
            complex_project / "valid.py",
            complex_project / "syntax_error.py",
            complex_project / "undocumented.py",
        ]

        syntax_error = SyntaxError(
            "invalid syntax", ("syntax_error.py", 2, 1, "def broken_function(")
        )
        upload_error = mysql.connector.DataError("Data too long for column")

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=complex_project,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=True,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = files_to_process

            # Mock callables extraction with mixed results
            mock_get_callables.side_effect = [
                expected_complex_callables["valid.py"],  # valid.py: 2 callables
                syntax_error,  # syntax_error.py: parse error
                expected_complex_callables[
                    "undocumented.py"
                ],  # undocumented.py: 3 callables
            ]

            # Mock validation results: some pass, some fail
            mock_validate.side_effect = [
                None,  # documented_function: valid
                None,  # DocumentedClass: valid
                "no_docstring",  # no_docs: no docstring
                "no_docstring",  # AlsoNoDocs: no docstring
                None,  # has_docs: valid
            ]

            # Mock code entries for valid callables
            mock_entries = [Mock(), Mock(), Mock()]
            mock_entries[0].cid = "bafkreivalid1"
            mock_entries[0].metadata = {"cid": "bafkreimeta1"}
            mock_entries[1].cid = "bafkreivalid2"
            mock_entries[1].metadata = {"cid": "bafkreimeta2"}
            mock_entries[2].cid = "bafkreivalid3"
            mock_entries[2].metadata = {"cid": "bafkreimeta3"}
            mock_create_entry.side_effect = mock_entries

            # Mock CID checking: first is duplicate, others are new
            mock_check_cid.side_effect = [True, False, False]

            # Mock uploads: one succeeds, one fails
            mock_upload.side_effect = [None, upload_error]

            # Act
            result = main()

            # Assert
            assert result == 1, "Should return 1 for partial success (has errors)"

            # Verify summary was called with correct statistics
            mock_summary.assert_called_once()
            stats = mock_summary.call_args[0][0]
            db_conn = mock_summary.call_args[0][1]

            # Verify statistics accumulation
            assert isinstance(stats, UploadStats), "Should pass UploadStats object"
            assert stats.files_scanned == 3, "Should scan all 3 files"
            assert stats.callables_found == 5, "Should find 5 total callables (2 + 3)"
            assert (
                stats.skipped_no_docstring == 2
            ), "Should skip 2 undocumented callables"
            assert stats.skipped_duplicates == 1, "Should skip 1 duplicate"
            assert stats.new_uploads == 1, "Should upload 1 new entry successfully"
            assert len(stats.errors) == 1, "Should have 1 upload error"
            assert len(stats.parse_errors) == 1, "Should have 1 parse error"

            # Verify error details
            assert stats.parse_errors[0][0] == complex_project / "syntax_error.py"
            assert "invalid syntax" in stats.parse_errors[0][1]
            assert "Data too long" in stats.errors[0]["error"]

            # Verify database connection passed to summary
            assert db_conn == mock_database_connection

    def test_main_verbose_output_integration(
        self,
        tmp_path,
        complex_project,
        mock_database_connection,
        expected_complex_callables,
    ):
        """
        GIVEN --verbose flag is set in arguments
        WHEN main() is executed
        THEN expect:
            - Detailed processing information is displayed
            - Each file processing decision is shown
            - Callable validation results are verbose
            - Additional debug information is printed
            - Summary report includes verbose details
        """
        # Arrange
        test_args = ["upload_code.py", str(complex_project), "--verbose"]

        files_to_process = [complex_project / "valid.py"]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=complex_project,
                recursive=False,
                dry_run=False,
                exclude=[],
                db_config=None,
                verbose=True,  # Verbose mode enabled
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = files_to_process
            mock_get_callables.return_value = expected_complex_callables["valid.py"][
                :1
            ]  # Just one callable
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreiverbosetest", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for success"

            # Verify verbose output was printed
            mock_print.assert_called()
            print_calls = [str(call[0][0]) for call in mock_print.call_args_list]

            # Check for verbose-specific output patterns
            verbose_indicators = [
                call
                for call in print_calls
                if any(
                    keyword in call.lower()
                    for keyword in [
                        "processing",
                        "found",
                        "validating",
                        "uploading",
                        "scanning",
                    ]
                )
            ]
            assert (
                len(verbose_indicators) > 0
            ), "Should print verbose processing information"

            # Verify arguments were parsed with verbose=True
            parsed_args = mock_parse_args.return_value
            assert (
                parsed_args.verbose == True
            ), "Verbose flag should be parsed correctly"


class TestMainIntegrationArgumentHandling:
    """
    Test command line argument parsing and handling integration.

    Test Methods:
    - test_main_with_all_optional_arguments: All optional arguments specified
    - test_main_with_minimal_arguments: Only required arguments provided
    - test_main_multiple_exclude_patterns: Multiple exclusion patterns
    - test_main_recursive_with_exclusions_integration: Recursive and exclusions combined
    """

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project with nested structure."""
        project_dir = tmp_path / "arg_test_project"
        project_dir.mkdir()

        # Create nested structure
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()
        (project_dir / "old_code").mkdir()

        # Create files in different locations
        (project_dir / "main.py").write_text(
            '''
def main():
    """Main entry point."""
    return "main"
'''
        )

        (project_dir / "src" / "utils.py").write_text(
            '''
def utility_function():
    """A utility function."""
    return "utility"
'''
        )

        (project_dir / "tests" / "test_main.py").write_text(
            '''
def test_main():
    """Test the main function."""
    assert main() == "main"
'''
        )

        (project_dir / "old_code" / "deprecated.py").write_text(
            '''
def deprecated_function():
    """This should be excluded."""
    return "deprecated"
'''
        )

        # Create backup files
        (project_dir / "backup_file.py.backup").write_text(
            '''
def backup_function():
    """This should be excluded."""
    return "backup"
'''
        )

        return project_dir

    @pytest.fixture
    def mock_database_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (2000,)
        return mock_conn

    @pytest.fixture
    def sample_callables(self):
        """Sample callable data for testing."""
        return [
            {
                "name": "test_function",
                "type": "function",
                "signature": "def test_function():",
                "docstring": "A test function.",
                "source_code": 'def test_function():\n    """A test function."""\n    return "test"',
                "line_number": 1,
                "is_async": False,
                "decorators": [],
            }
        ]

    def test_main_with_all_optional_arguments(
        self, tmp_path, sample_project, mock_database_connection, sample_callables
    ):
        """
        GIVEN command line with all optional arguments specified
        (--recursive, --dry-run, --exclude patterns, --db-config, --verbose)
        WHEN main() is executed
        THEN expect:
            - All arguments are parsed and applied correctly
            - Recursive scanning is performed
            - Exclusion patterns are applied
            - Dry run mode prevents database writes
            - Custom database config is used
            - Verbose output is enabled
            - Return code reflects dry run success
        """
        # Arrange
        custom_config = tmp_path / "custom_config.ini"
        custom_config.write_text(
            """
[database]
host = test_host
user = test_user
password = test_pass
database = test_db
"""
        )

        test_args = [
            "upload_code.py",
            str(sample_project),
            "--recursive",
            "--dry-run",
            "--exclude",
            "old_code/*",
            "--exclude",
            "*.backup",
            "--exclude",
            "tests/*",
            "--db-config",
            str(custom_config),
            "--verbose",
        ]

        expected_files = [
            sample_project / "main.py",
            sample_project / "src" / "utils.py",
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_project,
                recursive=True,
                dry_run=True,
                exclude=["old_code/*", "*.backup", "tests/*"],
                db_config=str(custom_config),
                verbose=True,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = expected_files
            mock_get_callables.return_value = sample_callables
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreiallargs", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for successful dry run"

            # Verify argument parsing
            mock_parse_args.assert_called_once()

            # Verify custom database config was used
            mock_start_db.assert_called_once_with(str(custom_config))

            # Verify recursive scanning with exclusions
            mock_find_files.assert_called_once_with(
                directory=sample_project,
                recursive=True,
                exclude_patterns=["old_code/*", "*.backup", "tests/*"],
            )

            # Verify processing occurred
            mock_get_callables.assert_called()
            mock_validate.assert_called()
            mock_create_entry.assert_called()
            mock_check_cid.assert_called()

            # Verify NO uploads in dry run mode
            mock_upload.assert_not_called()

            # Verify verbose output
            mock_print.assert_called()

            # Verify summary was generated
            mock_summary.assert_called_once()

    def test_main_with_minimal_arguments(
        self, tmp_path, sample_project, mock_database_connection, sample_callables
    ):
        """
        GIVEN command line with only required directory argument
        WHEN main() is executed
        THEN expect:
            - Default settings are applied
            - Non-recursive scan is performed
            - Default exclusions are used
            - Database writes occur (not dry run)
            - Default database config is used
            - Normal verbosity level
            - Return code reflects actual results
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_project)]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks with minimal/default arguments
            mock_parse_args.return_value = Namespace(
                directory=sample_project,
                recursive=False,  # Default: not recursive
                dry_run=False,  # Default: not dry run
                exclude=[],  # Default: no custom exclusions
                db_config=None,  # Default: no custom config
                verbose=False,  # Default: not verbose
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [sample_project / "main.py"]
            mock_get_callables.return_value = sample_callables
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreiminimal", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for successful execution"

            # Verify argument parsing
            mock_parse_args.assert_called_once()

            # Verify default database config (None)
            mock_start_db.assert_called_once_with(None)

            # Verify non-recursive scanning with default exclusions
            mock_find_files.assert_called_once_with(
                directory=sample_project,
                recursive=False,  # recursive=False (default)
                exclude_patterns=[],  # exclude=[] (default)
            )

            # Verify actual uploads occur (not dry run)
            mock_upload.assert_called_once()

            # Verify summary was generated
            mock_summary.assert_called_once()

    def test_main_multiple_exclude_patterns(
        self, tmp_path, sample_project, mock_database_connection, sample_callables
    ):
        """
        GIVEN command line with multiple --exclude flags
        WHEN main() is executed
        THEN expect:
            - All exclusion patterns are collected and applied
            - Files matching any pattern are excluded
            - Processing continues with remaining files
            - Return code is 0 (success)
        """
        # Arrange
        test_args = [
            "upload_code.py",
            str(sample_project),
            "--exclude",
            "test*",  # Exclude test files
            "--exclude",
            "*.backup",  # Exclude backup files
            "--exclude",
            "old_code/",  # Exclude old_code directory
            "--exclude",
            "temp*",  # Exclude temp files
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_project,
                recursive=False,
                dry_run=False,
                exclude=["test*", "*.backup", "old_code/", "temp*"],
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [sample_project / "main.py"]
            mock_get_callables.return_value = sample_callables
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreimultiexclude", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for successful execution"

            # Verify all exclusion patterns were passed to find_python_files
            mock_find_files.assert_called_once_with(
                directory=sample_project,
                recursive=False,
                exclude_patterns=["test*", "*.backup", "old_code/", "temp*"],
            )

            # Verify processing continued normally
            mock_upload.assert_called_once()
            mock_summary.assert_called_once()

    def test_main_recursive_with_exclusions_integration(
        self, tmp_path, sample_project, mock_database_connection, sample_callables
    ):
        """
        GIVEN command line with --recursive and --exclude flags combined
        WHEN main() is executed
        THEN expect:
            - Recursive scanning is performed
            - Exclusion patterns are applied during recursive scan
            - Both arguments work together correctly
            - Return code is 0 (success)
        """
        # Arrange
        test_args = [
            "upload_code.py",
            str(sample_project),
            "--recursive",
            "--exclude",
            "tests/",
            "--exclude",
            "*.backup",
        ]

        # Files that should be found after exclusions during recursive scan
        expected_remaining_files = [
            sample_project / "main.py",
            sample_project / "src" / "utils.py",
        ]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_project,
                recursive=True,  # Recursive enabled
                dry_run=False,
                exclude=["tests/", "*.backup"],  # Multiple exclusions
                db_config=None,
                verbose=False,
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = expected_remaining_files
            mock_get_callables.return_value = sample_callables
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreirecursive", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for successful execution"

            # Verify recursive scanning with exclusions
            mock_find_files.assert_called_once_with(
                directory=sample_project,
                recursive=True,  # recursive=True
                exclude_patterns=["tests/", "*.backup"],  # exclusions applied
            )

            # Verify processing occurred for remaining files
            assert mock_get_callables.call_count == len(expected_remaining_files)
            mock_upload.assert_called()
            mock_summary.assert_called_once()

    def test_main_dry_run_with_verbose_integration(
        self, tmp_path, sample_project, mock_database_connection, sample_callables
    ):
        """
        GIVEN command line with both --dry-run and --verbose flags
        WHEN main() is executed
        THEN expect:
            - Dry run mode prevents database writes
            - Verbose output shows detailed processing
            - Both flags work together correctly
            - Return code is 0 (success for dry run)
        """
        # Arrange
        test_args = ["upload_code.py", str(sample_project), "--dry-run", "--verbose"]

        with patch("sys.argv", test_args), patch(
            "main.parse_arguments"
        ) as mock_parse_args, patch("main.start_database") as mock_start_db, patch(
            "main.find_python_files"
        ) as mock_find_files, patch(
            "main.get_callables_from_file"
        ) as mock_get_callables, patch(
            "main.validate_callable"
        ) as mock_validate, patch(
            "main.create_code_entry"
        ) as mock_create_entry, patch(
            "main.check_cid_exists"
        ) as mock_check_cid, patch(
            "main.upload_code_entry"
        ) as mock_upload, patch(
            "main.generate_summary_report"
        ) as mock_summary, patch(
            "builtins.print"
        ) as mock_print:

            # Setup mocks
            mock_parse_args.return_value = Namespace(
                directory=sample_project,
                recursive=False,
                dry_run=True,  # Dry run enabled
                exclude=[],
                db_config=None,
                verbose=True,  # Verbose enabled
            )

            mock_start_db.return_value = mock_database_connection
            mock_find_files.return_value = [sample_project / "main.py"]
            mock_get_callables.return_value = sample_callables
            mock_validate.return_value = None
            mock_create_entry.return_value = Mock(
                cid="bafkreidryverbose", metadata={"cid": "bafkreimockmetacid"}
            )
            mock_check_cid.return_value = False

            # Act
            result = main()

            # Assert
            assert result == 0, "Should return 0 for successful dry run"

            # Verify dry run behavior: no uploads
            mock_upload.assert_not_called()

            # Verify verbose output was produced
            mock_print.assert_called()

            # Verify processing occurred up to upload step
            mock_get_callables.assert_called_once()
            mock_validate.assert_called_once()
            mock_create_entry.assert_called_once()
            mock_check_cid.assert_called_once()

            # Verify summary was generated
            mock_summary.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

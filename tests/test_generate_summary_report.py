import pytest
from pathlib import Path
from unittest.mock import Mock
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor


# Import the function and UploadStats class to test
from generate_summary_report import generate_summary_report
from upload_stats import UploadStats


class TestGenerateSummaryReport:
    """
    Test generate_summary_report function for displaying upload statistics.

    Test Methods:
    - test_generate_summary_report_basic_output: Basic report output structure
    - test_generate_summary_report_calculates_valid_callables: Valid callable calculation
    - test_generate_summary_report_queries_total_database_count: Database count querying
    - test_generate_summary_report_with_parse_errors: Parse error display
    - test_generate_summary_report_with_upload_errors: Upload error display
    - test_generate_summary_report_truncates_long_error_lists: Error list truncation
    - test_generate_summary_report_formatting: Output formatting verification
    - test_generate_summary_report_no_return_value: Return value verification
    - test_generate_summary_report_handles_database_error_gracefully: Database error handling
    - test_generate_summary_report_closes_database_cursor: Cursor cleanup
    - test_generate_summary_report_zero_counts: Zero count handling
    - test_generate_summary_report_error_count_calculation: Error count calculation
    """

    def test_generate_summary_report_basic_output(self, capsys):
        """
        GIVEN UploadStats with various counts and no errors
        WHEN generate_summary_report is called
        THEN expect printed output contains:
            - Header with "Upload Complete!" and separator lines
            - Files scanned count
            - Callables found count
            - Skipped counts (not standalone, no docstring)
            - Valid callables calculation
            - New uploads count
            - Duplicates skipped count
            - Errors count (0 in this case)
        """
        # Arrange
        stats = UploadStats(
            files_scanned=10,
            callables_found=25,
            skipped_not_standalone=8,
            skipped_no_docstring=5,
            skipped_duplicates=3,
            new_uploads=9,
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1247,)

        # Act
        result = generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        assert result is None
        output = captured.out

        assert "==================================================" in output
        assert "Upload Complete!" in output
        assert "Files scanned:            10" in output
        assert "Callables found:          25" in output
        assert "Skipped (not standalone): 8" in output
        assert "Skipped (no docstring):   5" in output
        assert "Valid callables:          12" in output  # 25 - 8 - 5 = 12
        assert "New uploads:              9" in output
        assert "Duplicates skipped:       3" in output
        assert "Errors:                   0" in output

    def test_generate_summary_report_calculates_valid_callables(self, capsys):
        """
        GIVEN UploadStats with callables_found=100, skipped_not_standalone=20, skipped_no_docstring=15
        WHEN generate_summary_report displays valid callables
        THEN expect:
            - Valid callables shows 65 (100 - 20 - 15)
            - Calculation is displayed correctly
            - All intermediate values shown
        """
        # Arrange
        stats = UploadStats(
            files_scanned=50,
            callables_found=100,
            skipped_not_standalone=20,
            skipped_no_docstring=15,
            new_uploads=65,
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (2000,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Callables found:          100" in output
        assert "Skipped (not standalone): 20" in output
        assert "Skipped (no docstring):   15" in output
        assert "Valid callables:          65" in output  # 100 - 20 - 15 = 65

    def test_generate_summary_report_queries_total_database_count(self, capsys):
        """
        GIVEN database connection is provided
        WHEN generate_summary_report is called
        THEN expect:
            - Queries database for total count in codes table
            - Displays "Database now contains X code entries"
            - Handles query errors gracefully
        """
        # Arrange
        stats = UploadStats(files_scanned=5, new_uploads=3)

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1500,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Database now contains 1,500 code entries" in output

        # Verify database query was made
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT COUNT(*) FROM codes")
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_generate_summary_report_with_parse_errors(self, capsys):
        """
        GIVEN UploadStats contains parse_errors list with file paths and error messages
        WHEN generate_summary_report is called
        THEN expect:
            - Shows "Parse Errors:" section
            - Lists first 5 errors with format "- filepath: error message"
            - Shows "... and X more" if more than 5 errors
            - Errors section only appears if parse_errors is non-empty
        """
        # Arrange
        parse_errors = [
            (Path("/home/user/project/bad_file.py"), "invalid syntax (line 42)"),
            (Path("/home/user/project/another.py"), "unexpected indent"),
            (
                Path("/home/user/project/broken.py"),
                "EOF while scanning triple-quoted string",
            ),
        ]

        stats = UploadStats(
            files_scanned=10, callables_found=15, parse_errors=parse_errors
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1000,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Parse Errors:" in output
        assert "- /home/user/project/bad_file.py: invalid syntax (line 42)" in output
        assert "- /home/user/project/another.py: unexpected indent" in output
        assert (
            "- /home/user/project/broken.py: EOF while scanning triple-quoted string"
            in output
        )
        assert (
            "Errors:                   3" in output
        )  # Should include parse errors in total

    def test_generate_summary_report_with_upload_errors(self, capsys):
        """
        GIVEN UploadStats contains errors list with dicts of file/callable/error
        WHEN generate_summary_report is called
        THEN expect:
            - Shows "Upload Errors:" section
            - Lists first 5 errors with format "- file (callable): error"
            - Shows "... and X more" if more than 5 errors
            - Errors section only appears if errors is non-empty
        """
        # Arrange
        upload_errors = [
            {
                "file": "utils/helpers.py",
                "callable": "process_data",
                "error": "Data too long for column",
            },
            {
                "file": "modules/analyzer.py",
                "callable": "calculate_metrics",
                "error": "Duplicate entry for key",
            },
            {
                "file": "core/processor.py",
                "callable": "transform_input",
                "error": "Connection timeout",
            },
        ]

        stats = UploadStats(
            files_scanned=8, callables_found=20, new_uploads=17, errors=upload_errors
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (800,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Upload Errors:" in output
        assert "- utils/helpers.py (process_data): Data too long for column" in output
        assert (
            "- modules/analyzer.py (calculate_metrics): Duplicate entry for key"
            in output
        )
        assert "- core/processor.py (transform_input): Connection timeout" in output
        assert (
            "Errors:                   3" in output
        )  # Should include upload errors in total

    def test_generate_summary_report_truncates_long_error_lists(self, capsys):
        """
        GIVEN UploadStats with 20 parse errors and 15 upload errors
        WHEN generate_summary_report is called
        THEN expect:
            - Only first 5 of each error type shown
            - "... and 15 more" shown for parse errors
            - "... and 10 more" shown for upload errors
            - Truncation happens at exactly 5 items
        """
        # Arrange
        parse_errors = [
            (Path(f"/home/user/project/parse_error_{i}.py"), f"syntax error {i}")
            for i in range(20)
        ]

        upload_errors = [
            {
                "file": f"module_{i}.py",
                "callable": f"function_{i}",
                "error": f"upload error {i}",
            }
            for i in range(15)
        ]

        stats = UploadStats(
            files_scanned=50,
            callables_found=100,
            parse_errors=parse_errors,
            errors=upload_errors,
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (2500,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Errors:                   35" in output  # 20 + 15 = 35

        # Check parse errors truncation
        assert "Parse Errors:" in output
        assert "- /home/user/project/parse_error_0.py: syntax error 0" in output
        assert "- /home/user/project/parse_error_4.py: syntax error 4" in output
        assert "... and 15 more" in output
        assert "parse_error_5.py" not in output  # Should not show beyond first 5

        # Check upload errors truncation
        assert "Upload Errors:" in output
        assert "- module_0.py (function_0): upload error 0" in output
        assert "- module_4.py (function_4): upload error 4" in output
        assert "... and 10 more" in output
        assert "module_5.py" not in output  # Should not show beyond first 5

    def test_generate_summary_report_formatting(self, capsys):
        """
        GIVEN any UploadStats
        WHEN generate_summary_report prints output
        THEN expect:
            - Separator line is exactly 50 equals signs
            - Labels are left-aligned with consistent spacing
            - Numbers are right-aligned in their columns
            - Consistent indentation for sub-items
        """
        # Arrange
        stats = UploadStats(
            files_scanned=1,
            callables_found=2,
            skipped_not_standalone=3,
            skipped_no_docstring=4,
            new_uploads=5,
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (123,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        lines = output.split("\n")

        # Check separator line length
        separator_lines = [line for line in lines if line.startswith("=")]
        assert len(separator_lines) >= 2
        assert len(separator_lines[0]) == 50

        # Check alignment and spacing consistency
        stat_lines = [
            line for line in lines if ":" in line and not line.startswith("=")
        ]
        for line in stat_lines:
            if "Files scanned:" in line:
                assert "Files scanned:            1" in line
            elif "Callables found:" in line:
                assert "Callables found:          2" in line

    def test_generate_summary_report_no_return_value(self, capsys):
        """
        GIVEN any UploadStats and connection
        WHEN generate_summary_report is called
        THEN expect:
            - Function returns None
            - All output goes to stdout
            - No exceptions raised
        """
        # Arrange
        stats = UploadStats(files_scanned=1)
        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (100,)

        # Act
        result = generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        assert result is None
        assert len(captured.out) > 0  # Should have output to stdout
        assert captured.err == ""  # No stderr output

    def test_generate_summary_report_handles_database_error_gracefully(self, capsys):
        """
        GIVEN database query for total count fails
        WHEN generate_summary_report attempts to show total
        THEN expect:
            - Error is caught and handled
            - Rest of report displays normally
            - May omit database total or show error message
            - No exception propagates to caller
        """
        # Arrange
        stats = UploadStats(files_scanned=5, new_uploads=3)

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database connection lost")

        # Act - should not raise exception
        try:
            result = generate_summary_report(stats, mock_connection)
            # Database total may be omitted or show error, but no exception should occur
        except Exception as e:
            pytest.fail(f"generate_summary_report propagated an exception: {e}")

            captured = capsys.readouterr()

            # Assert
            assert result is None
            output = captured.out

            # Basic report should still be there
            assert "Upload Complete!" in output
            assert "Files scanned:" in output
            assert "New uploads:" in output

    def test_generate_summary_report_closes_database_cursor(self):
        """
        GIVEN database connection is used for querying
        WHEN generate_summary_report completes
        THEN expect:
            - Any opened cursor is closed
            - Cursor closed even if query fails
            - No resource leaks occur
        """
        # Test successful case
        stats = UploadStats(files_scanned=1)
        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (100,)

        generate_summary_report(stats, mock_connection)

        mock_cursor.close.assert_called_once()

        # Test error case
        mock_cursor.reset_mock()
        mock_cursor.execute.side_effect = Exception("Query failed")

        generate_summary_report(stats, mock_connection)

        mock_cursor.close.assert_called_once()  # Should still be closed

    def test_generate_summary_report_zero_counts(self, capsys):
        """
        GIVEN UploadStats with all counts at zero
        WHEN generate_summary_report is called
        THEN expect:
            - All counts display as 0
            - No division by zero errors
            - Report structure remains consistent
            - No negative numbers in calculations
        """
        # Arrange
        stats = UploadStats()  # All defaults to 0

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (0,)

        # Act
        result = generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        assert result is None
        output = captured.out

        assert "Files scanned:            0" in output
        assert "Callables found:          0" in output
        assert "Skipped (not standalone): 0" in output
        assert "Skipped (no docstring):   0" in output
        assert "Valid callables:          0" in output  # 0 - 0 - 0 = 0
        assert "New uploads:              0" in output
        assert "Duplicates skipped:       0" in output
        assert "Errors:                   0" in output
        assert "Database now contains 0 code entries" in output

    def test_generate_summary_report_error_count_calculation(self, capsys):
        """
        GIVEN UploadStats with 3 parse_errors and 5 errors
        WHEN generate_summary_report shows total errors
        THEN expect:
            - Errors line shows 8 (sum of both error types)
            - Calculation combines both error lists
            - Individual error sections still shown separately
        """
        # Arrange
        parse_errors = [
            (Path(f"/home/user/file_{i}.py"), f"parse error {i}") for i in range(3)
        ]

        upload_errors = [
            {
                "file": f"module_{i}.py",
                "callable": f"func_{i}",
                "error": f"upload error {i}",
            }
            for i in range(5)
        ]

        stats = UploadStats(
            files_scanned=10,
            callables_found=20,
            parse_errors=parse_errors,
            errors=upload_errors,
        )

        mock_connection = Mock(spec=MySQLConnection)
        mock_cursor = Mock(spec=MySQLCursor)
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1000,)

        # Act
        generate_summary_report(stats, mock_connection)
        captured = capsys.readouterr()

        # Assert
        output = captured.out
        assert "Errors:                   8" in output  # 3 + 5 = 8
        assert "Parse Errors:" in output
        assert "Upload Errors:" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

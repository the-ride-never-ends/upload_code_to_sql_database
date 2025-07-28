import pytest
import json
from unittest.mock import Mock
from mysql.connector.errors import IntegrityError, DataError, ConnectionTimeoutError


# Import the function and CodeEntry class to test
from code_entry.upload_code_entry import upload_code_entry, CodeEntry


class TestUploadCodeEntry:
    """
    Test upload_code_entry function for database insertion with transactions.

    Test Methods:
    - test_upload_code_entry_successful_insertion: Successful database insertion
    - test_upload_code_entry_codes_table_fields: Codes table field verification
    - test_upload_code_entry_metadata_table_fields: Metadata table field verification
    - test_upload_code_entry_transaction_rollback_on_codes_failure: Codes table failure rollback
    - test_upload_code_entry_transaction_rollback_on_metadata_failure: Metadata table failure rollback
    - test_upload_code_entry_raises_integrity_error_on_duplicate: Duplicate entry handling
    - test_upload_code_entry_raises_data_error_on_invalid_data: Data constraint violation handling
    - test_upload_code_entry_handles_generic_database_error: Generic database error handling
    - test_upload_code_entry_atomicity: Transaction atomicity verification
    - test_upload_code_entry_handles_connection_loss_during_transaction: Connection loss handling
    - test_upload_code_entry_json_serialization_of_tags: JSON serialization of tags
    - test_upload_code_entry_handles_very_long_code: Large source code handling
    - test_upload_code_entry_parameterized_queries: SQL injection protection
    - test_upload_code_entry_cursor_cleanup: Cursor resource cleanup
    """

    def test_upload_code_entry_successful_insertion(self):
        """
        GIVEN valid CodeEntry with all required fields
        WHEN upload_code_entry is called
        THEN expect:
            - Transaction is started
            - SELECT to check for existing metadata CID
            - REPLACE INTO codes table with cid, version_cid, signature, docstring, computer_code
            - INSERT INTO metadata table with all metadata fields and code_cid reference
            - Transaction is committed
            - No exceptions raised
            - Returns None
        """
        # Create test CodeEntry
        code_entry = CodeEntry(
            cid="QmX7G8DPKj6L4Fr7RZNnPZyHTE8vPJNfV2mWYgFchVTqyY",
            signature="def calculate(x: int, y: int) -> int:",
            docstring="Calculate the sum of two integers.",
            computer_code='def calculate(x: int, y: int) -> int:\n    """Calculate the sum of two integers."""\n    return x + y',
            metadata={
                "cid": "QmMetadataCID123",
                "code_cid": "QmX7G8DPKj6L4Fr7RZNnPZyHTE8vPJNfV2mWYgFchVTqyY",
                "code_name": "calculate",
                "code_type": "function",
                "is_test": False,
                "file_path": "utils/math.py",
                "tags": ["utils", "math"],
            },
        )

        # Mock database connection and cursor
        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Simulate successful insert
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        # Call the function
        result = upload_code_entry(mock_db_connection, code_entry)

        # Verify transaction pattern
        mock_db_connection.cursor.assert_called_once()
        assert (
            mock_cursor.execute.call_count == 3
        )  # SELECT + REPLACE + INSERT statements
        mock_cursor.close.assert_called_once()
        mock_db_connection.commit.assert_called_once()
        mock_db_connection.rollback.assert_not_called()

        # Verify return value
        assert result is None

    def test_upload_code_entry_codes_table_fields(self):
        """
        GIVEN CodeEntry with specific field values
        WHEN upload_code_entry inserts into codes table
        THEN expect REPLACE contains:
            - cid: from code_entry.cid (used as immutable_cid since no existing metadata found)
            - version_cid: from code_entry.cid
            - signature: from code_entry.signature
            - docstring: from code_entry.docstring
            - computer_code: from code_entry.computer_code
            - Proper parameter binding for all values
        """
        code_entry = CodeEntry(
            cid="test_cid_123",
            signature="def test_func() -> None:",
            docstring="Test function docstring",
            computer_code="def test_func() -> None:\n    pass",
            metadata={
                "cid": "QmMetadataCID456",
                "code_cid": "test_cid_123",
                "code_name": "test_func",
                "code_type": "function",
                "is_test": True,
                "file_path": "tests/test_example.py",
                "tags": ["test"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Simulate successful insert
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        upload_code_entry(mock_db_connection, code_entry)

        # Check that second execute call (codes table REPLACE) has correct parameters
        second_call = mock_cursor.execute.call_args_list[
            1
        ]  # Get the SECOND call (REPLACE INTO codes)
        sql_query, params = second_call[0]

        # Verify it's a REPLACE INTO codes table
        assert "REPLACE INTO codes" in sql_query

        # Verify parameter binding includes all required fields
        assert (
            "test_cid_123" in params
        )  # immutable_cid (same as cid when no existing metadata)
        assert "test_cid_123" in params  # version_cid (should be same as cid)
        assert "def test_func() -> None:" in params  # signature
        assert "Test function docstring" in params  # docstring
        assert "def test_func() -> None:\n    pass" in params  # computer_code

    def test_upload_code_entry_metadata_table_fields(self):
        """
        GIVEN CodeEntry with metadata dictionary
        WHEN upload_code_entry inserts into metadata table
        THEN expect INSERT contains:
            - cid: from metadata['cid']
            - code_cid: matches the immutable_cid from codes table (code_entry.cid when no existing metadata)
            - code_name: from metadata['code_name']
            - code_type: from metadata['code_type']
            - is_test: from metadata['is_test']
            - file_path: from metadata['file_path']
            - tags: from metadata['tags'] as JSON
            - All fields properly bound as parameters
        """
        code_entry = CodeEntry(
            cid="metadata_test_cid",
            signature="class TestClass:",
            docstring="A test class",
            computer_code="class TestClass:\n    pass",
            metadata={
                "cid": "QmMetadataCID789",
                "code_cid": "metadata_test_cid",
                "code_name": "TestClass",
                "code_type": "class",
                "is_test": False,
                "file_path": "src/models.py",
                "tags": ["models", "classes"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # Simulate successful insert
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        upload_code_entry(mock_db_connection, code_entry)

        # Check that third execute call (metadata table) has correct parameters
        third_call = mock_cursor.execute.call_args_list[
            2
        ]  # Get the THIRD call (INSERT INTO metadata)
        sql_query, params = third_call[0]

        # Verify it's an INSERT into metadata table
        assert "INSERT INTO metadata" in sql_query

        # Verify parameter binding includes all metadata fields
        assert "QmMetadataCID789" in params  # metadata cid
        assert "metadata_test_cid" in params  # code_cid (immutable_cid)
        assert "TestClass" in params  # code_name
        assert "class" in params  # code_type
        assert False in params  # is_test
        assert "src/models.py" in params  # file_path

        # Verify tags are JSON serialized
        tags_json = json.dumps(["models", "classes"])
        assert tags_json in params

    def test_upload_code_entry_transaction_rollback_on_codes_failure(self):
        """
        GIVEN insertion into codes table fails
        WHEN upload_code_entry attempts the operation
        THEN expect:
            - Transaction is started
            - SELECT succeeds
            - REPLACE fails
            - Transaction is rolled back
            - No data inserted into either table
            - Original exception is raised
        """
        code_entry = CodeEntry(
            cid="failure_test_cid",
            signature="def failing_func():",
            docstring="This will fail",
            computer_code="def failing_func():\n    pass",
            metadata={
                "cid": "QmMetadataCIDFail",
                "code_cid": "failure_test_cid",
                "code_name": "failing_func",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/fail.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Make second execute call (codes table REPLACE) fail
        test_exception = Exception("Database connection error")
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            test_exception,
        ]  # First (SELECT) succeeds, second (REPLACE) fails

        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is test_exception

        # Verify transaction rollback pattern
        assert mock_cursor.execute.call_count == 2  # SELECT and REPLACE attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_transaction_rollback_on_metadata_failure(self):
        """
        GIVEN insertion into codes table succeeds but metadata table fails
        WHEN upload_code_entry attempts the operation
        THEN expect:
            - Transaction is started
            - SELECT succeeds
            - REPLACE succeeds
            - INSERT fails
            - Transaction is rolled back
            - No data persisted in either table
            - Original exception is raised
        """
        code_entry = CodeEntry(
            cid="metadata_failure_cid",
            signature="def metadata_fail():",
            docstring="Metadata insertion will fail",
            computer_code="def metadata_fail():\n    pass",
            metadata={
                "cid": "QmMetadataCIDMetaFail",
                "code_cid": "metadata_failure_cid",
                "code_name": "metadata_fail",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/meta_fail.py",
                "tags": ["fail"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Make third execute call (metadata table) fail
        test_exception = Exception("Metadata constraint violation")
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            None,
            test_exception,
        ]  # SELECT and REPLACE succeed, INSERT fails

        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is test_exception

        # Verify transaction rollback pattern
        assert mock_cursor.execute.call_count == 3  # All three calls attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_raises_integrity_error_on_duplicate(self):
        """
        GIVEN CID already exists in database (duplicate entry)
        WHEN upload_code_entry attempts insertion
        THEN expect:
            - IntegrityError is raised
            - Error message indicates duplicate entry
            - Transaction is rolled back
            - No partial data inserted
        """
        code_entry = CodeEntry(
            cid="duplicate_cid",
            signature="def duplicate_func():",
            docstring="This CID already exists",
            computer_code="def duplicate_func():\n    pass",
            metadata={
                "cid": "QmMetadataCIDDup",
                "code_cid": "duplicate_cid",
                "code_name": "duplicate_func",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/duplicate.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Simulate IntegrityError on REPLACE into codes (duplicate primary key)
        integrity_error = IntegrityError(
            "Duplicate entry 'duplicate_cid' for key 'PRIMARY'"
        )
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            integrity_error,
        ]  # SELECT succeeds, REPLACE fails

        # Verify IntegrityError is raised
        with pytest.raises(IntegrityError) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is integrity_error

        # Verify transaction rollback pattern
        assert mock_cursor.execute.call_count == 2  # SELECT and REPLACE attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_raises_data_error_on_invalid_data(self):
        """
        GIVEN CodeEntry with data that violates database constraints
        WHEN upload_code_entry attempts insertion
        THEN expect:
            - DataError is raised
            - Error indicates which constraint was violated
            - Transaction is rolled back
            - No partial data inserted
        """
        code_entry = CodeEntry(
            cid="data_error_cid",
            signature="def data_error_func():",
            docstring="Data too long for column",
            computer_code="def data_error_func():\n    pass",
            metadata={
                "cid": "QmMetadataCIDDataErr",
                "code_cid": "data_error_cid",
                "code_name": "data_error_func",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/data_error.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Simulate DataError (data too long, invalid type, etc.)
        data_error = DataError("Data too long for column 'signature' at row 1")
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            data_error,
        ]  # SELECT succeeds, REPLACE fails

        # Verify DataError is raised
        with pytest.raises(DataError) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is data_error

        # Verify transaction rollback pattern
        assert mock_cursor.execute.call_count == 2  # SELECT and REPLACE attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_handles_generic_database_error(self):
        """
        GIVEN unexpected database error occurs
        WHEN upload_code_entry attempts insertion
        THEN expect:
            - Runtime Exception is raised
            - Transaction is rolled back
            - Error details are preserved
            - No partial data inserted
        """
        code_entry = CodeEntry(
            cid="generic_error_cid",
            signature="def generic_error_func():",
            docstring="Generic database error",
            computer_code="def generic_error_func():\n    pass",
            metadata={
                "cid": "QmMetadataCIDGenErr",
                "code_cid": "generic_error_cid",
                "code_name": "generic_error_func",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/generic_error.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Simulate generic database error
        generic_error = RuntimeError("Connection to database lost")
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            generic_error,
        ]  # SELECT succeeds, REPLACE fails

        # Verify generic Exception is raised
        with pytest.raises(RuntimeError) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is generic_error

        # Verify transaction rollback pattern
        assert mock_cursor.execute.call_count == 2  # SELECT and REPLACE attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_atomicity(self):
        """
        GIVEN any failure during the three-step insertion process
        WHEN upload_code_entry executes
        THEN expect:
            - Either both tables are updated or neither
            - No partial success state possible
            - Database consistency maintained
        """
        code_entry = CodeEntry(
            cid="atomicity_test_cid",
            signature="def atomicity_test():",
            docstring="Test atomicity",
            computer_code="def atomicity_test():\n    pass",
            metadata={
                "cid": "QmMetadataCIDAtomicity",
                "code_cid": "atomicity_test_cid",
                "code_name": "atomicity_test",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/atomicity.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Test successful case - all operations succeed
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [None, None, None]  # All three succeed

        upload_code_entry(mock_db_connection, code_entry)

        # Verify all operations attempted and committed
        assert mock_cursor.execute.call_count == 3  # SELECT + REPLACE + INSERT
        mock_db_connection.commit.assert_called_once()
        mock_db_connection.rollback.assert_not_called()

        # Reset mocks for failure case
        mock_db_connection.reset_mock()
        mock_cursor.reset_mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Test failure case - third operation fails
        atomicity_error = Exception("Third operation failed")
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            None,
            atomicity_error,
        ]  # SELECT and REPLACE succeed, INSERT fails

        with pytest.raises(Exception):
            upload_code_entry(mock_db_connection, code_entry)

        # Verify rollback, no commit
        assert mock_cursor.execute.call_count == 3  # All three attempted
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_handles_connection_loss_during_transaction(self):
        """
        GIVEN database connection is lost mid-transaction
        WHEN upload_code_entry is executing
        THEN expect:
            - Connection error is raised
            - Any partial transaction is not committed
            - Database remains in consistent state
        """
        code_entry = CodeEntry(
            cid="connection_loss_cid",
            signature="def connection_loss_test():",
            docstring="Test connection loss",
            computer_code="def connection_loss_test():\n    pass",
            metadata={
                "cid": "QmMetadataCIDConnLoss",
                "code_cid": "connection_loss_cid",
                "code_name": "connection_loss_test",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/connection.py",
                "tags": [],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_db_connection.cursor.return_value = mock_cursor

        # Simulate connection loss during transaction
        connection_error = ConnectionTimeoutError(
            "MySQL server connection has timed out"
        )
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_cursor.execute.side_effect = [
            None,
            connection_error,
        ]  # SELECT succeeds, REPLACE fails

        # Verify connection error is raised
        with pytest.raises(ConnectionTimeoutError) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is connection_error

        # Verify rollback attempted (even if connection is lost)
        assert mock_cursor.execute.call_count == 2  # SELECT and REPLACE attempted
        mock_cursor.close.assert_called_once()
        mock_db_connection.rollback.assert_called_once()
        mock_db_connection.commit.assert_not_called()

    def test_upload_code_entry_json_serialization_of_tags(self):
        """
        GIVEN metadata['tags'] is a Python list
        WHEN upload_code_entry inserts into metadata table
        THEN expect:
            - tags list is serialized to JSON string
            - JSON serialization handles special characters
            - Empty list serializes to '[]'
            - None serializes appropriately
        """
        # Test with normal tags
        code_entry_normal = CodeEntry(
            cid="json_tags_cid",
            signature="def json_tags_test():",
            docstring="Test JSON tags",
            computer_code="def json_tags_test():\n    pass",
            metadata={
                "cid": "QmMetadataCIDJsonTags",
                "code_cid": "json_tags_cid",
                "code_name": "json_tags_test",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/json_test.py",
                "tags": ["special-chars", "with spaces", "unicode:测试"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        upload_code_entry(mock_db_connection, code_entry_normal)

        # Check metadata table parameters (third call)
        third_call = mock_cursor.execute.call_args_list[2]
        sql_query, params = third_call[0]

        # Verify tags are properly JSON serialized
        expected_tags_json = json.dumps(
            ["special-chars", "with spaces", "unicode:测试"]
        )
        assert expected_tags_json in params

        # Test with empty tags
        mock_db_connection.reset_mock()
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        code_entry_empty = CodeEntry(
            cid="empty_tags_cid",
            signature="def empty_tags_test():",
            docstring="Test empty tags",
            computer_code="def empty_tags_test():\n    pass",
            metadata={
                "cid": "QmMetadataCIDEmptyTags",
                "code_cid": "empty_tags_cid",
                "code_name": "empty_tags_test",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/empty_tags.py",
                "tags": [],
            },
        )

        upload_code_entry(mock_db_connection, code_entry_empty)

        # Check empty tags serialization (third call)
        third_call = mock_cursor.execute.call_args_list[2]
        sql_query, params = third_call[0]

        assert "[]" in params

    def test_upload_code_entry_handles_very_long_code(self):
        """
        GIVEN CodeEntry with very long source code (10000+ lines)
        WHEN upload_code_entry attempts insertion
        THEN expect:
            - Insertion succeeds if within database limits
            - Appropriate error if exceeds TEXT field limit
            - No truncation of data
        """
        # Create very long code string
        long_code_lines = []
        for i in range(10000):
            long_code_lines.append(f"    # This is line {i} of very long code")
        long_code = (
            "def very_long_function():\n" + "\n".join(long_code_lines) + "\n    pass"
        )

        code_entry = CodeEntry(
            cid="long_code_cid",
            signature="def very_long_function():",
            docstring="A function with very long implementation",
            computer_code=long_code,
            metadata={
                "cid": "QmMetadataCIDLongCode",
                "code_cid": "long_code_cid",
                "code_name": "very_long_function",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/long_code.py",
                "tags": ["long", "code"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        # Test successful case (within limits)
        upload_code_entry(mock_db_connection, code_entry)

        # Verify the long code is passed without truncation (second call is REPLACE INTO codes)
        second_call = mock_cursor.execute.call_args_list[1]
        sql_query, params = second_call[0]

        # Verify full code is in parameters (not truncated)
        assert long_code in params
        assert len([p for p in params if isinstance(p, str) and "line 9999" in p]) > 0

        # Verify normal execution pattern
        assert mock_cursor.execute.call_count == 3  # SELECT + REPLACE + INSERT
        mock_db_connection.commit.assert_called_once()

    def test_upload_code_entry_parameterized_queries(self):
        """
        GIVEN CodeEntry with SQL injection attempts in strings
        WHEN upload_code_entry executes queries
        THEN expect:
            - All values use parameter binding
            - No string concatenation in queries
            - Special characters safely handled
            - Queries execute without SQL injection
        """
        # Create CodeEntry with potential SQL injection strings
        malicious_code_entry = CodeEntry(
            cid="'; DROP TABLE codes; --",
            signature='def malicious_func(x: str = "\'; DROP TABLE metadata; --") -> str:',
            docstring="Test'; DELETE FROM codes WHERE 1=1; --",
            computer_code='def malicious_func():\n    return "\'; TRUNCATE TABLE metadata; --"',
            metadata={
                "cid": "QmMetadataCIDMalicious",
                "code_cid": "'; DROP TABLE codes; --",
                "code_name": "malicious'; DROP TABLE codes; --",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/'; DROP TABLE metadata; --.py",
                "tags": ["'; DROP TABLE", "sql-injection"],
            },
        )

        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        upload_code_entry(mock_db_connection, malicious_code_entry)

        # Verify parameterized queries were used
        for i, call_args in enumerate(mock_cursor.execute.call_args_list):
            sql_query, params = call_args[0]

            # Verify query uses placeholders (% or ?)
            assert "%s" in sql_query or "?" in sql_query

            # Verify no direct string concatenation of malicious content
            assert "DROP TABLE" not in sql_query
            assert "DELETE FROM" not in sql_query
            assert "TRUNCATE TABLE" not in sql_query

        # Check that malicious strings are safely contained in parameters
        all_params = []
        for call_args in mock_cursor.execute.call_args_list:
            _, params = call_args[0]
            all_params.extend([str(p) for p in params if p is not None])

        # The malicious CID should be in the parameters (safely bound)
        assert (
            "'; DROP TABLE codes; --" in all_params
        ), f"Expected malicious CID in params: {all_params}"

        # Verify malicious strings in other fields are also safely bound
        assert any(
            "DELETE FROM codes WHERE 1=1" in param for param in all_params
        ), "Malicious docstring should be in params"
        assert any(
            "TRUNCATE TABLE metadata" in param for param in all_params
        ), "Malicious code should be in params"

        # Verify normal execution completed
        assert mock_cursor.execute.call_count == 3  # SELECT + REPLACE + INSERT
        mock_db_connection.commit.assert_called_once()

    def test_upload_code_entry_cursor_cleanup(self):
        """
        GIVEN any outcome (success or failure)
        WHEN upload_code_entry completes
        THEN expect:
            - All cursors are properly closed
            - No resource leaks
            - Cleanup happens even on exceptions
        """
        code_entry = CodeEntry(
            cid="cleanup_test_cid",
            signature="def cleanup_test():",
            docstring="Test cursor cleanup",
            computer_code="def cleanup_test():\n    pass",
            metadata={
                "cid": "QmMetadataCIDCleanup",
                "code_cid": "cleanup_test_cid",
                "code_name": "cleanup_test",
                "code_type": "function",
                "is_test": False,
                "file_path": "src/cleanup.py",
                "tags": [],
            },
        )

        # Test successful case
        mock_db_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        upload_code_entry(mock_db_connection, code_entry)

        # Verify cursor cleanup on success
        mock_cursor.close.assert_called_once()

        # Test failure case
        mock_db_connection.reset_mock()
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        cleanup_error = Exception("Test cleanup error")
        mock_cursor.execute.side_effect = [
            None,
            cleanup_error,
        ]  # SELECT succeeds, REPLACE fails

        with pytest.raises(Exception):
            upload_code_entry(mock_db_connection, code_entry)

        # Verify cursor cleanup on failure
        mock_cursor.close.assert_called_once()

        # Test case where cursor.close() itself fails
        mock_db_connection.reset_mock()
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = None  # No existing metadata found
        mock_db_connection.cursor.return_value = mock_cursor

        cursor_close_error = Exception("Cursor close failed")
        mock_cursor.close.side_effect = cursor_close_error
        original_error = Exception("Original operation failed")
        mock_cursor.execute.side_effect = [
            None,
            original_error,
        ]  # SELECT succeeds, REPLACE fails

        # Should still raise original error, not cursor cleanup error
        with pytest.raises(Exception) as exc_info:
            upload_code_entry(mock_db_connection, code_entry)

        assert exc_info.value is original_error
        mock_cursor.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

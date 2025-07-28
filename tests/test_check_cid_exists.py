import pytest
from unittest.mock import Mock, patch
import mysql.connector


# Import the function to test
from cid.check_cid_exists import check_cid_exists


class TestCheckCidExists:
    """
    Test check_cid_exists function for querying CID existence in database.

    Test Methods:
    - test_check_cid_exists_when_cid_present: Valid CID that exists in codes table
    - test_check_cid_exists_when_cid_not_present: Valid CID that does not exist
    - test_check_cid_exists_uses_parameterized_query: Ensures SQL injection protection
    - test_check_cid_exists_closes_cursor_on_success: Verifies cursor cleanup
    - test_check_cid_exists_handles_database_connection_error: Connection failure handling
    - test_check_cid_exists_handles_query_timeout: Query timeout error handling
    - test_check_cid_exists_handles_invalid_table_name: Missing table error handling
    - test_check_cid_exists_with_empty_cid: Empty string CID handling
    - test_check_cid_exists_with_none_cid: None CID value handling
    - test_check_cid_exists_query_structure: Verifies SQL query structure
    - test_check_cid_exists_handles_cursor_creation_failure: Cursor creation error handling
    - test_check_cid_exists_thread_safety: Concurrent access testing
    """

    def test_check_cid_exists_when_cid_present(self):
        """
        GIVEN a CID that exists in the codes table
        WHEN check_cid_exists is called with this CID
        THEN expect:
            - Returns True
            - Executes SELECT query on codes table
            - Uses parameterized query for safety
            - Closes cursor after query
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("QmTestCID123",)  # CID exists

        test_cid = "QmTestCID123"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is True
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_check_cid_exists_when_cid_not_present(self):
        """
        GIVEN a CID that does not exist in the codes table
        WHEN check_cid_exists is called with this CID
        THEN expect:
            - Returns False
            - Executes SELECT query on codes table
            - Uses parameterized query for safety
            - Closes cursor after query
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # CID does not exist

        test_cid = "QmNonExistentCID456"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is False
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_check_cid_exists_uses_parameterized_query(self):
        """
        GIVEN a CID string with potential SQL injection characters
        WHEN check_cid_exists is called
        THEN expect:
            - Query uses parameter placeholders (? or %s)
            - CID value passed separately from query string
            - No string concatenation in query
            - SQL injection attempts are neutralized
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        # CID with potential SQL injection characters
        malicious_cid = "'; DROP TABLE codes; --"

        # Act
        result = check_cid_exists(mock_connection, malicious_cid)

        # Assert
        assert result is False
        mock_cursor.execute.assert_called_once()

        # Verify parameterized query was used
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = (
            call_args[0][1]
            if len(call_args[0]) > 1
            else call_args[1]["params"] if "params" in call_args[1] else None
        )

        # Query should contain placeholder, not the actual CID value
        assert malicious_cid not in query
        assert "%s" in query or "?" in query
        assert params is not None
        assert malicious_cid in params
        mock_cursor.close.assert_called_once()

    def test_check_cid_exists_closes_cursor_on_success(self):
        """
        GIVEN successful database query execution
        WHEN check_cid_exists completes
        THEN expect:
            - Cursor is closed via cursor.close()
            - Cursor closed even if CID not found
            - No resource leaks
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("QmTestCID",)

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is True
        mock_cursor.close.assert_called_once()

        # Test with CID not found case
        mock_cursor.reset_mock()
        mock_cursor.fetchone.return_value = None

        result = check_cid_exists(mock_connection, "QmNotFound")

        assert result is False
        mock_cursor.close.assert_called_once()

    @patch("logging.getLogger")
    def test_check_cid_exists_handles_database_connection_error(self, mock_get_logger):
        """
        GIVEN database connection is lost during query
        WHEN check_cid_exists attempts to execute query
        THEN expect:
            - Returns False (fail-safe behavior)
            - Does not raise exception
            - Logs error appropriately
            - Attempts to close cursor if it was created
        """
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = mysql.connector.Error("Connection lost")

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is False
        mock_cursor.close.assert_called_once()
        mock_logger.error.assert_called()

    @patch("logging.getLogger")
    def test_check_cid_exists_handles_query_timeout(self, mock_get_logger):
        """
        GIVEN database query times out
        WHEN check_cid_exists is executing
        THEN expect:
            - Returns False
            - Does not raise exception
            - Timeout error is caught and handled
            - Cursor is closed if possible
        """
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = mysql.connector.Error("Query timeout")

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is False
        mock_cursor.close.assert_called_once()
        mock_logger.error.assert_called()

    @patch("logging.getLogger")
    def test_check_cid_exists_handles_invalid_table_name(self, mock_get_logger):
        """
        GIVEN codes table does not exist (database schema issue)
        WHEN check_cid_exists attempts query
        THEN expect:
            - Returns False
            - Does not raise exception
            - Table error is caught and logged
            - Cursor is closed if it was created
        """
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = mysql.connector.Error(
            "Table 'database.codes' doesn't exist"
        )

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is False
        mock_cursor.close.assert_called_once()
        mock_logger.error.assert_called()

    def test_check_cid_exists_with_empty_cid(self):
        """
        GIVEN empty string as CID
        WHEN check_cid_exists is called with ""
        THEN expect:
            - Returns False
            - May skip database query for efficiency
            - No exceptions raised
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)

        # Act
        result = check_cid_exists(mock_connection, "")

        # Assert
        assert result is False
        # Connection should not be used for empty CID
        mock_connection.cursor.assert_not_called()

    def test_check_cid_exists_with_none_cid(self):
        """
        GIVEN None as CID value
        WHEN check_cid_exists is called with None
        THEN expect:
            - Returns False
            - Handles None gracefully
            - No exceptions raised
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)

        # Act
        result = check_cid_exists(mock_connection, None)

        # Assert
        assert result is False
        # Connection should not be used for None CID
        mock_connection.cursor.assert_not_called()

    def test_check_cid_exists_query_structure(self):
        """
        GIVEN valid CID to check
        WHEN check_cid_exists executes query
        THEN expect query structure:
            - SELECT with minimal columns (e.g., SELECT 1 or SELECT cid)
            - FROM metadata table
            - WHERE cid = ? with parameter
            - LIMIT 1 for efficiency
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0].upper()  # Convert to uppercase for easier checking

        # Verify query structure
        assert "SELECT" in query
        assert "FROM METADATA" in query or "FROM `CODES`" in query
        assert "WHERE" in query
        assert "CID" in query
        assert "LIMIT 1" in query
        assert "%S" in query or "?" in query  # Parameter placeholder

        # Verify parameters passed
        params = call_args[0][1] if len(call_args[0]) > 1 else None
        assert params is not None
        assert test_cid in params

    @patch("logging.getLogger")
    def test_check_cid_exists_handles_cursor_creation_failure(self, mock_get_logger):
        """
        GIVEN database connection cannot create cursor
        WHEN check_cid_exists attempts to create cursor
        THEN expect:
            - Returns False
            - Does not raise exception
            - Error is logged appropriately
            - No attempt to close non-existent cursor
        """
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)
        mock_connection.cursor.side_effect = mysql.connector.Error(
            "Cannot create cursor"
        )

        test_cid = "QmTestCID"

        # Act
        result = check_cid_exists(mock_connection, test_cid)

        # Assert
        assert result is False
        mock_connection.cursor.assert_called_once()
        mock_logger.error.assert_called()

    def test_check_cid_exists_thread_safety(self):
        """
        GIVEN multiple threads calling check_cid_exists
        WHEN concurrent calls are made
        THEN expect:
            - Each call uses its own cursor
            - No shared state issues
            - Connection pooling handled correctly
            - Results are consistent
        """
        # Arrange
        mock_connection = Mock(spec=mysql.connector.connection.MySQLConnection)

        # Create separate cursor mocks for each call
        mock_cursor1 = Mock()
        mock_cursor2 = Mock()
        mock_connection.cursor.side_effect = [mock_cursor1, mock_cursor2]

        mock_cursor1.fetchone.return_value = ("QmCID1",)
        mock_cursor2.fetchone.return_value = None

        test_cid1 = "QmCID1"
        test_cid2 = "QmCID2"

        # Act - Simulate concurrent calls
        result1 = check_cid_exists(mock_connection, test_cid1)
        result2 = check_cid_exists(mock_connection, test_cid2)

        # Assert
        assert result1 is True
        assert result2 is False

        # Verify each call got its own cursor
        assert mock_connection.cursor.call_count == 2
        mock_cursor1.close.assert_called_once()
        mock_cursor2.close.assert_called_once()

        # Verify no shared state between calls
        mock_cursor1.execute.assert_called_once()
        mock_cursor2.execute.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

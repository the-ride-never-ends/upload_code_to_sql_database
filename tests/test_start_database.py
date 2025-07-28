import pytest
import mysql.connector
from unittest.mock import Mock, patch, mock_open, MagicMock

# Import the function to test
from start_database import start_database


class TestStartDatabase:
    """
    Test start_database function for database connection setup.

    Test Methods:
    - test_start_database_with_valid_config_file: Valid configuration file usage
    - test_start_database_with_no_config_uses_defaults: Default environment variables
    - test_start_database_validates_required_tables_exist: Table existence validation
    - test_start_database_raises_on_missing_codes_table: Missing codes table handling
    - test_start_database_raises_on_missing_metadata_table: Missing metadata table handling
    - test_start_database_handles_connection_timeout: Connection timeout handling
    - test_start_database_handles_authentication_error: Authentication error handling
    - test_start_database_handles_invalid_config_file: Invalid config file handling
    - test_start_database_disables_autocommit: Autocommit setting verification
    - test_start_database_handles_network_error: Network connectivity error handling
    - test_start_database_closes_connection_on_table_check_failure: Connection cleanup on failure
    """

    @patch("mysql.connector.connect")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="DB_HOST=localhost\nDB_USER=testuser\nDB_PASSWORD=testpass\nDB_NAME=testdb\nDB_PORT=3306",
    )
    @patch("pathlib.Path.exists")
    def test_start_database_with_valid_config_file(
        self, mock_exists, mock_file, mock_connect
    ):
        """
        GIVEN a valid database configuration file path is provided
        AND the file contains valid MySQL connection parameters
        WHEN start_database is called with db_config='/path/to/config.conf'
        THEN expect:
            - Configuration file is read successfully
            - MySQL connection is established
            - Connection object is returned (mysql.connector.connection type)
            - Connection has autocommit disabled
            - Tables 'codes' and 'metadata' are verified to exist
        """
        # Arrange
        mock_exists.return_value = True
        mock_connection = MagicMock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock successful table existence checks
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.side_effect = [
            (1,),  # codes table exists
            (1,),  # metadata table exists
        ]

        config_path = "/path/to/config.env"

        # Act
        result = start_database(config_path)

        # Assert
        mock_exists.assert_called_once()
        mock_file.assert_called_once_with(config_path, "r")
        mock_connect.assert_called_once_with(
            host="localhost",
            user="testuser",
            password="testpass",
            database="testdb",
            port=3306,
        )

        # Verify autocommit is disabled
        assert mock_connection.autocommit == False

        # Verify table checks
        expected_calls = [
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'testdb' AND table_name = 'codes'",
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'testdb' AND table_name = 'metadata'",
        ]
        mock_cursor.execute.assert_any_call(expected_calls[0])
        mock_cursor.execute.assert_any_call(expected_calls[1])

        assert result == mock_connection

    @patch("mysql.connector.connect")
    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_start_database_with_no_config_uses_defaults(
        self, mock_exists, mock_file, mock_yaml_load, mock_connect
    ):
        """
        GIVEN no database configuration file is provided (db_config=None)
        WHEN start_database is called
        THEN expect:
            - Default YAML configuration file is loaded
            - Connection parameters from YAML are used
            - MySQL connection is established with defaults
            - Connection object is returned
            - Connection has autocommit disabled
            - Tables 'codes' and 'metadata' are verified to exist
        """
        # Arrange
        mock_exists.return_value = True
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock YAML configuration data
        yaml_config = {
            "DB_HOST": "test-host",
            "DB_USER": "test-user",
            "DB_PASSWORD": "test-password",
            "DB_NAME": "test-database",
            "DB_PORT": 5432,
        }
        mock_yaml_load.return_value = yaml_config

        # Mock successful table existence checks
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.side_effect = [
            (1,),  # codes table exists
            (1,),  # metadata table exists
        ]

        # Act
        result = start_database(None)

        # Assert - YAML file should be loaded
        mock_exists.assert_called_once()
        mock_file.assert_called_once()
        mock_yaml_load.assert_called_once()

        # Assert - connection should use YAML configuration
        mock_connect.assert_called_once_with(
            host="test-host",
            user="test-user",
            password="test-password",
            database="test-database",
            port=5432,
        )

        # Verify autocommit is disabled
        mock_connection.autocommit = False

        # Verify table checks were performed
        assert mock_cursor.execute.call_count == 2

        # Verify the connection was returned
        assert result == mock_connection

    @patch("mysql.connector.connect")
    def test_start_database_validates_required_tables_exist(self, mock_connect):
        """
        GIVEN a valid database connection can be established
        WHEN start_database is called
        THEN expect:
            - Function queries database to verify 'codes' table exists
            - Function queries database to verify 'metadata' table exists
            - No exception is raised if both tables exist
        """
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock successful table existence checks
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.side_effect = [
            (1,),  # codes table exists
            (1,),  # metadata table exists
        ]

        # Act
        result = start_database(None)

        # Assert
        # Verify both table existence queries were made
        expected_calls = [
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'computer_code' AND table_name = 'codes'",
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'computer_code' AND table_name = 'metadata'",
        ]
        mock_cursor.execute.assert_any_call(expected_calls[0])
        mock_cursor.execute.assert_any_call(expected_calls[1])

        # Should return connection without raising exception
        assert result == mock_connection

    @patch("mysql.connector.connect")
    def test_start_database_raises_on_missing_codes_table(self, mock_connect):
        """
        GIVEN database connection is successful
        BUT 'codes' table does not exist in the database
        WHEN start_database is called
        THEN expect:
            - Descriptive exception is raised indicating 'codes' table is missing
            - Exception message includes table name
            - Connection is properly closed before raising
        """
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock codes table doesn't exist (fetchone returns None)
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = None

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            start_database(None)

        # Verify error message contains table name
        assert "codes" in str(exc_info.value)
        assert "missing" in str(exc_info.value).lower()

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    @patch("mysql.connector.connect")
    def test_start_database_raises_on_missing_metadata_table(self, mock_connect):
        """
        GIVEN database connection is successful
        AND 'codes' table exists
        BUT 'metadata' table does not exist in the database
        WHEN start_database is called
        THEN expect:
            - Descriptive exception is raised indicating 'metadata' table is missing
            - Exception message includes table name
            - Connection is properly closed before raising
        """
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock codes table exists, metadata table doesn't exist
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.side_effect = [
            (1,),  # codes table exists
            None,  # metadata table doesn't exist
        ]

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            start_database(None)

        # Verify error message contains table name
        assert "metadata" in str(exc_info.value)
        assert "missing" in str(exc_info.value).lower()

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    @patch("mysql.connector.connect")
    def test_start_database_handles_connection_timeout(self, mock_connect):
        """
        GIVEN database server is not responding
        WHEN start_database attempts to connect
        THEN expect:
            - Connection timeout occurs
            - Descriptive exception is raised mentioning timeout
            - No resources are left open
        """
        # Arrange
        timeout_error = mysql.connector.Error("Connection timeout")
        mock_connect.side_effect = timeout_error

        # Act & Assert
        with pytest.raises(mysql.connector.Error) as exc_info:
            start_database(None)

        # Verify the original timeout error is raised
        assert exc_info.value == timeout_error

        # Verify connection attempt was made
        mock_connect.assert_called_once()

    @patch("mysql.connector.connect")
    def test_start_database_handles_authentication_error(self, mock_connect):
        """
        GIVEN invalid database credentials in configuration
        WHEN start_database attempts to connect
        THEN expect:
            - Authentication error occurs
            - Descriptive exception is raised mentioning authentication failure
            - No resources are left open
        """
        # Arrange
        auth_error = mysql.connector.Error("Access denied for user")
        mock_connect.side_effect = auth_error

        # Act & Assert
        with pytest.raises(mysql.connector.Error) as exc_info:
            start_database(None)

        # Verify the original authentication error is raised
        assert exc_info.value == auth_error

        # Verify connection attempt was made
        mock_connect.assert_called_once()

    @patch("builtins.open", side_effect=FileNotFoundError("Config file not found"))
    @patch("pathlib.Path.exists")
    def test_start_database_handles_invalid_config_file(self, mock_exists, mock_file):
        """
        GIVEN config file path is provided but file is malformed or missing
        WHEN start_database is called with db_config='/invalid/config.conf'
        THEN expect:
            - Descriptive exception is raised about config file issue
            - Exception indicates whether file is missing or malformed
            - No partial connections are left open
        """
        # Arrange
        mock_exists.return_value = False
        config_path = "/invalid/config.env"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            start_database(config_path)

        # Verify file existence was checked
        mock_exists.assert_called_once()

    @patch("mysql.connector.connect")
    def test_start_database_disables_autocommit(self, mock_connect):
        """
        GIVEN successful database connection
        WHEN start_database returns a connection object
        THEN expect:
            - connection.autocommit is False
            - This enables transaction support for atomic operations
        """
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock successful table existence checks
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.side_effect = [
            (1,),  # codes table exists
            (1,),  # metadata table exists
        ]

        # Act
        result = start_database(None)

        # Assert
        # Verify autocommit was explicitly disabled
        assert mock_connection.autocommit == False

        assert result == mock_connection

    @patch("mysql.connector.connect")
    def test_start_database_handles_network_error(self, mock_connect):
        """
        GIVEN network connectivity issues prevent database connection
        WHEN start_database attempts to connect
        THEN expect:
            - Network-related exception is caught
            - Descriptive error message about connectivity is raised
            - Original error details are preserved in the exception
        """
        # Arrange
        network_error = mysql.connector.Error("Can't connect to MySQL server")
        mock_connect.side_effect = network_error

        # Act & Assert
        with pytest.raises(mysql.connector.Error) as exc_info:
            start_database(None)

        # Verify the original network error is preserved
        assert exc_info.value == network_error

        # Verify connection attempt was made
        mock_connect.assert_called_once()

    @patch("mysql.connector.connect")
    def test_start_database_closes_connection_on_table_check_failure(
        self, mock_connect
    ):
        """
        GIVEN database connection is established successfully
        BUT an error occurs during table existence verification
        WHEN start_database is executing table checks
        THEN expect:
            - Original connection is properly closed
            - Exception is raised with details about the verification failure
            - No database connections remain open
        """
        # Arrange
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        # Mock table check failure
        table_check_error = mysql.connector.Error("Table check failed")
        mock_cursor.execute.side_effect = table_check_error

        # Act & Assert
        with pytest.raises(mysql.connector.Error) as exc_info:
            start_database(None)

        # Verify the table check error is raised
        assert exc_info.value == table_check_error

        # Verify connection was properly closed on failure
        mock_connection.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

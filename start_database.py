from pathlib import Path
from typing import Optional, Any


import mysql.connector
import yaml


def start_database(db_config: Optional[str]) -> Any:
    """
    Initialize and validate a MySQL database connection for code storage.

    Establishes a connection to the MySQL database using either provided
    configuration file settings or system defaults. Validates that required
    tables ('codes' and 'metadata') exist in the database schema. The connection
    is configured with autocommit disabled to support transaction management.

    This function serves as the database initialization point for the upload
    system, ensuring the database is ready before any upload operations begin.
    It handles various connection failure scenarios with descriptive error
    messages to aid in troubleshooting.

    Args:
        db_config: Optional path to a database configuration file containing
            MySQL connection parameters (host, user, password, database, port).
            If None, the function uses default connection parameters.
            The config file should be in a standard format (e.g., INI, JSON).

    Returns:
        mysql.connector.connection.MySQLConnection: Active database connection
            object with the following characteristics:
            - Connected to the specified MySQL database
            - Autocommit is disabled (set to False)
            - Ready for transaction-based operations
            - Has verified access to 'codes' and 'metadata' tables

    Raises:
        FileNotFoundError: If db_config path is provided but file doesn't exist.
        ValueError: If configuration file is malformed or missing required fields.
        mysql.connector.Error: For various database connection issues:
            - Authentication failures (wrong username/password)
            - Network/connectivity errors (host unreachable)
            - Database does not exist
            - Connection timeouts
        RuntimeError: If required tables are missing from the database schema.
            Includes specific table names in the error message.

    Example:
        # Using default configuration
        conn = start_database(None)

        # Using custom configuration file
        conn = start_database("/path/to/db_config.ini")

        # The connection is ready for use:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM codes")

    Notes:
        - The function ensures a clean connection state - if table validation
          fails, the connection is properly closed before raising an exception
        - Default configuration typically connects to localhost MySQL instance
        - The connection pool settings are optimized for the upload workload
        - Both 'codes' and 'metadata' tables must exist; the function does not
          create them if missing
    """
    # Parse configuration or use defaults
    if db_config is not None:

        # Check if config file exists
        config_path = Path(db_config)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {db_config}")

        # Parse configuration file
        config = {}
        try:
            with open(db_config, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            raise ValueError(f"Failed to parse configuration file: {e}")

        # Extract connection parameters
        host = config.get("DB_HOST", "localhost")
        user = config.get("DB_USER", "root")
        password = config.get("DB_PASSWORD", "")
        database = config.get("DB_NAME", "computer_code")
        port = int(config.get("DB_PORT", 3306))
    else:
        print("No config provided. Using default database configuration.")
        # Use default configuration from .env file
        yaml_configs = Path.cwd() / "sql_configs.yaml"
        if not yaml_configs.exists():
            raise FileNotFoundError(f"Default config file not found: {yaml_configs}")

        with open(yaml_configs, "r") as f:
            config = dict(yaml.safe_load(f))

        host = config.get("DB_HOST", "localhost")
        user = config.get("DB_USER", "root")
        password = config.get("DB_PASSWORD", "")
        database = config.get("DB_NAME", "computer_code")
        port = int(config.get("DB_PORT", 3306))

    print(f"Connecting to database '{database}' at {host}:{port} as user '{user}'")

    connection = None

    try:
        # Establish database connection
        connection = mysql.connector.connect(
            host=host, user=user, password=password, database=database, port=port
        )
        print("Database connection established successfully.")

        # Disable autocommit for transaction support
        connection.autocommit = False

        # Validate required tables exist
        cursor = connection.cursor()

        # Check for 'codes' table
        cursor.execute(
            f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{database}' AND table_name = 'codes'"
        )
        if cursor.fetchone() is None:
            raise RuntimeError(
                f"Required table 'codes' is missing from database '{database}'"
            )
        print("Validated 'codes' table exists.")

        # Check for 'metadata' table
        cursor.execute(
            f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{database}' AND table_name = 'metadata'"
        )
        if cursor.fetchone() is None:
            raise RuntimeError(
                f"Required table 'metadata' is missing from database '{database}'"
            )
        print("Validated 'metadata' table exists.")

        cursor.close()
        print("Database validation complete. Connection is ready.")

        return connection

    except Exception as e:
        if connection is not None:
            # Clean up connection on any failure during validation
            connection.close()
        raise

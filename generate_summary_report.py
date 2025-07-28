from typing import Any
from upload_stats import UploadStats


def generate_summary_report(stats: UploadStats, db_connection: Any) -> None:
    """
    Generate and display a comprehensive summary report of the upload process.

    Prints a formatted report to stdout showing all statistics collected during
    the code upload process. Includes counts of files processed, callables found,
    various skip reasons, successful uploads, and any errors encountered. Also
    queries the database to show the total number of code entries after the
    upload operation.

    The report is designed to give users a clear understanding of what happened
    during the upload process, with special attention to any issues that need
    investigation. Error lists are truncated to prevent overwhelming output
    while still providing useful debugging information.

    Args:
        stats: UploadStats object containing all counters and error lists:
            - files_scanned: Total Python files examined
            - callables_found: Total top-level callables discovered
            - skipped_not_standalone: Methods, nested functions, etc.
            - skipped_no_docstring: Callables without documentation
            - skipped_duplicates: CIDs already in database
            - new_uploads: Successfully inserted entries
            - errors: List of upload failure details
            - parse_errors: List of syntax error details

        db_connection: Active database connection for querying total count.
            Used to show final database size. If query fails, report
            continues without total count.

    Report Structure:
        1. Header with "Upload Complete!" banner
        2. File and callable statistics
        3. Skip reason breakdown
        4. Calculated valid callables (total - skips)
        5. Upload results (new uploads, duplicates)
        6. Error summary count
        7. Database total (if available)
        8. Detailed error listings (first 5 of each type)

    Error Display:
        - Parse Errors section shows file paths with error messages
        - Upload Errors section shows file, callable name, and error
        - Both sections limited to first 5 errors for readability
        - Shows "... and N more" for additional errors
        - Error sections only appear if errors exist

    Format Example:
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
        Errors:                   2

        Database now contains 1,247 code entries

        Parse Errors:
          - /path/to/bad_file.py: invalid syntax (line 42)
          - /path/to/another.py: unexpected indent

        Upload Errors:
          - utils.py (helper_func): Data too long for column

    Database Query:
        - Attempts to SELECT COUNT(*) FROM codes
        - Shows current total if successful
        - Omits database line if query fails
        - Errors in query don't affect report generation

    Output Behavior:
        - All output goes to stdout via print()
        - No return value (None)
        - Fixed-width formatting for alignment
        - Consistent indentation for readability
        - No exceptions raised; errors handled gracefully

    Example:
        stats = UploadStats(
            files_scanned=10,
            callables_found=25,
            skipped_not_standalone=5,
            skipped_no_docstring=3,
            new_uploads=15,
            skipped_duplicates=2
        )

        generate_summary_report(stats, db_connection)
        # Prints formatted report to console

    Notes:
        - Always shows complete statistics even if all zeros
        - Error calculation combines parse and upload errors
        - Database cursor properly closed after query attempt
        - Report generation never fails; partial output preferred
        - Format optimized for terminal display (50-char width)
    """
    # Print header
    print("=" * 50)
    print("Upload Complete!")
    print("=" * 50)

    # Calculate valid callables
    valid_callables = (
        stats.callables_found
        - stats.skipped_not_standalone
        - stats.skipped_no_docstring
    )

    # Calculate total errors
    parse_error_count = len(stats.parse_errors) if stats.parse_errors else 0
    upload_error_count = len(stats.errors) if stats.errors else 0
    total_errors = parse_error_count + upload_error_count

    # Print main statistics with consistent formatting
    print(f"Files scanned:            {stats.files_scanned}")
    print(f"Callables found:          {stats.callables_found}")
    print(f"Skipped (not standalone): {stats.skipped_not_standalone}")
    print(f"Skipped (no docstring):   {stats.skipped_no_docstring}")
    print(f"Valid callables:          {valid_callables}")
    print(f"New uploads:              {stats.new_uploads}")
    print(f"Duplicates skipped:       {stats.skipped_duplicates}")
    print(f"Errors:                   {total_errors}")

    # Query database for total count
    try:
        cursor = db_connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM codes")
            result = cursor.fetchone()
            if result:
                total_count = result[0]
                print(f"\nDatabase now contains {total_count:,} code entries")
        finally:
            cursor.close()
    except Exception:
        # Silently handle database errors - report continues without total
        pass

    # Display parse errors if any exist
    if stats.parse_errors:
        print("\nParse Errors:")
        for i, (file_path, error_msg) in enumerate(stats.parse_errors[:5]):
            print(f"  - {file_path}: {error_msg}")

        if len(stats.parse_errors) > 5:
            remaining = len(stats.parse_errors) - 5
            print(f"  ... and {remaining} more")

    # Display upload errors if any exist
    if stats.errors:
        print("\nUpload Errors:")
        for i, error_dict in enumerate(stats.errors[:5]):
            file_name = error_dict["file"]
            callable_name = error_dict["callable"]
            error_msg = error_dict["error"]
            print(f"  - {file_name} ({callable_name}): {error_msg}")

        if len(stats.errors) > 5:
            remaining = len(stats.errors) - 5
            print(f"  ... and {remaining} more")

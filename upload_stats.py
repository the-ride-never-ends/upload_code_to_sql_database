from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Any


@dataclass
class UploadStats:
    """
    Track and aggregate statistics throughout the code upload process.

    Maintains running counts of all significant events during the upload operation,
    including files processed, callables discovered, various skip reasons, successful
    uploads, and detailed error information. This dataclass serves as the central
    collection point for metrics that are displayed in the final summary report.

    The statistics are updated incrementally as the upload process progresses through
    each file and callable. Error lists accumulate detailed information for debugging
    while counters provide high-level success/failure metrics.

    Attributes:
        files_scanned (int): Total number of Python files discovered and attempted
            to process. Includes files that may have failed parsing. Incremented
            once per file regardless of content or success. Default: 0.

        callables_found (int): Total number of top-level callables (functions,
            classes, etc.) discovered across all files. Includes callables that
            may later be skipped for various reasons. This is the raw count before
            any validation. Default: 0.

        skipped_not_standalone (int): Count of callables skipped because they were
            not standalone module-level definitions. Includes methods within classes,
            nested functions, lambdas, and inner classes. These are excluded from
            upload as they depend on their parent context. Default: 0.

        skipped_no_docstring (int): Count of callables skipped due to missing or
            empty docstrings. Includes cases where docstring is None, empty string,
            or contains only whitespace. These are excluded to maintain code
            quality standards in the database. Default: 0.

        skipped_duplicates (int): Count of callables skipped because their CID
            already exists in the database. Indicates successful deduplication
            where identical code was previously uploaded. Default: 0.

        new_uploads (int): Count of callables successfully inserted into both
            the codes and metadata tables. Represents new, unique code additions
            to the database. Only incremented after successful transaction commit.
            Default: 0.

        errors (List[Dict[str, Any]]): Detailed list of upload failures. Each
            dictionary contains:
            - 'file' (str): Path to the source file
            - 'callable' (str): Name of the callable that failed
            - 'error' (str): Error message or exception details
            Used for debugging and displayed in final report (truncated to first 5).
            Default: empty list.

        parse_errors (List[Tuple[Path, str]]): List of files that failed to parse
            due to syntax errors. Each tuple contains:
            - Path: File path that failed parsing
            - str: Error message from the parser
            These represent files that couldn't be processed at all.
            Default: empty list.

    Derived Metrics:
        The following values are calculated from the base attributes:
        - Valid callables: callables_found - skipped_not_standalone - skipped_no_docstring
        - Total errors: len(errors) + len(parse_errors)
        - Success rate: new_uploads / valid_callables (if valid_callables > 0)

    Usage in Upload Flow:
        1. Created at start of main() with all zeros/empty
        2. files_scanned incremented for each file attempted
        3. callables_found incremented during extraction
        4. Skip counters incremented during validation
        5. new_uploads incremented after successful database insert
        6. Error lists appended when failures occur
        7. Passed to generate_summary_report() for display

    Example:
        # Initialize statistics tracker
        stats = UploadStats()

        # During processing
        stats.files_scanned += 1
        stats.callables_found += 3
        stats.skipped_no_docstring += 1
        stats.new_uploads += 2

        # Record an error
        stats.errors.append({
            'file': 'utils/helpers.py',
            'callable': 'process_data',
            'error': 'Column data too long'
        })

        # Final state might be:
        # files_scanned=10, callables_found=25, skipped_not_standalone=5,
        # skipped_no_docstring=3, skipped_duplicates=2, new_uploads=15,
        # errors=[...], parse_errors=[...]

    Thread Safety:
        This dataclass is not thread-safe. If used in concurrent upload
        scenarios, external synchronization is required for counter updates
        and list modifications.

    Notes:
        - All counters start at 0 and only increment (never decrement)
        - Error lists can grow unbounded; display is truncated in report
        - No validation is performed on counter values
        - Dataclass is mutable; values updated throughout process
        - Field defaults ensure proper initialization without arguments
    """
    files_scanned: int = 0
    callables_found: int = 0
    skipped_not_standalone: int = 0
    skipped_no_docstring: int = 0
    skipped_duplicates: int = 0
    new_uploads: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    parse_errors: List[Tuple[Path, str]] = field(default_factory=list)

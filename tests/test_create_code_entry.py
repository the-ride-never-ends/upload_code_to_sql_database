import pytest
import re
from pathlib import Path
from unittest.mock import patch
from typing import Dict, Any
from functools import cache

# Import the function and CodeEntry class to test
from code_entry.create_code_entry import create_code_entry, CodeEntry


class TestCreateCodeEntry:
    """
    Test create_code_entry function for generating CodeEntry objects with CIDs.

    Test Methods:
    - test_create_code_entry_basic_function: Basic function with all required fields
    - test_create_code_entry_cid_generation_deterministic: Deterministic CID generation
    - test_create_code_entry_metadata_extraction: Metadata dictionary creation
    - test_create_code_entry_test_detection_by_name: Test function detection by name patterns
    - test_create_code_entry_test_detection_by_path: Test function detection by file path
    - test_create_code_entry_code_type_mapping: Mapping of callable types
    - test_create_code_entry_file_path_relative: Relative path conversion
    - test_create_code_entry_tag_extraction_from_path: Tag generation from file paths
    - test_create_code_entry_escapes_strings_for_database: Special character handling
    - test_create_code_entry_handles_missing_docstring: None docstring handling
    - test_create_code_entry_preserves_source_formatting: Source code formatting preservation
    - test_create_code_entry_cid_uses_ipfs_function: IPFS CID generation verification
    - test_create_code_entry_async_function_handling: Async function processing
    """

    @pytest.fixture
    def basic_function_callable_info(self) -> Dict[str, Any]:
        """Sample callable_info for a basic function."""
        return {
            "name": "calculate_sum",
            "type": "function",
            "signature": "def calculate_sum(a: int, b: int) -> int:",
            "docstring": "Calculate the sum of two integers.\n\nArgs:\n    a: First integer\n    b: Second integer\n\nReturns:\n    Sum of a and b",
            "source_code": 'def calculate_sum(a: int, b: int) -> int:\n    """Calculate the sum of two integers.\n\n    Args:\n        a: First integer\n        b: Second integer\n\n    Returns:\n        Sum of a and b\n    """\n    return a + b',
            "line_number": 10,
            "is_async": False,
            "decorators": [],
        }

    @pytest.fixture
    def basic_file_path(self) -> Path:
        """Sample file path for testing."""
        return Path("/home/user/project/math/operations.py")

    @pytest.fixture
    def mock_cid(self) -> str:
        """Static mock CID that follows IPFS format."""
        return "bafkreibbyjbfe3qv7citcoihbxgi4y6yxxdni6ti5olfdzz3t64r3htula"

    def test_create_code_entry_basic_function(
        self, basic_function_callable_info, basic_file_path, mock_cid
    ):
        """
        GIVEN callable_info for a simple function and file_path
        WHEN create_code_entry is called
        THEN expect:
            - Returns CodeEntry instance
            - CID is generated from concatenation of signature + docstring + source_code
            - CID is valid IPFS CID format
            - signature, docstring, computer_code fields match input
            - metadata contains all required fields
        """
        # FIXED: Patch the get_cid function where it's imported in the module
        with patch(
            "code_entry.create_code_entry.get_cid", return_value=mock_cid
        ) as mock_get_cid:
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(
                    basic_function_callable_info, basic_file_path
                )

                # Verify function is called with correct concatenation
                expected_content = (
                    basic_function_callable_info["signature"]
                    + basic_function_callable_info["docstring"]
                    + basic_function_callable_info["source_code"]
                )
                mock_get_cid.assert_called_once_with(expected_content)

                # Verify CodeEntry structure
                assert isinstance(result, CodeEntry)
                assert result.cid == mock_cid
                assert result.signature == basic_function_callable_info["signature"]
                assert result.docstring == basic_function_callable_info["docstring"]
                assert (
                    result.computer_code == basic_function_callable_info["source_code"]
                )

                # Verify CID format (CIDv1 format)
                assert re.match(r"^bafk[a-z2-7]{55}$", result.cid)

                # Verify metadata structure
                assert isinstance(result.metadata, dict)
                required_keys = {
                    "code_cid",
                    "code_name",
                    "code_type",
                    "is_test",
                    "file_path",
                    "tags",
                }
                assert set(result.metadata.keys()) >= required_keys

    def test_create_code_entry_cid_generation_deterministic(
        self, basic_function_callable_info, basic_file_path, mock_cid
    ):
        """
        GIVEN identical callable_info and file_path
        WHEN create_code_entry is called multiple times
        THEN expect:
            - Same CID is generated each time
            - CID generation is deterministic
            - Order of concatenation is always: signature + docstring + source_code
        """
        # FIXED: Correct patching path
        with patch(
            "code_entry.create_code_entry.get_cid", return_value=mock_cid
        ) as mock_get_cid:
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result1 = create_code_entry(
                    basic_function_callable_info, basic_file_path
                )
                result2 = create_code_entry(
                    basic_function_callable_info, basic_file_path
                )

                # Both calls should produce identical results
                assert result1.cid == result2.cid
                assert result1.signature == result2.signature
                assert result1.docstring == result2.docstring
                assert result1.computer_code == result2.computer_code

                # Verify get_cid was called with same content both times
                expected_content = (
                    basic_function_callable_info["signature"]
                    + basic_function_callable_info["docstring"]
                    + basic_function_callable_info["source_code"]
                )
                assert mock_get_cid.call_count == 2
                mock_get_cid.assert_called_with(expected_content)

    def test_create_code_entry_metadata_extraction(
        self, basic_function_callable_info, basic_file_path, mock_cid
    ):
        """
        GIVEN callable_info with various fields
        WHEN create_code_entry is called
        THEN expect metadata dict contains:
            - code_name: matches callable name
            - code_type: correctly mapped from callable type
            - is_test: False for non-test code
            - file_path: relative to current working directory
            - tags: extracted from file path components
        """
        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(
                    basic_function_callable_info, basic_file_path
                )

                metadata = result.metadata
                assert metadata["code_cid"] == mock_cid
                assert metadata["code_name"] == "calculate_sum"
                assert metadata["code_type"] == "function"
                assert metadata["is_test"] is False
                assert metadata["file_path"] == "project/math/operations.py"
                assert isinstance(metadata["tags"], list)
                assert "math" in metadata["tags"]  # Extracted from path

    def test_create_code_entry_test_detection_by_name(self, basic_file_path, mock_cid):
        """
        GIVEN callable_info with names like 'test_function', 'function_test'
        WHEN create_code_entry is called
        THEN expect:
            - metadata['is_test'] is True
            - Detection works for test_ prefix
            - Detection works for _test suffix
        """
        test_cases = [
            {
                "name": "test_calculator",
                "type": "function",
                "signature": "def test_calculator():",
                "docstring": "Test the calculator function.",
                "source_code": 'def test_calculator():\n    """Test the calculator function."""\n    assert add(2, 2) == 4',
                "line_number": 1,
                "is_async": False,
                "decorators": [],
            },
            {
                "name": "calculator_test",
                "type": "function",
                "signature": "def calculator_test():",
                "docstring": "Test the calculator function.",
                "source_code": 'def calculator_test():\n    """Test the calculator function."""\n    assert add(2, 2) == 4',
                "line_number": 1,
                "is_async": False,
                "decorators": [],
            },
        ]

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                for callable_info in test_cases:
                    result = create_code_entry(callable_info, basic_file_path)
                    assert (
                        result.metadata["is_test"] is True
                    ), f"Failed for name: {callable_info['name']}"

    def test_create_code_entry_test_detection_by_path(
        self, basic_function_callable_info, mock_cid
    ):
        """
        GIVEN file_path contains 'test/' or 'tests/' directory
        WHEN create_code_entry is called
        THEN expect:
            - metadata['is_test'] is True
            - Works for files in test/ directory
            - Works for files in tests/ directory
            - Works for nested test directories
        """
        test_paths = [
            Path("/home/user/project/test/test_math.py"),
            Path("/home/user/project/tests/test_math.py"),
            Path("/home/user/project/src/test/unit_tests.py"),
            Path("/home/user/project/tests/unit/test_calculator.py"),
        ]

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                for test_path in test_paths:
                    result = create_code_entry(basic_function_callable_info, test_path)
                    assert (
                        result.metadata["is_test"] is True
                    ), f"Failed for path: {test_path}"

    def test_create_code_entry_code_type_mapping(self, basic_file_path, mock_cid):
        """
        GIVEN callable_info with different types
        WHEN create_code_entry is called
        THEN expect metadata['code_type'] maps correctly:
            - 'function' -> 'function'
            - 'class' -> 'class'
            - 'coroutine' -> 'coroutine'
            - 'generator' -> 'generator'
            - Matches database enum values
        """
        type_test_cases = [
            ("function", "def my_function():", "def my_function():\n    pass"),
            ("class", "class MyClass:", "class MyClass:\n    pass"),
            (
                "coroutine",
                "async def my_coroutine():",
                "async def my_coroutine():\n    pass",
            ),
            ("generator", "def my_generator():", "def my_generator():\n    yield 1"),
        ]

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                for code_type, signature, source in type_test_cases:
                    callable_info = {
                        "name": "test_item",
                        "type": code_type,
                        "signature": signature,
                        "docstring": "Test docstring",
                        "source_code": source,
                        "line_number": 1,
                        "is_async": code_type == "coroutine",
                        "decorators": [],
                    }

                    result = create_code_entry(callable_info, basic_file_path)
                    assert result.metadata["code_type"] == code_type

    def test_create_code_entry_file_path_relative(
        self, basic_function_callable_info, mock_cid
    ):
        """
        GIVEN absolute file_path
        WHEN create_code_entry is called
        THEN expect:
            - metadata['file_path'] is relative to current working directory
            - Absolute paths are converted to relative
            - Path separators are normalized
        """
        absolute_path = Path("/home/user/project/utils/helpers.py")

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(basic_function_callable_info, absolute_path)

                assert result.metadata["file_path"] == "project/utils/helpers.py"
                assert not result.metadata["file_path"].startswith("/")

    def test_create_code_entry_tag_extraction_from_path(
        self, basic_function_callable_info, mock_cid
    ):
        """
        GIVEN file at path like 'utils/database/connection.py'
        WHEN create_code_entry is called
        THEN expect:
            - metadata['tags'] includes path components
            - Tags might include: ['utils', 'database']
            - Common directories excluded from tags
            - Tags are meaningful identifiers
        """
        test_path = Path("/home/user/project/analysis/database/models.py")

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(basic_function_callable_info, test_path)

                tags = result.metadata["tags"]
                assert isinstance(tags, list)
                assert "analysis" in tags
                assert "database" in tags

                # Common directories should be excluded
                excluded_dirs = {
                    "src",
                    "lib",
                    "utils",
                    "common",
                    "shared",
                    "core",
                    "base",
                    "main",
                    "app",
                }
                for excluded in excluded_dirs:
                    assert (
                        excluded not in tags
                    ), f"Excluded directory '{excluded}' found in tags"

    def test_create_code_entry_escapes_strings_for_database(
        self, basic_file_path, mock_cid
    ):
        """
        GIVEN callable_info with special characters in strings
        WHEN create_code_entry is called
        THEN expect:
            - Docstrings with quotes are properly escaped
            - Source code with special chars is preserved
            - SQL injection characters are safe
            - Unicode characters are preserved
        """
        special_char_callable_info = {
            "name": "special_function",
            "type": "function",
            "signature": "def special_function(text: str) -> str:",
            "docstring": """Process text with "quotes" and 'apostrophes'.\n\nHandles unicode: café, naïve, résumé""",
            "source_code": '''def special_function(text: str) -> str:\n    """Process text with "quotes" and 'apostrophes'."""\n    return f"Processed: {text}; DROP TABLE users; --"''',
            "line_number": 1,
            "is_async": False,
            "decorators": [],
        }

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(special_char_callable_info, basic_file_path)

                # Verify that special characters are preserved
                assert '"quotes"' in result.docstring
                assert "'apostrophes'" in result.docstring
                assert "café" in result.docstring
                assert "DROP TABLE" in result.computer_code

                # All fields should be strings (no exceptions raised)
                assert isinstance(result.docstring, str)
                assert isinstance(result.computer_code, str)
                assert isinstance(result.signature, str)

    def test_create_code_entry_handles_missing_docstring(
        self, basic_file_path, mock_cid
    ):
        """
        GIVEN callable_info with docstring=None
        WHEN create_code_entry is called
        THEN expect:
            - CID generation handles None docstring
            - CodeEntry.docstring is empty string or None
            - No exceptions raised
        """
        no_docstring_callable_info = {
            "name": "no_doc_function",
            "type": "function",
            "signature": "def no_doc_function():",
            "docstring": None,
            "source_code": 'def no_doc_function():\n    return "hello"',
            "line_number": 1,
            "is_async": False,
            "decorators": [],
        }

        # FIXED: Correct patching path
        with patch(
            "code_entry.create_code_entry.get_cid", return_value=mock_cid
        ) as mock_get_cid:
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(no_docstring_callable_info, basic_file_path)

                # Verify no exceptions were raised
                assert isinstance(result, CodeEntry)

                # Verify CID generation handled None docstring (should convert to empty string)
                expected_content = (
                    no_docstring_callable_info["signature"]
                    + ""  # None docstring should become empty string
                    + no_docstring_callable_info["source_code"]
                )
                mock_get_cid.assert_called_once_with(expected_content)

                # Docstring should be empty string, not None
                assert result.docstring == ""

    def test_create_code_entry_preserves_source_formatting(
        self, basic_file_path, mock_cid
    ):
        """
        GIVEN source code with specific formatting
        WHEN create_code_entry is called
        THEN expect:
            - computer_code preserves original formatting
            - Indentation is maintained
            - Line breaks are preserved
            - Comments are included
        """
        from textwrap import dedent
        formatted_callable_info = {
            "name": "formatted_function",
            "type": "function",
            "signature": "def formatted_function(data: List[int]) -> int:",
            "docstring": "Calculate sum with specific formatting.",
            "source_code": '''def formatted_function(data: List[int]) -> int:
    """Calculate sum with specific formatting."""
    # Initialize sum
    total = 0

    # Process each item
    for item in data:
        total += item  # Add to running total

    return total  # Return final sum''',
            "line_number": 1,
            "is_async": False,
            "decorators": ["@staticmethod"],
        }

        with patch("code_entry.create_code_entry.get_cid", return_value=mock_cid):
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(formatted_callable_info, basic_file_path)

                # Verify exact formatting preservation
                assert "    # Initialize sum" in result.computer_code
                assert "\n    # Process each item" in result.computer_code
                assert (
                    "        total += item  # Add to running total"
                    in result.computer_code
                )
                assert result.computer_code.count("\n") == formatted_callable_info[
                    "source_code"
                ].count("\n")

    def test_create_code_entry_cid_uses_ipfs_function(
        self, basic_function_callable_info, basic_file_path, mock_cid
    ):
        """
        GIVEN callable_info data
        WHEN create_code_entry calls IPFS CID generation
        THEN expect:
            - IPFS hash function is called with concatenated string
            - Resulting CID follows IPFS format
            - CID is a valid string
        """
        # FIXED: Correct patching path
        with patch(
            "code_entry.create_code_entry.get_cid", return_value=mock_cid
        ) as mock_get_cid:
            with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
                result = create_code_entry(
                    basic_function_callable_info, basic_file_path
                )

                # Verify get_cid was called
                mock_get_cid.assert_called_once()

                # Verify it was called with correct concatenated content
                call_args = mock_get_cid.call_args[0][0]
                assert basic_function_callable_info["signature"] in call_args
                assert basic_function_callable_info["docstring"] in call_args
                assert basic_function_callable_info["source_code"] in call_args

                # Verify CID format
                assert result.cid == mock_cid
                assert re.match(r"^bafk[a-z2-7]{55}$", result.cid)

    def test_create_code_entry_async_function_handling(self, basic_file_path, mock_cid):
        """
        GIVEN callable_info for an async function
        WHEN create_code_entry is called
        THEN expect:
            - Signature includes 'async' keyword
            - code_type is 'coroutine'
            - All other fields handled normally
        """
        async_callable_info = {
            "name": "fetch_data",
            "type": "coroutine",
            "signature": "async def fetch_data(url: str) -> Dict[str, Any]:",
            "docstring": "Fetch data from a URL asynchronously.",
            "source_code": 'async def fetch_data(url: str) -> Dict[str, Any]:\n    """Fetch data from a URL asynchronously."""\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()',
            "line_number": 1,
            "is_async": True,
            "decorators": [],
        }

        # FIXED: Don't patch get_cid here since we want to test with the real CID generation
        # but if we need to patch, use the correct path
        with patch("pathlib.Path.cwd", return_value=Path("/home/user")):
            result = create_code_entry(async_callable_info, basic_file_path)

            assert "async def" in result.signature
            assert result.metadata["code_type"] == "coroutine"
            assert isinstance(result, CodeEntry)
            # FIXED: Don't assert equality with mock_cid since we're not mocking here
            # Instead, just verify it's a valid CID format
            assert re.match(r"^bafk[a-z2-7]{55}$", result.cid)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

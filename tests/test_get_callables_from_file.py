import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from textwrap import dedent


# Import the function to test
from callables.get_callables_from_file import get_callables_from_file


class TestGetCallablesFromFile:
    """
    Test get_callables_from_file function for AST parsing and callable extraction.

    Test Methods:
    - test_get_callables_from_file_with_simple_function: Simple function with docstring
    - test_get_callables_from_file_with_class: Class with methods extraction
    - test_get_callables_from_file_with_async_function: Async function handling
    - test_get_callables_from_file_with_generator: Generator function detection
    - test_get_callables_from_file_with_simple_decorator: Simple decorator parsing
    - test_get_callables_from_file_with_multiple_decorators: Multiple decorator handling
    - test_get_callables_from_file_with_complex_decorator: Decorator with arguments
    - test_get_callables_from_file_skips_nested_functions: Nested function exclusion
    - test_get_callables_from_file_handles_simple_type_hints: Basic type hint preservation
    - test_get_callables_from_file_handles_optional_type_hints: Optional type hint handling
    - test_get_callables_from_file_handles_complex_type_hints: Complex generic type hints
    - test_get_callables_from_file_with_multiline_docstrings: Multi-line docstring parsing
    - test_get_callables_from_file_syntax_error: Syntax error handling
    - test_get_callables_from_file_empty_file: Empty file handling
    - test_get_callables_from_file_no_callables: File with no callable definitions
    - test_get_callables_from_file_file_not_found: Non-existent file handling
    - test_get_callables_from_file_permission_error: Permission error handling
    - test_get_callables_from_file_with_non_standrd_decoding: ASCII encoding handling
    - test_get_callables_from_file_with_special_characters: Special character handling
    - test_get_callables_from_file_line_numbers: Line number accuracy
    - test_get_callables_from_file_lambda_excluded: Lambda expression exclusion
    - test_get_callables_from_file_property_decorator: Property decorator handling
    """

    def test_get_callables_from_file_with_simple_function(self, tmp_path):
        """
        GIVEN a Python file containing a simple function with docstring
        WHEN get_callables_from_file is called
        THEN expect:
            - Returns list with one dictionary
            - Dictionary contains all required keys: name, type, signature, docstring,
              source_code, line_number, is_async, decorators
            - 'type' is 'function'
            - 'signature' includes parameter names and type hints if present
            - 'docstring' contains the raw docstring text
            - 'source_code' includes the complete function definition
            - 'is_async' is False
            - 'decorators' is empty list
        """
        # Create test file with simple function
        test_file = tmp_path / "simple_function.py"
        test_content = dedent(
            """
            def greet(name: str) -> str:
                '''Return a greeting message.'''
                return f"Hello, {name}!"
        """
        ).strip()
        test_file.write_text(test_content)

        # Call function under test
        result = get_callables_from_file(test_file)

        # Assertions
        assert len(result) == 1
        callable_info = result[0]

        # Check all required keys exist
        required_keys = {
            "name",
            "type",
            "signature",
            "docstring",
            "source_code",
            "line_number",
            "is_async",
            "decorators",
        }
        assert set(callable_info.keys()) == required_keys

        # Check specific values
        assert callable_info["name"] == "greet"
        assert callable_info["type"] == "function"
        assert callable_info["signature"] == "def greet(name: str) -> str:"
        assert callable_info["docstring"] == "Return a greeting message."
        assert "def greet(name: str) -> str:" in callable_info["source_code"]
        assert 'return f"Hello, {name}!"' in callable_info["source_code"]
        assert callable_info["line_number"] == 1
        assert callable_info["is_async"] is False
        assert callable_info["decorators"] == []

    def test_get_callables_from_file_with_class(self, tmp_path):
        """
        GIVEN a Python file containing a class with docstring
        WHEN get_callables_from_file is called
        THEN expect:
            - Returns list with one dictionary for the class
            - 'type' is 'class'
            - 'signature' includes class name and base classes if any
            - 'docstring' contains the class docstring
            - 'source_code' includes entire class definition with all methods
            - Methods within class are NOT returned as separate entries
        """
        test_file = tmp_path / "test_class.py"
        test_content = dedent(
            """
            class Calculator:
                '''A simple calculator class.'''

                def add(self, a: int, b: int) -> int:
                    '''Add two numbers.'''
                    return a + b

                def multiply(self, a: int, b: int) -> int:
                    '''Multiply two numbers.'''
                    return a * b
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1  # Only class, not methods
        class_info = result[0]

        assert class_info["name"] == "Calculator"
        assert class_info["type"] == "class"
        assert class_info["signature"] == "class Calculator:"
        assert class_info["docstring"] == "A simple calculator class."
        assert "def add(self, a: int, b: int) -> int:" in class_info["source_code"]
        assert "def multiply(self, a: int, b: int) -> int:" in class_info["source_code"]
        assert class_info["line_number"] == 1
        assert class_info["is_async"] is False
        assert class_info["decorators"] == []

    def test_get_callables_from_file_with_async_function(self, tmp_path):
        """
        GIVEN a Python file containing an async function
        WHEN get_callables_from_file is called
        THEN expect:
            - 'type' is 'coroutine'
            - 'is_async' is True
            - 'signature' includes async keyword
            - All other fields populated correctly
        """
        test_file = tmp_path / "async_function.py"
        test_content = dedent(
            """
            async def fetch_data(url: str) -> dict:
                '''Fetch data from a URL asynchronously.'''
                # Simulated async operation
                return {"data": "example"}
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1
        async_info = result[0]

        assert async_info["name"] == "fetch_data"
        assert async_info["type"] == "coroutine"
        assert async_info["signature"] == "async def fetch_data(url: str) -> dict:"
        assert async_info["docstring"] == "Fetch data from a URL asynchronously."
        assert async_info["is_async"] is True
        assert async_info["decorators"] == []

    def test_get_callables_from_file_with_generator(self, tmp_path):
        """
        GIVEN a Python file containing a generator function (uses yield)
        WHEN get_callables_from_file is called
        THEN expect:
            - 'type' is 'generator'
            - Function body contains yield statement
            - All other fields populated correctly
        """
        test_file = tmp_path / "generator_function.py"
        test_content = dedent(
            """
            def count_up(limit: int):
                '''Generate numbers from 0 to limit.'''
                for i in range(limit):
                    yield i
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1
        gen_info = result[0]

        assert gen_info["name"] == "count_up"
        assert gen_info["type"] == "generator"
        assert gen_info["signature"] == "def count_up(limit: int):"
        assert gen_info["docstring"] == "Generate numbers from 0 to limit."
        assert "yield i" in gen_info["source_code"]
        assert gen_info["is_async"] is False

    def test_get_callables_from_file_with_simple_decorator(self, tmp_path):
        """
        GIVEN a Python file with a simple decorator
        WHEN get_callables_from_file is called
        THEN expect:
            - 'decorators' list contains decorator name as string
            - 'source_code' includes decorator line
        """
        test_file = tmp_path / "simple_decorator.py"
        test_content = dedent(
            """
            @staticmethod
            def simple_decorated():
                '''A simple decorated function.'''
                pass
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1
        func_info = result[0]

        assert func_info["decorators"] == ["staticmethod"]
        assert "@staticmethod" in func_info["source_code"]

    def test_get_callables_from_file_with_multiple_decorators(self, tmp_path):
        """
        GIVEN a Python file with multiple decorators
        WHEN get_callables_from_file is called
        THEN expect:
            - 'decorators' list contains all decorator names in order
            - 'source_code' includes all decorator lines
        """
        test_file = tmp_path / "multiple_decorators.py"
        test_content = dedent(
            """
            @property
            @cached
            def multi_decorated():
                '''Multiple decorators.'''
                pass
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1
        func_info = result[0]

        assert func_info["decorators"] == ["property", "cached"]
        assert "@property" in func_info["source_code"]
        assert "@cached" in func_info["source_code"]

    def test_get_callables_from_file_with_complex_decorator(self, tmp_path):
        """
        GIVEN a Python file with decorator that has arguments
        WHEN get_callables_from_file is called
        THEN expect:
            - 'decorators' list contains decorator with arguments
            - 'source_code' includes complete decorator with arguments
        """
        test_file = tmp_path / "complex_decorator.py"
        test_content = dedent(
            """
            @app.route('/api', methods=['GET', 'POST'])
            def complex_decorated():
                '''Decorator with arguments.'''
                pass
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1
        func_info = result[0]

        assert func_info["decorators"] == ["app.route('/api', methods=['GET', 'POST'])"]
        assert "@app.route('/api', methods=['GET', 'POST'])" in func_info["source_code"]

    def test_get_callables_from_file_skips_nested_functions(self, tmp_path):
        """
        GIVEN a Python file with functions defined inside other functions
        WHEN get_callables_from_file is called
        THEN expect:
            - Only top-level function is returned
            - Nested functions are not in the returned list
            - Parent function's source_code includes the nested function
        """
        test_file = tmp_path / "nested_functions.py"
        test_content = dedent(
            """
            def outer_function():
                '''Outer function with nested function.'''
                def inner_function():
                    '''This should not be returned.'''
                    return "inner"
                return inner_function()
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1  # Only outer function
        outer_info = result[0]

        assert outer_info["name"] == "outer_function"
        assert "def inner_function():" in outer_info["source_code"]
        assert "This should not be returned." in outer_info["source_code"]

    def test_get_callables_from_file_handles_simple_type_hints(self, tmp_path):
        """
        GIVEN function with simple type hints
        WHEN get_callables_from_file is called
        THEN expect 'signature' preserves type hint information
        """
        test_file = tmp_path / "simple_type_hints.py"
        test_content = "def simple_types(name: str, age: int) -> bool:\n    '''Test function.'''\n    pass"
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)
        assert len(result) == 1

        func_info = result[0]
        assert (
            func_info["signature"] == "def simple_types(name: str, age: int) -> bool:"
        )

    def test_get_callables_from_file_handles_optional_type_hints(self, tmp_path):
        """
        GIVEN function with Optional and Union type hints
        WHEN get_callables_from_file is called
        THEN expect 'signature' preserves complex type hint information
        """
        test_file = tmp_path / "optional_type_hints.py"
        test_content = "def optional_types(value: Optional[str], data: Union[int, str]) -> Optional[Dict[str, Any]]:\n    '''Test function.'''\n    pass"
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)
        assert len(result) == 1

        func_info = result[0]
        assert (
            func_info["signature"]
            == "def optional_types(value: Optional[str], data: Union[int, str]) -> Optional[Dict[str, Any]]:"
        )

    def test_get_callables_from_file_handles_complex_type_hints(self, tmp_path):
        """
        GIVEN function with very complex generic type hints
        WHEN get_callables_from_file is called
        THEN expect 'signature' preserves complex generic type information
        """
        test_file = tmp_path / "complex_type_hints.py"
        test_content = "def complex_types(items: List[Dict[str, List[Optional[int]]]]) -> Callable[[str], Awaitable[Dict[str, Any]]]:\n    '''Test function.'''\n    pass"
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)
        assert len(result) == 1

        func_info = result[0]
        assert (
            func_info["signature"]
            == "def complex_types(items: List[Dict[str, List[Optional[int]]]]) -> Callable[[str], Awaitable[Dict[str, Any]]]:"
        )

    def test_get_callables_from_file_with_multiline_docstrings(self, tmp_path):
        """
        GIVEN functions with multi-line docstrings (triple quotes)
        WHEN get_callables_from_file is called
        THEN expect:
            - 'docstring' contains entire docstring with newlines preserved
            - Leading indentation is preserved as in source
            - Triple quotes are not included in docstring value
        """
        test_file = tmp_path / "multiline_docstring.py"
        test_content = dedent(
            '''
            def documented_function():
                """
                This is a multi-line docstring.

                It contains multiple paragraphs and preserves
                formatting including:
                - Bullet points
                - Line breaks

                Args:
                    None

                Returns:
                    str: A sample return value
                """
                return "example"
        '''
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)
        import pprint

        assert len(result) == 1
        func_info = result[0]
        pprint.pprint(func_info["docstring"])

        expected_docstring = dedent(
            """
            This is a multi-line docstring.

            It contains multiple paragraphs and preserves
            formatting including:
            - Bullet points
            - Line breaks

            Args:
                None

            Returns:
                str: A sample return value
        """
        ).strip()
        pprint.pprint(expected_docstring)

        assert func_info["docstring"] == expected_docstring
        assert '"""' not in func_info["docstring"]

    def test_get_callables_from_file_syntax_error(self, tmp_path):
        """
        GIVEN a Python file with syntax errors
        WHEN get_callables_from_file is called
        THEN expect:
            - Raises SyntaxError with appropriate message
            - Error includes line number and error details
            - No partial results are returned
        """
        test_file = tmp_path / "syntax_error.py"
        test_content = dedent(
            """
            def broken_function(
                '''Missing closing parenthesis'''
                return "broken"
        """
        ).strip()
        test_file.write_text(test_content)

        with pytest.raises(SyntaxError) as exc_info:
            get_callables_from_file(test_file)

        # Verify error contains useful information
        assert "syntax" in str(exc_info.value).lower()

    def test_get_callables_from_file_empty_file(self, tmp_path):
        """
        GIVEN an empty Python file
        WHEN get_callables_from_file is called
        THEN expect:
            - Returns empty list []
            - No exceptions raised
        """
        test_file = tmp_path / "empty_file.py"
        test_file.write_text("")

        result = get_callables_from_file(test_file)

        assert result == []

    def test_get_callables_from_file_no_callables(self, tmp_path):
        """
        GIVEN a Python file with only imports, constants, and standalone code
        WHEN get_callables_from_file is called
        THEN expect:
            - Returns empty list []
            - No exceptions raised
        """
        test_file = tmp_path / "no_callables.py"
        test_content = dedent(
            """
            import os
            from pathlib import Path

            # Constants
            VERSION = "1.0.0"
            DEBUG = True

            # Standalone code
            if __name__ == "__main__":
                print("Running standalone")
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert result == []

    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    def test_get_callables_from_file_file_not_found(self, mock_file):
        """
        GIVEN a non-existent file path
        WHEN get_callables_from_file is called
        THEN expect FileNotFoundError to be raised
        """
        fake_path = Path("/non/existent/file.py")

        with pytest.raises(FileNotFoundError):
            get_callables_from_file(fake_path)

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_get_callables_from_file_permission_error(self, mock_file):
        """
        GIVEN a file without read permissions
        WHEN get_callables_from_file is called
        THEN expect PermissionError to be raised
        """
        restricted_path = Path("/restricted/file.py")

        with pytest.raises(PermissionError):
            get_callables_from_file(restricted_path)

    def test_get_callables_from_file_with_non_standrd_decoding(self, tmp_path):
        """
        GIVEN a Python file with non-UTF8 encoding
        WHEN get_callables_from_file is called
        THEN expect:
            - File is read successfully with proper encoding detection
            - Special characters in docstrings/code are preserved
            - No UnicodeDecodeError raised
        """
        # Test with various encodings using mock
        test_content = 'def nothing_but_ascii(): """I am nothing but ascii"""; pass'

        with patch(
            "builtins.open",
            mock_open(read_data=test_content.encode("ascii").decode("ascii")),
        ):
            # Mock successful UTF-8 reading
            fake_path = Path("special_chars.py")
            result = get_callables_from_file(fake_path)

            assert len(result) == 1
            assert result[0]["name"] == "nothing_but_ascii"
            assert "I am nothing but ascii" in result[0]["docstring"]

    def test_get_callables_from_file_with_special_characters(self, tmp_path):
        """
        GIVEN a Python file with special characters
        WHEN get_callables_from_file is called
        THEN expect:
            - File is read successfully with proper encoding detection
            - Special characters in docstrings/code are preserved
            - No UnicodeDecodeError raised
        """
        # Test with various encodings using mock
        test_content = (
            'def café(): """Función con caracteres especiales: ñáéíóú"""; pass'
        )

        with patch(
            "builtins.open",
            mock_open(read_data=test_content.encode("utf-8").decode("utf-8")),
        ):
            # Mock successful UTF-8 reading
            fake_path = Path("special_chars.py")
            result = get_callables_from_file(fake_path)

            assert len(result) == 1
            assert result[0]["name"] == "café"
            assert "ñáéíóú" in result[0]["docstring"]

    def test_get_callables_from_file_line_numbers(self, tmp_path):
        """
        GIVEN a file with multiple callables at different positions
        WHEN get_callables_from_file is called
        THEN expect:
            - 'line_number' accurately reflects starting line of each callable
            - Line numbers are 1-based (not 0-based)
            - Decorators are included in line number calculation
        """
        test_file = tmp_path / "line_numbers.py"
        test_content = dedent(
            """
            # Comment line 1

            def first_function():
                '''First function on line 4.'''
                pass

            # More comments

            @decorator
            def second_function():
                '''Second function starts at decorator on line 11.'''
                pass

            class TestClass:
                '''Class starts on line 16.'''
                pass
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 3

        # Sort by line number to ensure consistent ordering
        result.sort(key=lambda x: x["line_number"])

        assert result[0]["name"] == "first_function"
        assert result[0]["line_number"] == 3  # def first_function line

        assert result[1]["name"] == "second_function"
        assert result[1]["line_number"] == 9  # @decorator line

        assert result[2]["name"] == "TestClass"
        assert result[2]["line_number"] == 14  # class TestClass line

    def test_get_callables_from_file_lambda_excluded(self, tmp_path):
        """
        GIVEN a file containing lambda expressions assigned to variables
        WHEN get_callables_from_file is called
        THEN expect:
            - Lambda expressions are not included in results
            - Only named function/class definitions are returned
        """
        test_file = tmp_path / "lambda_test.py"
        test_content = dedent(
            """
            # Lambda expressions should be excluded
            square = lambda x: x * x
            add = lambda a, b: a + b

            def real_function():
                '''This should be included.'''
                return "included"

            # More lambdas
            multiply = lambda x, y: x * y
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1  # Only real_function
        assert result[0]["name"] == "real_function"
        assert result[0]["type"] == "function"

    def test_get_callables_from_file_property_decorator(self, tmp_path):
        """
        GIVEN a class with @property decorated methods
        WHEN get_callables_from_file is called
        THEN expect:
            - Only the class itself is returned
            - Class source_code includes all property methods
            - Property methods are not returned as separate callables
        """
        test_file = tmp_path / "property_test.py"
        test_content = dedent(
            """
            class Circle:
                '''A circle class with properties.'''

                def __init__(self, radius):
                    self._radius = radius

                @property
                def radius(self):
                    '''Get the radius.'''
                    return self._radius

                @radius.setter
                def radius(self, value):
                    '''Set the radius.'''
                    self._radius = value

                @property
                def area(self):
                    '''Calculate the area.'''
                    return 3.14159 * self._radius ** 2
        """
        ).strip()
        test_file.write_text(test_content)

        result = get_callables_from_file(test_file)

        assert len(result) == 1  # Only the Circle class
        class_info = result[0]

        assert class_info["name"] == "Circle"
        assert class_info["type"] == "class"
        assert "@property" in class_info["source_code"]
        assert "def radius(self):" in class_info["source_code"]
        assert "def area(self):" in class_info["source_code"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

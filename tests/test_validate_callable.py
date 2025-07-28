import pytest
import copy


# Import the function to test
from callables.validate_callable import validate_callable


class TestValidateCallable:
    """
    Test validate_callable function for checking if callables meet upload criteria.

    Test Methods:
    - test_validate_callable_with_valid_function: Valid top-level function with docstring
    - test_validate_callable_with_valid_class: Valid top-level class with docstring
    - test_validate_callable_function_without_docstring: Function with None docstring
    - test_validate_callable_function_with_empty_docstring: Function with empty string docstring
    - test_validate_callable_function_with_whitespace_only_docstring: Function with whitespace-only docstring
    - test_validate_callable_nested_function: Function defined inside another function
    - test_validate_callable_class_method: Method inside a class
    - test_validate_callable_lambda_function: Lambda function (not standalone)
    - test_validate_callable_does_not_modify_input: Ensures no side effects on input dict
    - test_validate_callable_with_valid_async_function: Valid async function with docstring
    - test_validate_callable_with_valid_generator: Valid generator function with docstring
    - test_validate_callable_staticmethod: Static method in a class (not standalone)
    - test_validate_callable_classmethod: Class method (not standalone)
    - test_validate_callable_inner_class: Class defined inside another class
    """

    def test_validate_callable_with_valid_function(self):
        """
        GIVEN a callable_info dict for a top-level function with docstring
        WHEN validate_callable is called
        THEN expect:
            - Returns None (indicating valid)
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "calculate_sum",
            "type": "function",
            "signature": "def calculate_sum(numbers: List[int]) -> int:",
            "docstring": "Calculate the sum of numbers.",
            "source_code": 'def calculate_sum(numbers: List[int]) -> int:\n    """Calculate the sum of numbers."""\n    return sum(numbers)',
            "line_number": 10,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result is None
        assert callable_info == original_info

    def test_validate_callable_with_valid_class(self):
        """
        GIVEN a callable_info dict for a top-level class with docstring
        WHEN validate_callable is called
        THEN expect:
            - Returns None (indicating valid)
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "DataProcessor",
            "type": "class",
            "signature": "class DataProcessor:",
            "docstring": "A class for processing data efficiently.",
            "source_code": 'class DataProcessor:\n    """A class for processing data efficiently."""\n    def __init__(self):\n        pass',
            "line_number": 1,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result is None
        assert callable_info == original_info

    def test_validate_callable_function_without_docstring(self):
        """
        GIVEN a callable_info dict with docstring=None
        WHEN validate_callable is called
        THEN expect:
            - Returns "no_docstring"
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "helper_func",
            "type": "function",
            "signature": "def helper_func() -> None:",
            "docstring": None,
            "source_code": "def helper_func():\n    pass",
            "line_number": 15,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "no_docstring"
        assert callable_info == original_info

    def test_validate_callable_function_with_empty_docstring(self):
        """
        GIVEN a callable_info dict with docstring="" (empty string)
        WHEN validate_callable is called
        THEN expect:
            - Returns "no_docstring"
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "empty_doc_func",
            "type": "function",
            "signature": "def empty_doc_func() -> str:",
            "docstring": "",
            "source_code": 'def empty_doc_func() -> str:\n    """"""\n    return "hello"',
            "line_number": 5,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "no_docstring"
        assert callable_info == original_info

    def test_validate_callable_function_with_whitespace_only_docstring(self):
        """
        GIVEN a callable_info dict with docstring containing only whitespace
        WHEN validate_callable is called
        THEN expect:
            - Returns "no_docstring"
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "whitespace_doc_func",
            "type": "function",
            "signature": "def whitespace_doc_func() -> int:",
            "docstring": "   \n\t  \r\n   ",
            "source_code": 'def whitespace_doc_func() -> int:\n    """   \n\t  \r\n   """\n    return 42',
            "line_number": 8,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "no_docstring"
        assert callable_info == original_info

    def test_validate_callable_nested_function(self):
        """
        GIVEN a callable_info dict indicating a nested function
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Detects nesting from context/metadata in callable_info
        """
        callable_info = {
            "name": "inner_helper",
            "type": "function",
            "signature": "def inner_helper(x: int) -> int:",
            "docstring": "Helper function inside another function.",
            "source_code": 'def outer_func():\n    def inner_helper(x: int) -> int:\n        """Helper function inside another function."""\n        return x * 2\n    return inner_helper',
            "line_number": 2,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info

    def test_validate_callable_class_method(self):
        """
        GIVEN a callable_info dict for a method inside a class
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Methods are not considered standalone callables
        """
        callable_info = {
            "name": "get_value",
            "type": "function",
            "signature": "def get_value(self) -> int:",
            "docstring": "Get the value from the instance.",
            "source_code": 'class MyClass:\n    def get_value(self) -> int:\n        """Get the value from the instance."""\n        return self.value',
            "line_number": 2,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info

    def test_validate_callable_lambda_function(self):
        """
        GIVEN a callable_info dict representing a lambda function
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Lambdas are not considered valid for upload
        """
        callable_info = {
            "name": "<lambda>",
            "type": "function",
            "signature": "lambda x: x * 2",
            "docstring": None,
            "source_code": "square = lambda x: x * 2",
            "line_number": 10,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info

    def test_validate_callable_does_not_modify_input(self):
        """
        GIVEN any callable_info dictionary
        WHEN validate_callable is called multiple times
        THEN expect:
            - Input dictionary remains unchanged
            - Same result returned each time
            - Function has no side effects
        """
        callable_info = {
            "name": "test_function",
            "type": "function",
            "signature": "def test_function() -> str:",
            "docstring": "A test function.",
            "source_code": 'def test_function() -> str:\n    """A test function."""\n    return "test"',
            "line_number": 1,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        # Call multiple times
        result1 = validate_callable(callable_info)
        result2 = validate_callable(callable_info)
        result3 = validate_callable(callable_info)

        # Verify same result each time
        assert result1 == result2 == result3
        assert result1 is None  # Should be valid

        # Verify input unchanged
        assert callable_info == original_info

    def test_validate_callable_with_valid_async_function(self):
        """
        GIVEN a callable_info dict for a top-level async function with docstring
        WHEN validate_callable is called
        THEN expect:
            - Returns None (async functions are valid if standalone with docstring)
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "fetch_data",
            "type": "function",
            "signature": "async def fetch_data(url: str) -> dict:",
            "docstring": "Asynchronously fetch data from a URL.",
            "source_code": 'async def fetch_data(url: str) -> dict:\n    """Asynchronously fetch data from a URL."""\n    # async implementation\n    return {}',
            "line_number": 15,
            "is_async": True,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result is None
        assert callable_info == original_info

    def test_validate_callable_with_valid_generator(self):
        """
        GIVEN a callable_info dict for a top-level generator function with docstring
        WHEN validate_callable is called
        THEN expect:
            - Returns None (generators are valid if standalone with docstring)
            - Input dictionary is not modified
        """
        callable_info = {
            "name": "generate_numbers",
            "type": "function",
            "signature": "def generate_numbers(n: int) -> Iterator[int]:",
            "docstring": "Generate numbers from 0 to n-1.",
            "source_code": 'def generate_numbers(n: int) -> Iterator[int]:\n    """Generate numbers from 0 to n-1."""\n    for i in range(n):\n        yield i',
            "line_number": 20,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result is None
        assert callable_info == original_info

    def test_validate_callable_staticmethod(self):
        """
        GIVEN a callable_info dict for a static method in a class
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Static methods are still methods, not standalone
        """
        callable_info = {
            "name": "utility_method",
            "type": "function",
            "signature": "def utility_method(x: int) -> int:",
            "docstring": "A static utility method.",
            "source_code": 'class MyClass:\n    @staticmethod\n    def utility_method(x: int) -> int:\n        """A static utility method."""\n        return x * 2',
            "line_number": 3,
            "is_async": False,
            "decorators": ["staticmethod"],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info

    def test_validate_callable_classmethod(self):
        """
        GIVEN a callable_info dict for a class method
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Class methods are not standalone
        """
        callable_info = {
            "name": "create_instance",
            "type": "function",
            "signature": "def create_instance(cls, value: int):",
            "docstring": "Create a new instance of the class.",
            "source_code": 'class MyClass:\n    @classmethod\n    def create_instance(cls, value: int):\n        """Create a new instance of the class."""\n        return cls(value)',
            "line_number": 3,
            "is_async": False,
            "decorators": ["classmethod"],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info

    def test_validate_callable_inner_class(self):
        """
        GIVEN a callable_info dict for a class defined inside another class
        WHEN validate_callable is called
        THEN expect:
            - Returns "not_standalone"
            - Nested classes are not considered standalone
        """
        callable_info = {
            "name": "InnerClass",
            "type": "class",
            "signature": "class InnerClass:",
            "docstring": "A class defined inside another class.",
            "source_code": 'class OuterClass:\n    class InnerClass:\n        """A class defined inside another class."""\n        def __init__(self):\n            pass',
            "line_number": 2,
            "is_async": False,
            "decorators": [],
        }
        original_info = copy.deepcopy(callable_info)

        result = validate_callable(callable_info)

        assert result == "not_standalone"
        assert callable_info == original_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

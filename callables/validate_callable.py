import re
from typing import Dict, Any, Optional


def validate_callable(callable_info: Dict[str, Any]) -> Optional[str]:
    """
    Validate whether a callable meets the criteria for database upload.

    Examines a callable's metadata to determine if it should be uploaded to
    the database. A callable is valid only if it is a standalone, top-level
    definition with a non-empty docstring. This function enforces the quality
    standards for the code database by filtering out incomplete or dependent
    code fragments.

    The validation is performed without modifying the input dictionary,
    ensuring this is a pure function with no side effects. The function
    checks multiple criteria to determine validity.

    Args:
        callable_info: Dictionary containing callable metadata as returned by
            get_callables_from_file().
            Each dictionary contains:
            - name (str): The callable's identifier (function or class name)
            - type (str): One of 'function', 'class', 'coroutine', 'generator'
            - signature (str): Complete signature with parameters and type hints
                Format: "def name(param: type, ...) -> return_type:"
            - docstring (Optional[str]): Raw docstring if present, None otherwise
                Preserves original formatting and indentation
            - source_code (str): Complete source including decorators and body
                Maintains original formatting, comments, and whitespace
            - line_number (int): Starting line number in file (1-based)
            - is_async (bool): True for async functions, False otherwise
            - decorators (List[str]): List of decorator names in order applied

    Returns:
        None: If the callable is valid for upload (standalone with docstring)
        str: Reason for rejection if invalid:
            - "not_standalone": Callable is a method, nested function, lambda,
                or otherwise not a module-level definition
            - "no_docstring": Callable lacks a docstring or has empty/whitespace
                only docstring

    Validation Rules:
        1. Standalone Check:
           - Must be defined at module level (not nested)
           - Must not be a class method or instance method
           - Must not be a lambda expression
           - Must not be defined inside another function
           - Must not be an inner class

        2. Docstring Check:
           - Must have a non-None docstring
           - Docstring must contain non-whitespace characters
           - Empty strings and whitespace-only strings are rejected

    Example:
        # Valid top-level function with docstring
        callable_info = {
            'name': 'calculate_sum',
            'type': 'function',
            'signature': 'def calculate_sum(numbers: List[int]) -> int:',
            'docstring': 'Calculate the sum of numbers.',
            'source_code': 'def calculate_sum(numbers: List[int]) -> int:\n    '''Calculate the sum of numbers.'''\n    return sum(numbers)',
            'line_number': 10,
            'is_async': False,
            'decorators': []
        }
        result = validate_callable(callable_info)
        # Returns: None (valid)

        # Invalid: method inside a class
        callable_info = {
            'name': 'get_value',
            'type': 'function',
            'docstring': 'Get the value.',
            'signature': 'def get_value(self) -> int:',
            'source_code': 'class MyClass:\n    def get_value(self):\n        '''Get the value.''''\n        return 420',
            'line_number': 5,
            'is_async': False,
            'decorators': []
        }
        result = validate_callable(callable_info)
        # Returns: "not_standalone"

        # Invalid: missing docstring
        callable_info = {
            'name': 'helper_func',
            'type': 'function',
            'signature': 'def helper_func() -> None:',
            'docstring': None,
            'source_code': 'def helper_func():\n    pass',
            'line_number': 15,
            'is_async': False,
            'decorators': []
        }
        result = validate_callable(callable_info)
        # Returns: "no_docstring"

    Notes:
        - Async functions and generators are valid if they meet other criteria
        - Static methods and class methods are considered "not_standalone"
        - Property decorators make a function "not_standalone"
        - The function is deterministic - same input always produces same output
        - Input dictionary is never modified (immutable operation)
    """
    # Check if it's a lambda function first, since they are not standalone nor have docstrings.
    name = callable_info.get("name", "")
    if name == "<lambda>":
        return "not_standalone"

    # Check docstring first - must be non-None and contain non-whitespace characters
    docstring = callable_info.get("docstring")
    if docstring is None or not docstring.strip():
        return "no_docstring"

    # Check for method decorators that indicate non-standalone callables
    decorators = callable_info.get("decorators", [])
    method_decorators = {"staticmethod", "classmethod", "property"}
    if any(decorator in method_decorators for decorator in decorators):
        return "not_standalone"

    # Check if it's a method by examining the signature for 'self' or 'cls' parameter
    signature = callable_info.get("signature", "")
    if callable_info.get("type") == "function":
        # Extract parameter list from signature
        # Look for patterns like "def name(self" or "def name(cls"
        match = re.search(r"def\s+\w+\s*\(\s*(\w+)", signature)
        if match:
            first_param = match.group(1)
            if first_param in ("self", "cls"):
                return "not_standalone"

    # Check if it's nested by analyzing the source code
    source_code = callable_info.get("source_code", "")

    # Look for indentation patterns that suggest nesting
    lines = source_code.split("\n")

    # Find the line where this callable is defined
    callable_type = callable_info.get("type", "")
    match callable_type:
        case "function":
            # Look for the function definition line
            func_def_pattern = rf"(async\s+)?def\s+{re.escape(name)}\s*\("
        case "class":
            # Look for the class definition line
            func_def_pattern = rf"class\s+{re.escape(name)}\s*[:\(]"
        case _:
            # For other types, use a generic pattern
            func_def_pattern = rf"(async\s+)?def\s+{re.escape(name)}\s*\("

    definition_line_found = False
    for line in lines:
        if re.search(func_def_pattern, line):
            # Check if this line has leading whitespace (indicating nesting)
            if line.startswith(" ") or line.startswith("\t"):
                return "not_standalone"
            definition_line_found = True
            break

    # If we didn't find the definition line in a clean way,
    # check for other indicators of nesting in the source
    if not definition_line_found:
        # Look for patterns that indicate the callable is inside another structure
        # Check if there are class or function definitions before our callable
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # If we find a class or function definition with proper indentation,
            # and our callable is later with more indentation, it's nested
            if (
                re.match(r"(class|def|async\s+def)\s+", stripped)
                and not line.startswith(" ")
                and not line.startswith("\t")
            ):
                # This is a top-level definition, which is fine
                continue

            # If we find our callable definition but it's indented, it's nested
            if re.search(func_def_pattern, line) and (
                line.startswith(" ") or line.startswith("\t")
            ):
                return "not_standalone"

    # If we've passed all checks, the callable is valid
    return None

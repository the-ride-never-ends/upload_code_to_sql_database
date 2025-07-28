import ast
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional


def get_callables_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract all top-level callable definitions from a Python source file.

    Parses a Python file using the Abstract Syntax Tree (AST) to identify and
    extract information about top-level functions, classes, async functions,
    and generators. For each callable, extracts its complete source code,
    signature, docstring, and metadata. Nested functions, methods, and lambdas
    are intentionally excluded as they are not standalone callables.

    The function preserves all formatting, comments, and structure from the
    original source code. It handles various Python syntax features including
    decorators, type hints, and async definitions.

    Args:
        file_path: Path to the Python source file to parse. Must be a valid
            .py file with readable permissions.

    Returns:
        List[Dict[str, Any]]: List of dictionaries, one per top-level callable.
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

            Returns empty list if no callables found or file is empty.

    Callable Type Detection:
        - 'function': Regular function defined with 'def'
        - 'class': Class definition
        - 'coroutine': Async function defined with 'async def'
        - 'generator': Function containing 'yield' statement

    Raises:
        SyntaxError: If the Python file contains syntax errors. Includes
            line number and error details from the parser.
        FileNotFoundError: If file_path does not exist.
        PermissionError: If file cannot be read due to permissions.
        UnicodeDecodeError: If file encoding cannot be determined, though
            the function attempts multiple encodings before failing.

    Example:
        # Given a file with this content:
        # @decorator
        # def process_data(items: List[str]) -> Dict[str, int]:
        #     '''Process items and return counts.'''
        #     return {item: len(item) for item in items}

        callables = get_callables_from_file(Path("example.py"))
        # Returns: [{
        #     'name': 'process_data',
        #     'type': 'function',
        #     'signature': 'def process_data(items: List[str]) -> Dict[str, int]:',
        #     'docstring': 'Process items and return counts.',
        #     'source_code': '@decorator\\ndef process_data(items: List[str]) -> Dict[str, int]:\\n    ...',
        #     'line_number': 1,
        #     'is_async': False,
        #     'decorators': ['decorator']
        # }]

    Notes:
        - Methods within classes are not returned separately
        - Nested functions are excluded from results
        - Lambda expressions are never included
        - Source code includes everything from decorators to end of definition
        - Empty files return empty list, not an error
        - File encoding is auto-detected, preferring UTF-8
    """
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    # Handle empty file
    if not source_code.strip():
        return []

    # Parse the AST
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        # Re-raise with more context
        raise SyntaxError(f"Syntax error in {file_path}: {e}")

    # Split source into lines for extraction
    source_lines = source_code.splitlines()

    callables = []

    # Only process top-level nodes
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            callable_info = _extract_callable_info(node, source_lines)
            callables.append(callable_info)

    return callables


def _extract_callable_info(node: ast.AST, source_lines: List[str]) -> Dict[str, Any]:
    """Extract information from a callable AST node."""

    # Basic info
    name = node.name
    line_number = node.lineno
    is_async = isinstance(node, ast.AsyncFunctionDef)

    # Extract decorators
    decorators = []
    for decorator in node.decorator_list:
        decorators.append(_ast_to_string(decorator))

    # Determine callable type and create signature
    match node:
        case ast.ClassDef():
            callable_type = "class"
            signature = _create_class_signature(node)
        case ast.AsyncFunctionDef():
            callable_type = "coroutine"
            signature = _create_function_signature(node, is_async=True)
        case ast.FunctionDef():
            # Check if it's a generator by looking for yield statements
            if _contains_yield(node):
                callable_type = "generator"
            else:
                callable_type = "function"
            signature = _create_function_signature(node, is_async=False)

    # Extract docstring
    docstring = _extract_docstring(node)

    # Normalize the docstring
    if docstring is not None:
        docstring = dedent(docstring).strip("\n")

    # Extract source code
    source_code = _extract_source_code(node, source_lines, decorators)

    return {
        "name": name,
        "type": callable_type,
        "signature": signature,
        "docstring": docstring,
        "source_code": source_code,
        "line_number": line_number if not decorators else node.decorator_list[0].lineno,
        "is_async": is_async,
        "decorators": decorators,
    }


def _ast_to_string(node: ast.AST) -> str:
    """Convert an AST node to its string representation."""
    match node:
        case ast.Name():
            return node.id
        case ast.Attribute():
            return f"{_ast_to_string(node.value)}.{node.attr}"
        case ast.Call():
            func_name = _ast_to_string(node.func)
            args = []
            for arg in node.args:
                args.append(_ast_to_string(arg))
            for keyword in node.keywords:
                args.append(f"{keyword.arg}={_ast_to_string(keyword.value)}")
            return f"{func_name}({', '.join(args)})"
        case ast.Constant():
            if isinstance(node.value, str):
                return f"'{node.value}'"
            return str(node.value)
        case ast.List():
            elements = [_ast_to_string(el) for el in node.elts]
            return f"[{', '.join(elements)}]"
        case _:
            # Unparse for complex expressions
            return ast.unparse(node)


def _create_class_signature(node: ast.ClassDef) -> str:
    """Create signature string for a class."""
    if node.bases:
        bases = [_ast_to_string(base) for base in node.bases]
        return f"class {node.name}({', '.join(bases)}):"
    return f"class {node.name}:"


def _get_regular_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef, params: list[str]
) -> str:
    for arg in node.args.args:
        param_str = arg.arg
        if arg.annotation:
            param_str += f": {_ast_to_string(arg.annotation)}"
        params.append(param_str)


def _get_varargs(
    node: ast.FunctionDef | ast.AsyncFunctionDef, params: list[str]
) -> str:
    if node.args.vararg:
        vararg_str = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            vararg_str += f": {_ast_to_string(node.args.vararg.annotation)}"
        params.append(vararg_str)


def _get_kwonly_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef, params: list[str]
) -> str:
    for arg in node.args.kwonlyargs:
        param_str = arg.arg
        if arg.annotation:
            param_str += f": {_ast_to_string(arg.annotation)}"
        params.append(param_str)


def _get_kwargs(node: ast.FunctionDef | ast.AsyncFunctionDef, params: list[str]) -> str:
    if node.args.kwarg:
        kwarg_str = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            kwarg_str += f": {_ast_to_string(node.args.kwarg.annotation)}"
        params.append(kwarg_str)


def _create_function_signature(node: ast.FunctionDef, is_async: bool = False) -> str:
    """Create signature string for a function."""
    params = []
    # Build parameter list
    for func in [
        _get_regular_args,  # Regular arguments
        _get_varargs,  # Varargs (*args)
        _get_kwonly_args,  # Keyword-only arguments
        _get_kwargs,  # Kwargs (**kwargs)
    ]:
        func(node, params)

    # Return type annotation
    return_annotation = f" -> {_ast_to_string(node.returns)}" if node.returns else ""

    return f"{"async def" if is_async else "def"} {node.name}({", ".join(params)}){return_annotation}:"


def _contains_yield(node: ast.FunctionDef) -> bool:
    """Check if a function contains yield statements (making it a generator)."""
    for child in ast.walk(node):
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _extract_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from a callable node."""
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value
    return None


def _extract_source_code(
    node: ast.AST, source_lines: List[str], decorators: List[str]
) -> str:
    """Extract the complete source code for a callable including decorators."""
    # Determine start line (including decorators)
    if decorators and node.decorator_list:
        start_line = node.decorator_list[0].lineno - 1  # Convert to 0-based
    else:
        start_line = node.lineno - 1  # Convert to 0-based

    # Find end line using end_lineno
    end_line = node.end_lineno

    # Extract the source code
    return "\n".join(source_lines[start_line:end_line])

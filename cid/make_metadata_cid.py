from code_entry.create_code_entry import CodeEntry, get_cid


def _get_first_line_of_docstring(docstring: str) -> str:
    """
    Extract the first line of a docstring, handling None or empty cases.

    Args:
        docstring: Full docstring string

    Returns:
        First line of the docstring or empty string if None
    """
    return docstring.split("\n", 1)[0].strip("\n").strip() if docstring else ""


def _get_signature_without_name(signature: str) -> str:
    """
    Extract the signature without the callable name.

    Args:
        signature: Full signature string including name

    Returns:
        Signature without the name part, preserving parameters and return type
        If signature is a plain class, returns an empty string.

    Examples:
        - "def calculate(x: int) -> int:" → "(x: int) -> int:"
        - "class SomeClass:" → ""
        - "class DataProcessor(BaseClass):" → "(BaseClass):"
        - "async def fetch_data(url: str) -> Dict[str, Any]:" → "(url: str) -> Dict[str, Any]:"
    """
    # Handle function signatures
    if signature.startswith("def "):
        # Find the opening parenthesis
        paren_index = signature.find("(")
        if paren_index != -1:
            return signature[paren_index:]

    # Handle class signatures
    elif signature.startswith("class "):
        # Find the opening parenthesis or colon
        paren_index = signature.find("(")
        colon_index = signature.find(":")

        if paren_index != -1 and (colon_index == -1 or paren_index < colon_index):
            # Has inheritance - return from opening paren
            return signature[paren_index:]
        elif colon_index != -1:
            # No inheritance - return empty string
            return ""

    # Handle async functions
    elif signature.startswith("async def "):
        paren_index = signature.find("(")
        if paren_index != -1:
            return signature[paren_index:]

    # If no pattern matches, return the signature as-is
    return signature


def make_metadata_cid(code_entry: CodeEntry) -> str:
    """
    Interface-only metadata CID

    Stable across implementation changes, updates when contract changes.

    Generates a CID based on the code entry's metadata content.

    CID generation is based on the following fields:
        - signature without name
        - docstring first line
        - code type enum (one of 'function', 'class', 'coroutine', 'generator')
        - file path (relative to project root)

    Use case: Track callable identity including its documented contract
    """
    metadata_content = (
        f"{_get_signature_without_name(code_entry.signature)}"
        f"{_get_first_line_of_docstring(code_entry.docstring)}"
        f"{code_entry.metadata['code_type']}"
        f"{code_entry.metadata['file_path']}"
    )
    return get_cid(metadata_content)

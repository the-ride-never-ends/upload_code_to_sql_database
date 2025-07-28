from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Dict, Any, List
import json


from multiformats import CID, multihash
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


try:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    raise RuntimeError(f"Failed to download NLTK resources: {e}")


def _get_all_nouns_and_proper_nouns_from_list_of_strings(strings: List[str]) -> List[str]:
    """
    Extract all nouns and proper nouns from a list of strings.
    
    Args:
        strings: List of strings to process
    Returns:
        List of unique nouns and proper nouns found in the strings
    """
    nouns = set()
    for string in strings:
        tokens = word_tokenize(string)
        pos_tags = nltk.pos_tag(tokens)
        
        for word, tag in pos_tags:
            if tag.startswith('NN') or tag.startswith('NNP'):  # Nouns and proper nouns
                nouns.add(word.lower())
    
    return list(nouns)




@dataclass
class CodeEntry:
    """
    Represent a complete code entry ready for database insertion.
    
    Encapsulates all data required to insert a code callable into both the codes
    and metadata database tables. Combines the core code content (source, signature,
    docstring) with its unique identifier (CID) and associated metadata. This
    dataclass serves as the transfer object between code extraction/processing
    and database storage.
    
    The CID (Content Identifier) is generated from the combination of signature,
    docstring, and source code, ensuring that identical code always produces the
    same identifier. This enables natural deduplication in the database.
    
    Attributes:
        cid (str): IPFS Content Identifier uniquely identifying this code content.
            Generated deterministically from signature + docstring + computer_code.
            Format: CIDv1 base32-encoded raw multihash string (e.g., "QmX7G8DPK...").
            Used as primary key in codes table and foreign key reference.
            Immutable once generated.
        
        signature (str): Complete function or class signature including name,
            parameters, type hints, and return type annotation. Preserves the
            exact syntax from source file.
            Examples:
            - "def calculate(x: int, y: int) -> int:"
            - "class DataProcessor(BaseClass):"
            - "async def fetch_data(url: str) -> Dict[str, Any]:"
        
        docstring (str): Raw docstring extracted from the callable. Preserves
            original formatting, indentation, and style (Google, NumPy, etc.).
            Empty string if callable has no docstring (though such callables
            should be filtered before CodeEntry creation).
            May contain multi-line documentation with examples.
        
        computer_code (str): Complete source code of the callable including:
            - All decorators (if any)
            - Full signature line
            - Docstring
            - Complete body implementation
            - Original formatting, comments, and whitespace
            Represents exactly what will be stored in codes.computer_code column.
        
        metadata (Dict[str, Any]): Additional information for the metadata table.
            Required keys:
            - code_cid (str): Copy of main cid for foreign key reference
            - code_name (str): Callable name extracted from signature
            - code_type (str): One of 'function', 'class', 'coroutine', 'generator'
                Must match database enum values
            - is_test (bool): Whether this is test code (name or path based)
            - file_path (str): Relative path from working directory to source file
            - tags (List[str]): Categorization tags from path components
            
            Optional keys may include:
            - other_metadata: Additional JSON-serializable data
            - line_number: Starting line in source file
            - decorators: List of decorator names
    
    Database Mapping:
        This dataclass maps to two tables:
        
        1. codes table:
           - cid → codes.cid (PRIMARY KEY)
           - cid → codes.version_cid (initially same)
           - signature → codes.signature
           - docstring → codes.docstring  
           - computer_code → codes.computer_code
        
        2. metadata table:
           - metadata['cid'] → metadata.cid (UNIQUE)
           - metadata['code_cid'] → metadata.code_cid (FOREIGN KEY)
           - metadata['code_name'] → metadata.code_name
           - metadata['code_type'] → metadata.code_type
           - metadata['is_test'] → metadata.is_test
           - metadata['file_path'] → metadata.file_path
           - metadata['tags'] → metadata.tags (as JSON)
    
    Example:
        # Creating a CodeEntry for a test function
        entry = CodeEntry(
            cid="QmX7G8DPKj6L4Fr7RZNnPZyHTE8vPJNfV2mWYgFchVTqyY",
            signature="def test_addition(a: int, b: int) -> None:",
            docstring="Test that addition works correctly.",
            computer_code='''def test_addition(a: int, b: int) -> None:
            \"\"\"Test that addition works correctly.\"\"\"
            assert a + b == b + a
            assert a + 0 == a''',
            metadata={
                'code_cid': "QmX7G8DPKj6L4Fr7RZNnPZyHTE8vPJNfV2mWYgFchVTqyY",
                'code_name': 'test_addition',
                'code_type': 'function',
                'is_test': True,
                'file_path': 'tests/test_math.py',
                'tags': ['tests', 'math']
            }
        )
    
    Validation Notes:
        - CID must be a valid IPFS content identifier string
        - code_type must match database enum constraints
        - All string fields should be properly escaped for SQL
        - tags must be JSON-serializable (list of strings)
        - file_path should use forward slashes even on Windows
        - No field should exceed database column size limits
    
    Immutability:
        While Python dataclasses are mutable by default, CodeEntry instances
        should be treated as immutable once created. The CID is based on content,
        so modifying fields after creation would invalidate the CID.
    
    Notes:
        - Used as parameter type for upload_code_entry()
        - Created by create_code_entry() after CID generation
        - All fields required; no optional attributes
        - Metadata dict must contain all required keys
        - Tags list may be empty but must be present
    """
    cid: str
    signature: str
    docstring: str
    computer_code: str
    metadata: Dict[str, Any]




class ipfs_multiformats_py:

    def __init__(self):

        self.multihash = multihash
        return None

    # Step 1: Hash the file content with SHA-256
    def get_file_sha256(self, file_path: str) -> bytes:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.digest()

    # Step 2: Wrap the hash in Multihash format
    def get_multihash_sha256(self, file_content_hash: bytes) -> multihash.Multihash:
        mh = self.multihash.wrap(file_content_hash, 'sha2-256')
        return mh

    # Step 3: Generate CID from Multihash (CIDv1)
    def _get_cid(self, file_path: str) -> str:
        file_content_hash = self.get_file_sha256(file_path)
        mh = self.get_multihash_sha256(file_content_hash)
        cid = CID('base32', 1, 'raw', mh)
        return str(cid)

    def get_cid(self, string: str) -> str:
        if not os.path.exists(string):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = Path(temp_dir) / "temp_code_entry.txt"
                temp_file_path.write_text(string, encoding='utf-8')
                return self._get_cid(temp_file_path)
        else:
            return self._get_cid(string)


def get_cid(content: str) -> str:
    """
    Generate an IPFS-style Content Identifier (CIDv1) from string content.
    
    Creates a CIDv0 format identifier by hashing the content with SHA-256
    and encoding with base58 in the IPFS multihash format.
    
    Args:
        content: String content to hash
        content = signature + docstring + source_code
        
    Returns:
        CID string in "CIDv1 base32-encoded raw multihash" format.
    """
    # Create an instance of the IPFS multiformats class
    ipfs = ipfs_multiformats_py()

    # Generate the CID from the content
    cid = ipfs.get_cid(content)

    return cid


def _is_test_code(name: str, file_path: Path) -> bool:
    """
    Determine if code is test-related based on name or file path.
    
    Args:
        name: Function or class name
        file_path: Path to the source file
        
    Returns:
        True if this appears to be test code
    """
    # Check name patterns
    if name.startswith('test_') or name.endswith('_test'):
        return True
    
    # Check if file is in test directory
    path_parts = file_path.parts
    for part in path_parts:
        if part in ('test', 'tests'):
            return True
    
    return False


def _extract_tags(file_path: Path, current_dir: Path) -> List[str]:
    """
    Extract meaningful tags from file path components.
    
    Args:
        file_path: Path to the source file
        current_dir: Current working directory
        
    Returns:
        List of tag strings derived from path
    """
    # Get relative path and its parts
    try:
        rel_path = file_path.relative_to(current_dir)
    except ValueError:
        # If file_path is not relative to current_dir, use as-is
        rel_path = file_path
    
    # Extract directory components (excluding home directory)
    home = Path.home()
    parts = rel_path.parts

    # Filter out home directory components, include filename
    tags = []
    for part in parts:
        if part != home.name:
            tags.append(part)

    # Filter out common/meaningless directories
    excluded_dirs = {
        'src', 'lib', 'utils', 'common', 'shared', 'core', 'base', 
        'main', 'app', 'code', 'source', 'python', 'py', 'shared',
    }
    
    tags = []
    for part in parts:
        if part not in excluded_dirs and not part.startswith('.'):
            tags.append(part.strip('_').lower())
    
    # Remove common stop words.
    common_stop_words = {
        'the', 'and', 'or', 'a', 'an', 'is', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'as', 'this', 'that', 'it', 'be',
        'are', 'was', 'were', 'been', 'have', 'has', 'had', 'do',
        'does', 'did', 'will', 'would', 'could', 'should', 'may',
        'might', 'can', 'must', 'shall', 'from', 'up', 'out', 'if',
        'then', 'than', 'when', 'where', 'why', 'how', 'all', 'any',
        'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'also',
        'but', 'very', 'just', 'now', 'here', 'there', 'between',
        'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'over', 'under', 'again', 'further', 'once', 'two'
    }
    for tag in tags[:]:
        if tag.lower() in common_stop_words:
            tags.remove(tag)
            
    tags = _get_all_nouns_and_proper_nouns_from_list_of_strings(tags)
    
    # Deduplicate tags, then sort alphabetically
    list(set(tags))
    tags.sort()

    # Deduplicate tags
    return tags


from cid.make_metadata_cid import make_metadata_cid






def create_code_entry(callable_info: Dict[str, Any], 
                     file_path: Path) -> CodeEntry:
    """
    Create a CodeEntry object with generated CID and extracted metadata.
    
    Transforms callable information into a structured CodeEntry ready for
    database insertion. Generates a unique Content Identifier (CID) by hashing
    the combination of signature, docstring, and source code. Extracts and
    formats metadata including test detection, path information, and code
    categorization tags.
    
    The CID generation ensures that identical code blocks will always produce
    the same identifier, enabling natural deduplication in the database. All
    string data is properly prepared for safe database insertion.
    
    Args:
        callable_info: Dictionary containing parsed callable data from
            get_callables_from_file() with keys:
            - name: Callable identifier
            - type: Type string (function, class, coroutine, generator)
            - signature: Full signature with type hints
            - docstring: Documentation string (may be None)
            - source_code: Complete source including decorators
            - Additional parsing metadata
        
        file_path: Path object indicating the source file location. Used for:
            - Generating relative path for storage
            - Extracting module hierarchy for tags
            - Test detection based on directory structure
    
    Returns:
        CodeEntry: Dataclass instance containing:
            - cid (str): IPFS Content Identifier generated from content
                Format: "bafk..." (CIDv1 base32-encoded multihash)
                Deterministic: same input always generates same CID
            - signature (str): Function/class signature ready for database
            - docstring (str): Original docstring or empty string if None
            - computer_code (str): Complete source code with formatting preserved
            - metadata (Dict[str, Any]): Additional information:
                - cid: Made from name + type + file_path + tags
                - code_cid: Matches the main CID for foreign reference
                - code_name: Callable name from callable_info
                - code_type: Database enum value (mapped from type)
                - is_test: Boolean indicating if this is test code
                - file_path: Relative path from current working directory
                - tags: JSON-serializable list of categorization tags
    
    CID Generation Process:
        1. Concatenate: signature + docstring + source_code
        2. Handle None docstring as empty string in concatenation
        3. Pass concatenated string to IPFS hash function
        4. Resulting CID is unique identifier for this exact code
    
    Test Detection:
        Code is marked as test (is_test=True) if:
        - Function/class name starts with "test_"
        - Function/class name ends with "_test"
        - File is in a "test/" or "tests/" directory
        - File path contains "/test/" or "/tests/" anywhere
    
    Tag Extraction:
        Tags are derived from file path components:
        - Each directory in path becomes a potential tag
        - Common directories excluded (src, lib, utils)
        - Example: "project/analysis/stats.py" → ["analysis", "stats"]
    
    Example:
        callable_info = {
            'name': 'test_calculator',
            'type': 'function',
            'signature': 'def test_calculator():',
            'docstring': 'Test the calculator function.',
            'source_code': 'def test_calculator():\n    '''Test the calculator function.'''\n    assert add(2, 2) == 4'
        }
        file_path = Path('/home/user/project/tests/test_math.py')
        
        entry = create_code_entry(callable_info, file_path)
        # Results in:
        # entry.cid = "bafkreig..." (deterministic CIDv1 hash)
        # entry.metadata['is_test'] = True (name starts with test_)
        # entry.metadata['file_path'] = "tests/test_math.py" (relative)
        # entry.metadata['tags'] = ["tests", "math"]
    
    Notes:
        - CID generation is deterministic and consistent
        - Paths are always stored as relative to avoid absolute path issues
        - All strings are properly escaped for database safety
        - None docstrings are converted to empty strings
        - Original formatting in source code is preserved exactly
        - Database enum values must match the schema constraints
    """
    # Extract basic information
    name: str = callable_info['name']
    signature: str = callable_info['signature']
    docstring: str = callable_info.get('docstring') or ''  # Handle None docstring
    source_code: str = callable_info['source_code']
    code_type: str = callable_info['type']
    
    # Generate CID from concatenated content
    content_for_cid = signature + docstring + source_code
    code_cid: str = get_cid(content_for_cid)
    
    # Get current working directory for relative path calculation
    current_dir = Path.cwd()
    
    # Calculate relative file path
    try:
        relative_path = file_path.relative_to(current_dir)
    except ValueError:
        # If file_path is not under current_dir, use as-is but remove leading slash
        relative_path = Path(*file_path.parts[1:]) if file_path.is_absolute() else file_path

    # Convert to string with forward slashes
    file_path_str = str(relative_path).replace('\\', '/')

    # Detect if this is test code
    is_test = _is_test_code(name, file_path)

    # Extract tags from path
    tags = _extract_tags(file_path, current_dir)

    # Build metadata dictionary
    metadata = {
        'code_cid': code_cid,
        'code_name': name,
        'code_type': code_type,
        'is_test': is_test,
        'file_path': file_path_str,
        'tags': tags
    }
    
    # Create and return CodeEntry
    code_entry = CodeEntry(
        cid=code_cid,
        signature=signature,
        docstring=docstring,
        computer_code=source_code,
        metadata=metadata
    )

    code_entry.metadata['cid'] = make_metadata_cid(code_entry)
    return code_entry
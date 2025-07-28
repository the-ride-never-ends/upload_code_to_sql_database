import pytest
import os
from pathlib import Path

# Import the function to test
from find_python_files import find_python_files


class TestFindPythonFiles:
    """
    Test find_python_files function for finding Python source files.

    Test Methods:
    - test_find_python_files_in_flat_directory: Non-recursive file discovery
    - test_find_python_files_recursive_search: Recursive directory scanning
    - test_find_python_files_excludes_default_directories: Default exclusion patterns
    - test_find_python_files_with_custom_exclude_patterns: Custom exclusion patterns
    - test_find_python_files_returns_empty_list_when_no_files: No Python files found
    - test_find_python_files_handles_only_py_extension: File extension filtering
    - test_find_python_files_returns_absolute_paths: Path conversion to absolute
    - test_find_python_files_sorted_output: Alphabetical sorting of results
    - test_find_python_files_handles_permission_errors: Permission error handling
    - test_find_python_files_handles_symlinks: Symbolic link processing
    - test_find_python_files_with_nonexistent_directory: Non-existent directory handling
    - testfind_python_files_exclude_pattern_precedence: Pattern precedence testing
    """

    def test_find_python_files_in_flat_directory(self, tmp_path):
        """
        GIVEN a directory containing Python files at the root level
        AND recursive=False
        WHEN find_python_files is called
        THEN expect:
            - Returns list of Path objects for all .py files in directory
            - Does not include files from subdirectories
            - All paths are absolute paths
            - List is sorted alphabetically
        """
        # Setup: Create test directory structure
        (tmp_path / "main.py").write_text("# main module")
        (tmp_path / "utils.py").write_text("# utils module")
        (tmp_path / "config.py").write_text("# config module")

        # Create subdirectory with Python file (should be excluded in non-recursive)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("# nested module")

        # Create non-Python files (should be excluded)
        (tmp_path / "readme.txt").write_text("documentation")
        (tmp_path / "data.json").write_text("{}")

        # Execute
        result = find_python_files(tmp_path, recursive=False, exclude_patterns=[])

        # Verify
        assert isinstance(result, list)
        assert len(result) == 3

        # Check all are Path objects and absolute
        for path in result:
            assert isinstance(path, Path)
            assert path.is_absolute()
            assert path.suffix == ".py"

        # Check specific files are included
        result_names = [p.name for p in result]
        assert "main.py" in result_names
        assert "utils.py" in result_names
        assert "config.py" in result_names

        # Check subdirectory file is NOT included
        assert "nested.py" not in result_names

        # Check alphabetical sorting
        expected_order = ["config.py", "main.py", "utils.py"]
        actual_order = [p.name for p in result]
        assert actual_order == expected_order

    def test_find_python_files_recursive_search(self, tmp_path):
        """
        GIVEN a directory with nested subdirectories containing Python files
        AND recursive=True
        WHEN find_python_files is called
        THEN expect:
            - Returns list of Path objects for all .py files in directory tree
            - Includes files from all subdirectories
            - All paths are absolute paths
            - List is sorted alphabetically
        """
        # Setup: Create nested directory structure
        (tmp_path / "root.py").write_text("# root module")

        # Level 1 subdirectories
        level1_a = tmp_path / "dir_a"
        level1_a.mkdir()
        (level1_a / "module_a.py").write_text("# module a")

        level1_b = tmp_path / "dir_b"
        level1_b.mkdir()
        (level1_b / "module_b.py").write_text("# module b")

        # Level 2 subdirectory
        level2 = level1_a / "nested"
        level2.mkdir()
        (level2 / "deep.py").write_text("# deep module")

        # Execute
        result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Verify
        assert isinstance(result, list)
        assert len(result) == 4

        # Check all are absolute paths
        for path in result:
            assert path.is_absolute()
            assert path.suffix == ".py"

        # Check all expected files are included
        result_names = [p.name for p in result]
        assert "root.py" in result_names
        assert "module_a.py" in result_names
        assert "module_b.py" in result_names
        assert "deep.py" in result_names

        # Verify alphabetical sorting by full path
        result_paths = [str(p) for p in result]
        assert result_paths == sorted(result_paths)

    def test_find_python_files_excludes_default_directories(self, tmp_path):
        """
        GIVEN a directory containing Python files in excluded directories
        AND exclude_patterns is empty list (using defaults)
        WHEN find_python_files is called
        THEN expect:
            - Files in __pycache__ are excluded
            - Files in .git are excluded
            - Files in venv and .venv are excluded
            - Files in node_modules are excluded
            - Files in .pytest_cache are excluded
            - Files in build and dist are excluded
            - Files in non-excluded directories are included
        """
        # Setup: Create valid Python file
        (tmp_path / "valid.py").write_text("# valid module")

        # Create default excluded directories with Python files
        excluded_dirs = [
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "node_modules",
            ".pytest_cache",
            "build",
            "dist",
        ]

        for dir_name in excluded_dirs:
            excluded_dir = tmp_path / dir_name
            excluded_dir.mkdir()
            (excluded_dir / f"{dir_name}_file.py").write_text(f"# file in {dir_name}")

        # Create non-excluded directory with Python file
        good_dir = tmp_path / "src"
        good_dir.mkdir()
        (good_dir / "good.py").write_text("# good module")

        # Execute
        result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Verify - should only include files from non-excluded directories
        assert len(result) == 2
        result_names = [p.name for p in result]
        assert "valid.py" in result_names
        assert "good.py" in result_names

        # Verify no excluded directory files are present
        for excluded_dir in excluded_dirs:
            assert not any(excluded_dir in str(p) for p in result)
            assert f"{excluded_dir}_file.py" not in result_names

    def test_find_python_files_with_custom_exclude_patterns(self, tmp_path):
        """
        GIVEN custom exclude patterns like ['test_*', '*_backup', 'old/']
        WHEN find_python_files is called with these patterns
        THEN expect:
            - Files matching test_* pattern are excluded
            - Files matching *_backup pattern are excluded
            - All files in 'old/' directory are excluded
            - Default exclusions are still applied
            - Non-matching files are included
        """
        # Setup: Create various files
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "test_main.py").write_text("# test main")  # Should be excluded
        (tmp_path / "config_backup.py").write_text("# backup")  # Should be excluded
        (tmp_path / "exclude_me.py").write_text("# backup")  # Should be excluded
        (tmp_path / "utils.py").write_text("# utils")  # Should be included

        # Create 'old' directory with files (should be excluded)
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        (old_dir / "legacy.py").write_text("# legacy")

        # Create __pycache__ (default exclusion, should still be excluded)
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("# cached")

        # Execute with custom exclusions
        custom_patterns = [
            "test_*",  # Any file starting with 'test_'
            "*_backup*",  # Any file with '_backup' in name
            "*_me.py",  # Any file ending with '_me.py'
            "old/",  # Any file in 'old/' directory
        ]
        result = find_python_files(
            tmp_path, recursive=True, exclude_patterns=custom_patterns
        )

        # Verify
        result_names = [p.name for p in result]

        # Should include
        assert "main.py" in result_names
        assert "utils.py" in result_names

        # Should exclude (custom patterns)
        assert "test_main.py" not in result_names
        assert "config_backup.py" not in result_names
        assert "legacy.py" not in result_names
        assert "exclude_me.py" not in result_names

        # Should exclude (default patterns still active)
        assert "cached.py" not in result_names

        # Verify exclusion by checking paths don't contain patterns
        result_paths = [str(p) for p in result]
        print(f"Result paths: {result_paths}")
        # NOTE Specifically test fot 'test_main' because the temp directory
        # is based off the test function name, which contains "test_"
        assert not any(["test_main" in path for path in result_paths])
        assert not any(["_backup" in path for path in result_paths])
        assert not any(["/old/" in path for path in result_paths])
        assert not any(["__pycache__" in path for path in result_paths])

    def test_find_python_files_returns_empty_list_when_no_files(self, tmp_path):
        """
        GIVEN a directory with no Python files
        WHEN find_python_files is called
        THEN expect:
            - Returns empty list []
            - Does not return None
            - Does not raise exception
        """
        # Setup: Create directory with only non-Python files
        (tmp_path / "readme.txt").write_text("documentation")
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "data.csv").write_text("col1,col2")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "image.png").write_text("fake image")

        # Execute
        result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Verify
        assert result == []
        assert isinstance(result, list)
        assert result is not None

    def test_find_python_files_handles_only_py_extension(self, tmp_path):
        """
        GIVEN a directory with various file types (.txt, .pyc, .pyx, .py)
        WHEN find_python_files is called
        THEN expect:
            - Only .py files are included
            - .pyc files are excluded
            - .pyx files are excluded
            - .txt and other extensions are excluded
        """
        # Setup: Create files with various extensions
        (tmp_path / "script.py").write_text("# Python script")
        (tmp_path / "compiled.pyc").write_text("compiled bytecode")
        (tmp_path / "cython_ext.pyx").write_text("# Cython extension")
        (tmp_path / "interface.pyi").write_text("# Type stubs")
        (tmp_path / "readme.txt").write_text("documentation")
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "no_extension").write_text("no extension")

        # Execute
        result = find_python_files(tmp_path, recursive=False, exclude_patterns=[])

        # Verify
        assert len(result) == 1
        assert result[0].name == "script.py"
        assert result[0].suffix == ".py"

        # Double-check excluded extensions
        result_names = [p.name for p in result]
        assert "compiled.pyc" not in result_names
        assert "cython_ext.pyx" not in result_names
        assert "interface.pyi" not in result_names
        assert "readme.txt" not in result_names
        assert "config.json" not in result_names
        assert "no_extension" not in result_names

    def test_find_python_files_returns_absolute_paths(self, tmp_path):
        """
        GIVEN relative or absolute directory path as input
        WHEN find_python_files is called
        THEN expect:
            - All returned Path objects are absolute paths
            - Paths are resolved (symlinks followed)
            - No relative paths in output
        """
        # Setup: Create test files
        (tmp_path / "module.py").write_text("# module")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("# nested")

        # Test with absolute path
        result_abs = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Test with relative path (change to parent directory first)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path.parent)
            relative_path = Path(tmp_path.name)
            result_rel = find_python_files(
                relative_path, recursive=True, exclude_patterns=[]
            )
        finally:
            os.chdir(original_cwd)

        # Verify both return absolute paths
        for result in [result_abs, result_rel]:
            assert len(result) == 2
            for path in result:
                assert path.is_absolute()
                assert not str(path).startswith(".")
                assert not str(path).startswith("..")

        # Results should be identical regardless of input path type
        assert set(result_abs) == set(result_rel)

    def test_find_python_files_sorted_output(self, tmp_path):
        """
        GIVEN multiple Python files with various names
        WHEN find_python_files is called
        THEN expect:
            - Returned list is sorted alphabetically by full path
            - Sort is consistent across different filesystems
            - Subdirectory files are sorted within parent directory order
        """
        # Setup: Create files in non-alphabetical creation order
        files_to_create = [
            "zebra.py",
            "alpha.py",
            "beta.py",
            "subdir/zulu.py",
            "subdir/alpha_sub.py",
            "another/gamma.py",
        ]

        for file_path in files_to_create:
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"# {file_path}")

        # Execute
        result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Verify sorting
        result_paths = [str(p) for p in result]
        expected_sorted = sorted(result_paths)
        assert result_paths == expected_sorted

        # Verify specific ordering expectations
        assert len(result) == 6

        # Check that paths are sorted by full path, not just filename
        path_strings = [str(p) for p in result]
        for i in range(len(path_strings) - 1):
            assert path_strings[i] <= path_strings[i + 1]

    def test_find_python_files_handles_permission_errors(self, tmp_path):
        """
        GIVEN a directory with subdirectories that have no read permissions
        WHEN find_python_files is called
        THEN expect:
            - Accessible files are still discovered
            - Permission errors are handled gracefully
            - Function continues scanning other directories
            - Returns list of accessible files only
        """
        # Setup: Create accessible files
        (tmp_path / "accessible.py").write_text("# accessible")

        accessible_dir = tmp_path / "good_dir"
        accessible_dir.mkdir()
        (accessible_dir / "good.py").write_text("# good file")

        # Create restricted directory
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        (restricted_dir / "hidden.py").write_text("# hidden file")

        # Remove read permissions from restricted directory
        restricted_dir.chmod(0o000)

        try:
            # Execute
            result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

            # Verify accessible files are found
            result_names = [p.name for p in result]
            assert "accessible.py" in result_names
            assert "good.py" in result_names

            # Verify restricted file is not found (due to permission error)
            assert "hidden.py" not in result_names

            # Should not raise exception
            assert isinstance(result, list)

        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_find_python_files_handles_symlinks(self, tmp_path):
        """
        GIVEN a directory containing symbolic links to Python files or directories
        WHEN find_python_files is called
        THEN expect:
            - Symlinked Python files are included if they point to .py files
            - Symlinked directories are traversed if recursive=True
            - Broken symlinks are skipped without error
            - Circular symlinks don't cause infinite loops
        """
        # Setup: Create real files and directories
        real_file = Path(tmp_path) / "real_module.py"
        real_file.write_text("# real module")

        real_dir = Path(tmp_path) / "real_dir"
        real_dir.mkdir()
        (real_dir / "nested.py").write_text("# nested in real dir")

        # Create symlinks
        symlink_to_file = tmp_path / "link_to_file.py"
        symlink_to_file.symlink_to(real_file)  # This points to 'real_module.py'

        symlink_to_dir = tmp_path / "link_to_dir"
        symlink_to_dir.symlink_to(real_dir)  # This points to 'real_dir'

        # Create broken symlink
        broken_link = tmp_path / "broken_link.py"
        broken_link.symlink_to(tmp_path / "nonexistent.py")

        # Create circular symlink
        circular_dir = tmp_path / "circular"
        circular_dir.mkdir()
        circular_link = circular_dir / "self_link"
        circular_link.symlink_to(circular_dir)

        # Execute
        result = find_python_files(tmp_path, recursive=True, exclude_patterns=[])

        # Verify
        result_names = [p.name for p in result]

        # Real files should be found
        assert "real_module.py" in result_names
        assert "nested.py" in result_names

        # File in symlinked directory should be found
        symlinked_nested_found = any("nested.py" in str(p) for p in result)
        assert symlinked_nested_found

        # Broken symlink should not cause errors
        assert "broken_link.py" not in result_names

        # Should complete without infinite loop (circular symlink)
        assert isinstance(result, list)

    def test_find_python_files_with_nonexistent_directory(self, tmp_path):
        """
        GIVEN a path to a directory that does not exist
        WHEN find_python_files is called
        THEN expect:
            - Returns empty list []
            - Behavior is consistent and documented
        """
        # Setup: Create path to nonexistent directory
        nonexistent_path = tmp_path / "does_not_exist"

        # Verify directory doesn't exist
        assert not nonexistent_path.exists()

        # Execute and verify empty list is returned
        result = find_python_files(
            nonexistent_path, recursive=True, exclude_patterns=[]
        )

        # Verify
        assert result == []
        assert isinstance(result, list)

    # NOTE This test name is intentionally mispelled, or else it messes with the directory checks
    def testfind_python_files_exclude_pattern_precedence(self, tmp_path):
        """
        GIVEN both default and custom exclude patterns
        AND some patterns might conflict or overlap
        WHEN find_python_files is called
        THEN expect:
            - Both default and custom patterns are applied
            - No pattern overrides another
            - File is excluded if it matches ANY exclude pattern
        """
        # Setup: Create files that match various patterns
        (tmp_path / "normal.py").write_text("# normal file")

        # File that matches both default and custom exclusion
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test_cached.py").write_text("# matches both default and custom")

        # File that matches only custom exclusion
        (tmp_path / "test_only.py").write_text("# matches only custom")

        # File that matches only default exclusion
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        (venv_dir / "regular_name.py").write_text("# matches only default")

        # Custom pattern that overlaps with default behavior
        custom_patterns = ["test_*", "__pycache__"]  # __pycache__ is also default

        # Execute
        result = find_python_files(
            tmp_path, recursive=True, exclude_patterns=custom_patterns
        )

        # Verify
        result_names = [p.name for p in result]

        # Only normal file should be included
        assert len(result) == 1
        assert "normal.py" in result_names

        # All pattern-matching files should be excluded
        assert "test_cached.py" not in result_names  # matches both
        assert "test_only.py" not in result_names  # matches custom
        assert "regular_name.py" not in result_names  # matches default

        # Verify exclusion by path checking
        result_paths = [str(p) for p in result]
        print(f"Result paths: {result_paths}")
        assert not any("__pycache__" in path for path in result_paths)
        assert not any("test_" in path for path in result_paths)
        assert not any("venv" in path for path in result_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

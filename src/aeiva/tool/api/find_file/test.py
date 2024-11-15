# tools/find_file/test.py

import pytest
from unittest.mock import patch
from .api import find_file

@pytest.mark.asyncio
async def test_find_file_success():
    pattern = "*.py"
    depth = 2
    case_sensitive = False
    include = ["/test/include"]
    exclude = ["/test/exclude"]
    expected_matched_files = ["/test/include/file1.py", "/test/include/subdir/file2.py"]

    with patch('os.getcwd', return_value="/test"), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.walk') as mock_walk, \
         patch('fnmatch.fnmatch') as mock_fnmatch:
        
        mock_walk.return_value = [
            ("/test/include", ["subdir"], ["file1.py"]),
            ("/test/include/subdir", [], ["file2.py"]),
            ("/test/exclude", [], ["file3.py"])
        ]
        
        # Mock fnmatch to handle case sensitivity
        def fnmatch_side_effect(filename, pattern):
            if not case_sensitive:
                return fnmatch.fnmatchcase(filename.lower(), pattern.lower())
            return fnmatch.fnmatchcase(filename, pattern)
        
        mock_fnmatch.side_effect = fnmatch_side_effect
        
        result = find_file(pattern, depth, case_sensitive, include, exclude)
        assert result['output'] == expected_matched_files
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_find_file_no_matches():
    pattern = "*.md"
    depth = 1
    case_sensitive = True
    include = ["/test/include"]
    exclude = ["/test/exclude"]
    expected_error = "No files found matching the pattern."

    with patch('os.getcwd', return_value="/test"), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.walk') as mock_walk, \
         patch('fnmatch.fnmatch') as mock_fnmatch:
        
        mock_walk.return_value = [
            ("/test/include", [], ["file1.py", "file2.py"]),
            ("/test/exclude", [], ["file3.py"])
        ]
        
        mock_fnmatch.return_value = False
        
        result = find_file(pattern, depth, case_sensitive, include, exclude)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "NO_MATCHES"

@pytest.mark.asyncio
async def test_find_file_too_many_results():
    pattern = "*.txt"
    depth = None
    case_sensitive = False
    include = ["/test/include"]
    exclude = ["/test/exclude"]
    # Generate 250 mock files
    expected_matched_files = [f"/test/include/file{i}.txt" for i in range(1, 201)]
    total_files = 250

    with patch('os.getcwd', return_value="/test"), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('os.walk') as mock_walk, \
         patch('fnmatch.fnmatch') as mock_fnmatch:
        
        mock_walk.return_value = [
            ("/test/include", [], [f"file{i}.txt" for i in range(1, total_files + 1)])
        ]
        
        mock_fnmatch.return_value = True
        
        result = find_file(pattern, depth, case_sensitive, include, exclude)
        assert result['output'] == expected_matched_files
        assert result['error'] == f"Too many results found ({total_files}). Showing first 200 results."
        assert result['error_code'] == "TOO_MANY_RESULTS"

@pytest.mark.asyncio
async def test_find_file_missing_pattern():
    pattern = ""
    depth = 1
    case_sensitive = True
    include = ["/test/include"]
    exclude = ["/test/exclude"]
    expected_error = "Pattern must be provided."

    result = find_file(pattern, depth, case_sensitive, include, exclude)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_PATTERN"

@pytest.mark.asyncio
async def test_find_file_exception():
    pattern = "*.py"
    depth = 1
    case_sensitive = False
    include = ["/test/include"]
    exclude = ["/test/exclude"]
    expected_error_code = "FIND_FILE_FAILED"
    expected_error_message = "Error finding files: Sample exception."

    with patch('os.walk', side_effect=Exception("Sample exception.")):
        result = find_file(pattern, depth, case_sensitive, include, exclude)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code
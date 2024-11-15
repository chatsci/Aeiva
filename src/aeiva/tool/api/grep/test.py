# test.py

import pytest
from unittest.mock import patch, mock_open
from .api import grep
import os

@pytest.mark.asyncio
async def test_grep_success():
    word = "search_term"
    pattern = "*.txt"
    recursive = True
    case_insensitive = True
    expected_output = {
        "/path/to/file1.txt": [(3, "This line contains Search_Term."), (10, "Another search_term here.")]
    }

    mock_file_content = "Line 1\nLine 2 search_term\nLine 3 This line contains Search_Term.\nLine 4\nLine 10 Another search_term here.\n"

    m = mock_open(read_data=mock_file_content)
    with patch('os.walk') as mock_walk, \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('builtins.open', m):
        
        mock_walk.return_value = [
            ("/path/to", [], ["file1.txt"])
        ]

        result = grep(word, pattern, recursive, case_insensitive)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_grep_no_matches():
    word = "nonexistent"
    pattern = "*.md"
    recursive = False
    case_insensitive = False
    expected_output = {}
    expected_error = "No matches found."
    expected_error_code = "NO_MATCHES"

    mock_file_content = "Line 1\nLine 2\nLine 3\n"

    m = mock_open(read_data=mock_file_content)
    with patch('os.walk') as mock_walk, \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('builtins.open', m):
        
        mock_walk.return_value = [
            ("/path/to", [], ["file1.md"])
        ]

        result = grep(word, pattern, recursive, case_insensitive)
        assert result['output'] == expected_output
        assert result['error'] == expected_error
        assert result['error_code'] == "NO_MATCHES"

@pytest.mark.asyncio
async def test_grep_missing_word():
    word = ""
    pattern = "*.py"
    recursive = True
    case_insensitive = True
    expected_error = "Search word must be provided."
    expected_error_code = "MISSING_WORD"

    result = grep(word, pattern, recursive, case_insensitive)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_WORD"

@pytest.mark.asyncio
async def test_grep_too_many_matches():
    word = "test"
    pattern = "*.txt"
    recursive = True
    case_insensitive = False

    # Generate 150 mock files with matches
    mock_walk_return = []
    mock_files = []
    mock_contents = []
    for i in range(150):
        file_path = f"/path/to/file{i}.txt"
        mock_files.append(f"file{i}.txt")
        mock_contents.append(f"Line with test in file{i}\n")

    mock_walk_return.append(("/path/to", [], mock_files))

    m = mock_open()
    with patch('os.walk', return_value=mock_walk_return), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', side_effect=lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', side_effect=lambda x: x), \
         patch('builtins.open', m):
        
        # Mock readlines for each file
        handle = m()
        handle.__iter__.return_value = iter(mock_contents)

        result = grep(word, pattern, recursive, case_insensitive)
        assert len(result['output']) == 100
        assert result['error'] == "Warning: More than 100 files matched. Showing first 100 results."
        assert result['error_code'] == "TOO_MANY_MATCHES"

@pytest.mark.asyncio
async def test_grep_permission_denied():
    word = "test"
    pattern = "*.py"
    recursive = True
    case_insensitive = True

    with patch('os.walk', side_effect=PermissionError("Permission denied")), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', lambda x: x):
        
        result = grep(word, pattern, recursive, case_insensitive)
        assert result['output'] is None
        assert "Permission denied" in result['error']
        assert result['error_code'] == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_grep_io_error():
    word = "test"
    pattern = "*.py"
    recursive = True
    case_insensitive = True

    with patch('os.walk', side_effect=IOError("I/O error occurred")), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', lambda x: x):
        
        result = grep(word, pattern, recursive, case_insensitive)
        assert result['output'] is None
        assert "Error reading files: I/O error occurred" in result['error']
        assert result['error_code'] == "IO_ERROR"

@pytest.mark.asyncio
async def test_grep_unexpected_error():
    word = "test"
    pattern = "*.py"
    recursive = True
    case_insensitive = True

    with patch('os.walk', side_effect=Exception("Unexpected exception")), \
         patch('os.path.isfile', return_value=True), \
         patch('os.path.abspath', lambda x: os.path.abspath(x)), \
         patch('os.path.expanduser', lambda x: x):
        
        result = grep(word, pattern, recursive, case_insensitive)
        assert result['output'] is None
        assert "Unexpected error: Unexpected exception" in result['error']
        assert result['error_code'] == "UNEXPECTED_ERROR"
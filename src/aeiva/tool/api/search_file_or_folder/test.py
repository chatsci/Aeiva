# tools/search_file_or_folder/test.py

import pytest
from unittest.mock import patch
from .api import search_file_or_folder

@pytest.mark.asyncio
async def test_search_file_or_folder_success_both():
    name = "test_file"
    search_path = "/test/path"
    search_type = "both"
    case_sensitive = True
    partial_match = False
    expected_matched_paths = ["/test/path/test_file.txt", "/test/path/test_file_folder"]

    with patch('os.walk') as mock_walk, \
         patch('unicodedata.normalize', side_effect=lambda form, s: s.casefold() if not case_sensitive else s):
        
        mock_walk.return_value = [
            ("/test/path", ["test_file_folder"], ["test_file.txt"])
        ]
        
        result = search_file_or_folder(name, search_path, search_type, case_sensitive, partial_match)
        assert result['output']['matched_paths'] == expected_matched_paths
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_search_file_or_folder_invalid_search_type():
    name = "test_file"
    search_path = "/test/path"
    search_type = "invalid_type"
    case_sensitive = True
    partial_match = False
    expected_error = f"Invalid search_type: {search_type}. Choose from 'file', 'folder', or 'both'."
    
    result = search_file_or_folder(name, search_path, search_type, case_sensitive, partial_match)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "INVALID_SEARCH_TYPE"

@pytest.mark.asyncio
async def test_search_file_or_folder_case_insensitive_partial_match():
    name = "test"
    search_path = "/test/path"
    search_type = "file"
    case_sensitive = False
    partial_match = True
    expected_matched_paths = ["/test/path/TestFile.txt"]

    with patch('os.walk') as mock_walk, \
         patch('unicodedata.normalize', side_effect=lambda form, s: s.casefold()):
        
        mock_walk.return_value = [
            ("/test/path", [], ["TestFile.txt", "AnotherFile.doc"])
        ]
        
        result = search_file_or_folder(name, search_path, search_type, case_sensitive, partial_match)
        assert result['output']['matched_paths'] == expected_matched_paths
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_search_file_or_folder_no_matches():
    name = "nonexistent"
    search_path = "/test/path"
    search_type = "file"
    case_sensitive = True
    partial_match = False
    expected_matched_paths = []

    with patch('os.walk') as mock_walk, \
         patch('unicodedata.normalize', side_effect=lambda form, s: s):
        
        mock_walk.return_value = [
            ("/test/path", [], ["file1.txt", "file2.doc"])
        ]
        
        result = search_file_or_folder(name, search_path, search_type, case_sensitive, partial_match)
        assert result['output']['matched_paths'] == expected_matched_paths
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_search_file_or_folder_exception():
    name = "test_file"
    search_path = "/test/path"
    search_type = "file"
    case_sensitive = True
    partial_match = False

    with patch('os.walk', side_effect=Exception("Walk error")), \
         patch('unicodedata.normalize'):
        
        result = search_file_or_folder(name, search_path, search_type, case_sensitive, partial_match)
        assert result['output'] is None
        assert result['error'] == "Error searching for file or folder: Walk error"
        assert result['error_code'] == "SEARCH_FAILED"
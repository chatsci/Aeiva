# tools/list_files/test.py

import pytest
from unittest.mock import patch
from .api import list_files

@pytest.mark.asyncio
async def test_list_files_success_default_directory():
    expected_items = ['file1.txt', 'file2.jpg', 'folder1']
    
    with patch('os.path.isdir', return_value=True), \
         patch('os.listdir', return_value=expected_items), \
         patch('os.path.expanduser', return_value='/home/testuser'):
        
        result = list_files()
        assert result['output'] == {"items": expected_items}
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_list_files_success_specified_directory():
    directory = "/tmp"
    expected_items = ['temp1.tmp', 'temp2.log']
    
    with patch('os.path.isdir', return_value=True), \
         patch('os.listdir', return_value=expected_items), \
         patch('os.path.expanduser', return_value=directory):
        
        result = list_files(directory)
        assert result['output'] == {"items": expected_items}
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_list_files_directory_not_found():
    directory = "/non/existent/path"
    
    with patch('os.path.isdir', return_value=False), \
         patch('os.path.expanduser', return_value=directory):
        
        result = list_files(directory)
        assert result['output'] is None
        assert result['error'] == f"Directory not found: {directory}"
        assert result['error_code'] == "DIRECTORY_NOT_FOUND"

@pytest.mark.asyncio
async def test_list_files_exception():
    directory = "/home/testuser"
    
    with patch('os.path.isdir', side_effect=Exception("Permission denied")), \
         patch('os.path.expanduser', return_value=directory):
        
        result = list_files(directory)
        assert result['output'] is None
        assert result['error'] == "Error listing files: Permission denied"
        assert result['error_code'] == "LIST_FILES_FAILED"
# tools/get_system_info/test.py

import pytest
from unittest.mock import patch
from .api import get_system_info

@pytest.mark.asyncio
async def test_get_system_info_success():
    expected_info = {
        'os': 'Windows',
        'os_version': '10.0.19041',
        'cpu_count': 8,
        'memory': 17000000000,
        'disk_usage': 500000000000
    }
    
    with patch('platform.system', return_value='Windows'), \
         patch('platform.version', return_value='10.0.19041'), \
         patch('psutil.cpu_count', return_value=8), \
         patch('psutil.virtual_memory') as mock_virtual_memory, \
         patch('psutil.disk_usage') as mock_disk_usage:
        
        mock_virtual_memory.return_value.total = 17000000000
        mock_disk_usage.return_value.total = 500000000000
        
        result = get_system_info()
        assert result['output'] == expected_info
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_get_system_info_exception():
    with patch('psutil.cpu_count', side_effect=Exception("CPU count error")), \
         patch('platform.system', return_value='Linux'), \
         patch('platform.version', return_value='5.4.0-42-generic'):
        
        result = get_system_info()
        assert result['output'] is None
        assert result['error'] == "Error retrieving system information: CPU count error"
        assert result['error_code'] == "GET_SYSTEM_INFO_FAILED"
# tools/test_operation/test.py

import pytest
from unittest.mock import patch
from .api import test_operation

@pytest.mark.asyncio
async def test_test_operation_success():
    a = 2
    b = 3
    expected_output = 2 + 3 + (2 * 3) + 100  # 2 + 3 + 6 + 100 = 111
    
    result = test_operation(a, b)
    assert result['output'] == expected_output
    assert result['error'] is None
    assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_test_operation_failed():
    a = 2
    b = 3
    expected_error_code = "TEST_OPERATION_FAILED"
    expected_error_message = "Error performing test operation: Sample exception."
    
    with patch('tools.test_operation.api.test_operation', side_effect=Exception("Sample exception.")):
        result = test_operation(a, b)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == expected_error_code
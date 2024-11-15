# tools/fun_facts/test.py

import pytest
from unittest.mock import patch
from .api import fun_facts

@pytest.mark.asyncio
async def test_fun_facts_success():
    expected_data = {"fact": "Honey never spoils."}
    
    with patch('requests.get') as mock_get, \
         patch.dict('os.environ', {'RAPIDAPI_KEY': 'test_key'}):
        
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        
        result = fun_facts()
        mock_get.assert_called_once_with(
            "https://fun-facts1.p.rapidapi.com/api/fun-facts",
            headers={
                'x-rapidapi-key': 'test_key',
                'x-rapidapi-host': "fun-facts1.p.rapidapi.com"
            }
        )
        assert result['output'] == expected_data
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_fun_facts_missing_api_key():
    with patch.dict('os.environ', {}, clear=True):
        result = fun_facts()
        assert result['output'] is None
        assert result['error'] == "RapidAPI key is missing."
        assert result['error_code'] == "MISSING_API_KEY"

@pytest.mark.asyncio
async def test_fun_facts_fetch_failed():
    with patch('requests.get') as mock_get, \
         patch.dict('os.environ', {'RAPIDAPI_KEY': 'test_key'}):
        
        mock_response = mock_get.return_value
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        
        result = fun_facts()
        mock_get.assert_called_once_with(
            "https://fun-facts1.p.rapidapi.com/api/fun-facts",
            headers={
                'x-rapidapi-key': 'test_key',
                'x-rapidapi-host': "fun-facts1.p.rapidapi.com"
            }
        )
        assert result['output'] is None
        assert result['error'] == "Failed to fetch facts. Status code: 500"
        assert result['error_code'] == "FETCH_FAILED"

@pytest.mark.asyncio
async def test_fun_facts_unexpected_error():
    with patch('requests.get', side_effect=Exception("Network error")), \
         patch.dict('os.environ', {'RAPIDAPI_KEY': 'test_key'}):
        
        result = fun_facts()
        assert result['output'] is None
        assert result['error'] == "Error fetching fun facts: Network error"
        assert result['error_code'] == "UNEXPECTED_ERROR"
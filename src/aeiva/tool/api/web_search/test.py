# tools/web_search/test.py

import pytest
from unittest.mock import patch
from .api import web_search

@pytest.mark.asyncio
async def test_web_search_success():
    query = "Python programming"
    mock_response_data = {
        'Abstract': 'Python is a programming language.',
        'Answer': 'Python is a programming language.',
        'RelatedTopics': [{'Text': 'Python is an interpreted language.'}],
        'Image': '',
        'Type': 'A'
    }
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response_data
        
        result = web_search(query)
        mock_get.assert_called_once_with(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
        )
        assert result['output'] == {
            'Abstract': 'Python is a programming language.',
            'Answer': 'Python is a programming language.',
            'RelatedTopics': [{'Text': 'Python is an interpreted language.'}],
            'Image': '',
            'Type': 'A'
        }
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_web_search_missing_query():
    query = ""
    expected_error = "Search query must be provided."
    
    result = web_search(query)
    assert result['output'] is None
    assert result['error'] == expected_error
    assert result['error_code'] == "MISSING_QUERY"

@pytest.mark.asyncio
async def test_web_search_failed_status_code():
    query = "Python programming"
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 500
        
        result = web_search(query)
        mock_get.assert_called_once_with(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
        )
        assert result['output'] is None
        assert result['error'] == "Web search failed with status code: 500"
        assert result['error_code'] == "SEARCH_FAILED"

@pytest.mark.asyncio
async def test_web_search_exception():
    query = "Python programming"
    expected_error_code = "WEB_SEARCH_FAILED"
    expected_error_message = "Error performing web search: Sample exception."
    
    with patch('requests.get', side_effect=Exception("Sample exception.")):
        result = web_search(query)
        assert result['output'] is None
        assert result['error'] == expected_error_message
        assert result['error_code'] == "WEB_SEARCH_FAILED"
# tools/percept_terminal_input/test.py

import pytest
from unittest.mock import patch
from .api import percept_terminal_input

@pytest.mark.asyncio
async def test_percept_terminal_input_success():
    prompt_message = "Enter command: "
    user_input = "Hello, World!"
    expected_output = user_input

    with patch('builtins.input', return_value=user_input):
        result = percept_terminal_input(prompt_message)
        assert result['output'] == expected_output
        assert result['error'] is None
        assert result['error_code'] == "SUCCESS"

@pytest.mark.asyncio
async def test_percept_terminal_input_session_terminated_exit():
    prompt_message = "Enter command: "
    user_input = "exit"
    expected_error = "Input session terminated by user."

    with patch('builtins.input', return_value=user_input):
        result = percept_terminal_input(prompt_message)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "SESSION_TERMINATED"

@pytest.mark.asyncio
async def test_percept_terminal_input_session_terminated_quit():
    prompt_message = "Enter command: "
    user_input = "quit"
    expected_error = "Input session terminated by user."

    with patch('builtins.input', return_value=user_input):
        result = percept_terminal_input(prompt_message)
        assert result['output'] is None
        assert result['error'] == expected_error
        assert result['error_code'] == "SESSION_TERMINATED"

@pytest.mark.asyncio
async def test_percept_terminal_input_exception():
    prompt_message = "Enter command: "

    with patch('builtins.input', side_effect=Exception("Input error")):
        result = percept_terminal_input(prompt_message)
        assert result['output'] is None
        assert result['error'] == "Error retrieving terminal input: Input error"
        assert result['error_code'] == "INPUT_FAILED"
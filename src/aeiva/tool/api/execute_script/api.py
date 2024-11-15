# tools/execute_script/api.py

from typing import Dict, Any
import subprocess
import tempfile
import os

def execute_script(script_content: str, language: str = "python") -> Dict[str, Any]:
    """
    Executes a script in a controlled environment.

    Args:
        script_content (str): The content of the script to execute.
        language (str): The programming language of the script ('python', 'bash').

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if language not in ['python', 'bash']:
            return {
                "output": None,
                "error": "Unsupported script language. Choose 'python' or 'bash'.",
                "error_code": "UNSUPPORTED_LANGUAGE"
            }

        suffix = '.py' if language == 'python' else '.sh'
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=suffix) as temp_file:
            temp_file.write(script_content)
            temp_file_path = temp_file.name

        # Set execution permissions if necessary
        if language == 'bash':
            os.chmod(temp_file_path, 0o700)

        # Execute the script safely
        if language == 'python':
            cmd = ['python', temp_file_path]
        elif language == 'bash':
            cmd = ['bash', temp_file_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        # Remove the temporary file
        os.remove(temp_file_path)

        if result.returncode == 0:
            return {
                "output": f"Script executed successfully:\n{result.stdout}",
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": None,
                "error": f"Script execution failed:\n{result.stderr}",
                "error_code": "SCRIPT_EXECUTION_FAILED"
            }
    except subprocess.TimeoutExpired:
        return {
            "output": None,
            "error": "Script execution timed out.",
            "error_code": "TIMEOUT_EXPIRED"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error executing script: {e}",
            "error_code": "EXECUTION_FAILED"
        }
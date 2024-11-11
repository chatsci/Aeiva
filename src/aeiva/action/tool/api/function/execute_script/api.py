# tools/execute_script/api.py

import subprocess
import tempfile
import os

def execute_script(script_content: str, language: str = "python") -> str:
    """
    Execute a script in a controlled environment.

    Args:
        script_content (str): The content of the script to execute.
        language (str): The programming language of the script ('python', 'bash').

    Returns:
        str: The output or result of the script execution.
    """
    try:
        # Create a temporary file in a safe directory
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py' if language == 'python' else '.sh') as temp_file:
            temp_file.write(script_content)
            temp_file_path = temp_file.name

        # Set execution permissions if necessary
        os.chmod(temp_file_path, 0o700)

        # Execute the script safely
        if language == 'python':
            result = subprocess.run(['python', temp_file_path], capture_output=True, text=True, timeout=5)
        elif language == 'bash':
            result = subprocess.run(['bash', temp_file_path], capture_output=True, text=True, timeout=5)
        else:
            return "Unsupported script language."

        # Remove the temporary file
        os.remove(temp_file_path)

        if result.returncode == 0:
            return f"Script executed successfully:\n{result.stdout}"
        else:
            return f"Script execution failed:\n{result.stderr}"
    except Exception as e:
        return f"Error executing script: {e}"
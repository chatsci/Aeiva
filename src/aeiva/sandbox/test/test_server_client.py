from aeiva.sandbox.sandbox_client import SandboxClient

# Initialize the client with the FastAPI server's URL
client = SandboxClient("http://localhost:8000")

# Test file upload
file_name = "test_upload_file.txt"
local_upload_path = "test_upload_file.txt"
try:
    upload_response = client.upload_file(file_name, local_upload_path)
    print(f"Upload Response: {upload_response}")
except Exception as e:
    print(f"Upload Error: {e}")

# Test code execution
code = """
with open('/sandbox/test_upload_file.txt', 'r') as f:
    content = f.read()
print(content)
"""
try:
    exec_response = client.execute_code(code)
    print(f"Execution Output: {exec_response['output']}")
except Exception as e:
    print(f"Execution Error: {e}")

# Test file download
local_download_path = "downloaded_test_file.txt"
try:
    download_response = client.download_file(file_name, local_download_path)
    print(f"Download Response: {download_response}")
except Exception as e:
    print(f"Download Error: {e}")
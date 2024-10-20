from aeiva.sandbox.docker_sandbox import Sandbox

# Initialize the sandbox and start the container
with Sandbox() as sandbox:
    # Upload any type of file to the container
    sandbox.upload_file("test_upload_file.txt", "/sandbox/file.txt")
    print("File uploaded successfully")

    # Run Python code inside the container
    code = """
with open('/sandbox/file.txt', 'r') as f:
    content = f.read()
print(content)
print('you successfully executed your code in docker container!')
"""
    result = sandbox.run_code(code)
    print("Execution Result:", result.output.decode("utf-8"))

    # Download the file from the container back to the local file system
    sandbox.download_file("/sandbox/file.txt", "downloaded_file.txt")
    print("File downloaded successfully")
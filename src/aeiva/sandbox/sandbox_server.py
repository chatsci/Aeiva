from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
from aeiva.sandbox.docker_sandbox import Sandbox  # Import the working Sandbox class from docker_sandbox.py

app = FastAPI()

# Create a function to ensure the sandbox is initialized and container is running
def get_sandbox():
    global sandbox
    if not sandbox.container:
        sandbox.start_container()
    return sandbox

# Initialize the Sandbox (but ensure container is started for each request)
sandbox = Sandbox()

@app.post("/uploadfile/{file_name}")
async def upload_file(file_name: str, file: UploadFile = File(...)):
    # Ensure the sandbox container is running
    sandbox = get_sandbox()

    # Save the uploaded file locally
    local_path = f"/tmp/{file_name}"
    with open(local_path, "wb") as f:
        f.write(await file.read())

    # Upload the file to the container using the Sandbox class
    container_path = f"/sandbox/{file_name}"
    try:
        sandbox.upload_file(local_path, container_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file to container: {e}")

    return {"message": f"File {file_name} has been uploaded to the container."}


@app.get("/downloadfile/{file_name}")
async def download_file(file_name: str):
    # Ensure the sandbox container is running
    sandbox = get_sandbox()

    # Download the file from the container to the local path
    local_path = f"/tmp/{file_name}"
    container_path = f"/sandbox/{file_name}"

    try:
        sandbox.download_file(container_path, local_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file from container: {e}")

    # Return the downloaded file
    if os.path.exists(local_path):
        return FileResponse(local_path, filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/execute_code/")
async def execute_code(request_body: dict):
    # Ensure the sandbox container is running
    sandbox = get_sandbox()

    code = request_body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    # Execute the code inside the container using the Sandbox class
    try:
        result = sandbox.run_code(code)
        output = result.output.decode("utf-8") if result.output else "No output"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing code: {e}")

    return {"output": output}
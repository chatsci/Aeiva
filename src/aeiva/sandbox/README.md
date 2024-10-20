# Sandbox Module for Secure File Upload/Download and Code Execution

This module provides a secure sandbox environment that allows users to upload files, download files, and execute Python code within an isolated Docker container. It is designed to safely handle file operations and code execution without affecting the host system, using FastAPI as the interface.

## Setup Guide: Step-by-Step Instructions to Set Up the Sandbox Environment

### Step 1: Start the Docker Daemon

Ensure Docker is installed on your system. If Docker is not installed, download and install it from the official Docker website: [Docker Install Guide](https://docs.docker.com/get-docker/).

- **Linux:** Start Docker using the following command:

    ```bash
    sudo systemctl start docker
    ```

- **macOS/Windows:** Open Docker Desktop from your Applications or Start Menu.

### Step 2: Verify the Docker Daemon is Running

To confirm Docker is running, execute the following command:

```bash
docker --version
```

This will display the Docker version if it is installed and running correctly.

### Step 3: Build the Docker Image

Navigate to the project directory where the Dockerfile is located and run the following command to build the Docker image:

```bash
docker build -t sandbox_image .
```

This will create a Docker image named sandbox_image based on the configuration in the Dockerfile.

If you have trouble with download python image, try pulling the base Python image manually:
```
docker pull python:3.11-slim
```
Once it is successfully pulled, you can rerun the build.


### Step 4: Run the FastAPI Server in Docker

After building the image, run the FastAPI server inside a Docker container. Expose port 8000 so that the FastAPI API endpoints are accessible locally:

```bash
docker run -d -p 8000:8000 --name sandbox_container sandbox_image
```

The server will now be running and accessible via http://localhost:8000.

### Step 5: (Optional) Running FastAPI Locally

If you prefer to run the FastAPI server locally on your machine instead of using Docker:

```bash
uvicorn sandbox:app --host 0.0.0.0 --port 8000
```

For safety, you can create an virtual env and install the requirements.

### Step 6: Testing the Sandbox Environment
```
python test.py
```


### Step 7: Stopping and Cleaning Up the Docker Container

To stop the Docker container when you’re done:

```
docker stop sandbox_container
```

To remove the container:
```
docker rm sandbox_container
```
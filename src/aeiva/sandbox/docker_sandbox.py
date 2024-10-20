import docker
import tarfile
import os
from io import BytesIO

class Sandbox:
    def __init__(self, image="sandbox_image:latest", container_name="sandbox_container"):
        self.docker_client = docker.from_env()
        self.image = image
        self.container_name = container_name
        self.container = None

    def __enter__(self):
        # Start the container when entering the context
        self.start_container()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Stop the container when exiting the context
        self.stop_container()

    def start_container(self):
        # Check if a container with the same name exists, and remove it if necessary
        try:
            existing_container = self.docker_client.containers.get(self.container_name)
            existing_container.remove(force=True)
        except docker.errors.NotFound:
            pass  # No existing container, proceed to create a new one
        
        # Start the container
        self.container = self.docker_client.containers.run(
            self.image,
            detach=True,
            name=self.container_name,
            tty=True,
            stdin_open=True
        )

    def stop_container(self):
        # Stop and remove the container
        if self.container:
            self.container.stop()
            self.container.remove()

    def upload_file(self, local_path: str, container_path: str):
        # Create the directory inside the container if it doesn't exist
        container_dir = os.path.dirname(container_path)
        self.container.exec_run(f"mkdir -p {container_dir}")
        
        # Create a tar archive of the file to upload to the Docker container
        tar_stream = BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tar.add(local_path, arcname=os.path.basename(container_path))
        tar_stream.seek(0)
        
        # Upload the tar archive to the container
        self.container.put_archive(container_dir, tar_stream)

    def download_file(self, container_path: str, local_path: str):
        # Download a tar archive from the container
        bits, _ = self.container.get_archive(container_path)
        tar_stream = BytesIO()
        for chunk in bits:
            tar_stream.write(chunk)
        tar_stream.seek(0)

        # Extract the file from the tar archive and save it locally
        with tarfile.open(fileobj=tar_stream) as tar:
            tar.extractall(path=os.path.dirname(local_path))

    def run_code(self, code: str):
        # Execute Python code inside the container
        exec_cmd = f"python3 -c \"{code}\""
        result = self.container.exec_run(exec_cmd)
        return result
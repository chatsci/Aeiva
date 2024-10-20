import requests

class SandboxClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def upload_file(self, file_name: str, local_file_path: str):
        # Upload any file to the sandbox (FastAPI server)
        with open(local_file_path, 'rb') as f:
            files = {'file': (file_name, f)}
            response = requests.post(f'{self.base_url}/uploadfile/{file_name}', files=files)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error uploading file: {response.status_code}, {response.text}")

    def download_file(self, file_name: str, local_file_path: str):
        # Download any file from the sandbox (FastAPI server)
        response = requests.get(f'{self.base_url}/downloadfile/{file_name}', stream=True)
        if response.status_code == 200:
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return {"message": f"File {file_name} downloaded successfully"}
        else:
            raise ValueError(f"Error downloading file: {response.status_code}, {response.text}")

    def execute_code(self, code: str):
        # Execute Python code inside the sandbox (FastAPI server)
        response = requests.post(f'{self.base_url}/execute_code/', json={"code": code})
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error executing code: {response.status_code}, {response.text}")
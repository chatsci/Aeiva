import os
import pytest

docker = pytest.importorskip("docker")

from aeiva.sandbox.docker_sandbox import Sandbox


def _docker_ready(image: str) -> bool:
    try:
        client = docker.from_env()
        client.ping()
        return bool(client.images.list(name=image))
    except Exception:
        return False


def test_docker_sandbox_roundtrip(tmp_path):
    image = os.getenv("AEIVA_SANDBOX_IMAGE", "sandbox_image:latest")
    if not _docker_ready(image):
        pytest.skip("Docker not available or sandbox image missing.")

    local_path = tmp_path / "upload.txt"
    local_path.write_text("hello", encoding="utf-8")
    download_path = tmp_path / "download.txt"

    with Sandbox(image=image) as sandbox:
        sandbox.upload_file(str(local_path), "/sandbox/file.txt")
        code = "print(open('/sandbox/file.txt', 'r').read())"
        result = sandbox.run_code(code)
        assert "hello" in result.output.decode("utf-8")
        sandbox.download_file("/sandbox/file.txt", str(download_path))

    assert download_path.read_text(encoding="utf-8") == "hello"

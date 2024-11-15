import pytest
from download_arxiv_papers.api import download_arxiv_papers


def test_download_arxiv_papers(tmp_path):
    response = download_arxiv_papers(query="machine learning", max_results=2, output_dir=str(tmp_path))
    assert response["error"] is None
    assert response["error_code"] == "SUCCESS"
    assert (tmp_path / "machine_learning.pdf").exists()
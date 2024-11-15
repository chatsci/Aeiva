import pytest
from search_arxiv_papers.api import search_arxiv_papers


def test_search_arxiv_papers():
    response = search_arxiv_papers(query="machine learning", max_results=2)
    assert response["error"] is None
    assert response["error_code"] == "SUCCESS"
    assert len(response["output"]) == 2
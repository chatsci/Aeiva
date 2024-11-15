import arxiv
from typing import List, Dict


def search_arxiv_papers(query: str, paper_ids: List[str] = None, max_results: int = 5) -> Dict[str, any]:
    """
    Searches for academic papers on arXiv using a query string and optional paper IDs.

    Args:
        query (str): The search query string.
        paper_ids (List[str], optional): A list of specific arXiv paper IDs to search for. Defaults to None.
        max_results (int, optional): The maximum number of search results to return. Defaults to 5.

    Returns:
        Dict[str, any]: Dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        client = arxiv.Client()
        search_query = arxiv.Search(query=query, id_list=paper_ids or [], max_results=max_results)
        search_results = client.results(search_query)

        papers_data = []
        for paper in search_results:
            papers_data.append({
                "title": paper.title,
                "published_date": paper.updated.date().isoformat(),
                "authors": [author.name for author in paper.authors],
                "entry_id": paper.entry_id,
                "summary": paper.summary,
            })

        return {
            "output": papers_data,
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": str(e),
            "error_code": "ERROR"
        }
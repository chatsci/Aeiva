import arxiv
from pathlib import Path
from typing import List, Dict


def download_arxiv_papers(
    query: str, paper_ids: List[str] = None, max_results: int = 5, output_dir: str = "./"
) -> Dict[str, any]:
    """
    Downloads PDFs of academic papers from arXiv based on the provided query.

    Args:
        query (str): The search query string.
        paper_ids (List[str], optional): A list of specific arXiv paper IDs to download. Defaults to None.
        max_results (int, optional): The maximum number of search results to download. Defaults to 5.
        output_dir (str, optional): The directory to save the downloaded PDFs. Defaults to "./".

    Returns:
        Dict[str, any]: Dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        client = arxiv.Client()
        search_query = arxiv.Search(query=query, id_list=paper_ids or [], max_results=max_results)
        search_results = client.results(search_query)

        for paper in search_results:
            sanitized_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in paper.title)
            paper.download_pdf(dirpath=str(output_path), filename=f"{sanitized_title}.pdf")

        return {
            "output": f"Papers downloaded successfully to {output_dir}",
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": str(e),
            "error_code": "ERROR"
        }
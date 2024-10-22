# api/api_tools/arxiv_json/api.py

import requests

def get_paper_details(paper_id: str, toolbench_rapidapi_key: str='088440d910mshef857391f2fc461p17ae9ejsnaebc918926ff'):
    """Get details of a paper by Arxiv ID."""
    url = f"https://arxiv-json.p.rapidapi.com/papers/{paper_id}"
    headers = {
        "X-RapidAPI-Key": toolbench_rapidapi_key,
        "X-RapidAPI-Host": "arxiv-json.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers)
    try:
        return response.json()
    except:
        return response.text

def search_papers_by_author_and_or_keywords(keywords: str='network', sort_by: str='relevance', sort_order: str='descending', start: int=0, authors: str='geoffrey hinton', max_results: int=10, toolbench_rapidapi_key: str='088440d910mshef857391f2fc461p17ae9ejsnaebc918926ff'):
    """Search papers by author and/or keywords."""
    url = f"https://arxiv-json.p.rapidapi.com/papers"
    headers = {
        "X-RapidAPI-Key": toolbench_rapidapi_key,
        "X-RapidAPI-Host": "arxiv-json.p.rapidapi.com"
    }
    querystring = {
        "keywords": keywords,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "start": start,
        "authors": authors,
        "max_results": max_results
    }
    response = requests.get(url, headers=headers, params=querystring)
    try:
        return response.json()
    except:
        return response.text
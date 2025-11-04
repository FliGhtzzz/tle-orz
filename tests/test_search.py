from unittest.mock import MagicMock
from app.search import search_query

def test_search_query_mocks():
    es = MagicMock()
    # craft a fake response
    es.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "1",
                    "_score": 1.2,
                    "_source": {"filename":"a.py", "path":"/tmp/a.py", "content":"hello world"},
                    "highlight": {"content": ["hello \033[1mworld\033[0m"]}
                }
            ]
        }
    }
    results = search_query(es, "hello world", top_n_per_keyword=1)
    assert "hello world" in results
    hits = results["hello world"]
    assert hits[0]["filename"] == "a.py"
    assert "path_link" in hits[0]

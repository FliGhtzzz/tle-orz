from elasticsearch import Elasticsearch
from .config import load_config
from .utils import key_word_generating
from typing import List, Dict
cfg = load_config()

ES_URL = cfg["es"]["url"]
INDEX_NAME = cfg["index"]["name"]

def _format_hyperlink(path: str, text: str) -> str:
    # OSC8 hyperlink format: \x1b]8;;<uri>\x1b\\<text>\x1b]8;;\x1b\\
    # Use file:// URI
    uri = f"file://{path}"
    return f"\x1b]8;;{uri}\x1b\\{text}\x1b]8;;\x1b\\"

def search_query(es: Elasticsearch, query_text: str, top_n_per_keyword: int = None) -> Dict[str, List[Dict]]:
    """
    For each generated keyword, run a separate fuzzy match query and return top results.
    Return dict: {keyword: [hits...]}
    """
    if top_n_per_keyword is None:
        top_n_per_keyword = cfg["search"]["top_n_per_keyword"]
    keywords = key_word_generating(query_text)
    results = {}
    for kw in keywords:
        # use match with fuzziness OR match_phrase for full phrase
        q = {
            "bool": {
                "should": [
                    {"match_phrase": {"content": {"query": kw, "slop": 2}}},
                    {"match": {"content": {"query": kw, "fuzziness": "AUTO"}}},
                    {"match": {"filename": {"query": kw, "fuzziness": "AUTO", "boost": 3.0}}}
                ]
            }
        }
        resp = es.search(
            index=INDEX_NAME,
            query=q,
            highlight={
                "fields": {"content": {}},
                "pre_tags": [cfg["highlight"]["pre_tag"]],
                "post_tags": [cfg["highlight"]["post_tag"]]
            },
            size=top_n_per_keyword
        )
        hits = []
        for hit in resp.get("hits", {}).get("hits", []):
            src = hit["_source"]
            h = {
                "filename": src.get("filename"),
                "path": src.get("path"),
                "score": hit.get("_score"),
                "highlight": None
            }
            if "highlight" in hit and "content" in hit["highlight"]:
                h["highlight"] = hit["highlight"]["content"][0]
            # format path as hyperlink for terminal
            h["path_link"] = _format_hyperlink(h["path"], h["path"])
            hits.append(h)
        results[kw] = hits
    return results

def get_es_client():
    return Elasticsearch(ES_URL)

import os
from datetime import datetime
from pathlib import Path
from elasticsearch import Elasticsearch, helpers
from typing import List, Dict, Optional

from .config import load_config

cfg = load_config()

INDEX_NAME = cfg["index"]["name"]
MAX_CONTENT_BYTES = cfg["index"]["max_content_size_bytes"]
EXTS = tuple(cfg["files"]["exts"])
ES_URL = cfg["es"]["url"]

def get_es_client():
    return Elasticsearch(ES_URL)

def doc_from_path(path: str) -> Optional[Dict]:
    try:
        p = Path(path)
        stat = p.stat()
        size = stat.st_size
        content = None
        if size <= MAX_CONTENT_BYTES:
            try:
                with p.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = None
        doc = {
            "filename": p.name,
            "path": str(p.resolve()),
            "size": size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            # only include content when not too big
            "content": content
        }
        return doc
    except Exception as e:
        print("doc_from_path error:", e)
        return None

def read_folder(folder_paths: List[str]) -> List[Dict]:
    docs = []
    for folder in folder_paths:
        for root, _, files in os.walk(folder):
            for name in files:
                if not name.endswith(EXTS):
                    continue
                path = os.path.join(root, name)
                doc = doc_from_path(path)
                if doc:
                    docs.append(doc)
    return docs

def ensure_index(es: Elasticsearch):
    # create index with mapping if not exists
    if not es.indices.exists(index=INDEX_NAME):
        mapping = {
            "mappings": {
                "properties": {
                    "filename": {"type": "text"},
                    "path": {"type": "keyword"},
                    "size": {"type": "long"},
                    "created": {"type": "date"},
                    "modified": {"type": "date"},
                    "content": {"type": "text", "analyzer": "standard"}
                }
            }
        }
        es.indices.create(index=INDEX_NAME, body=mapping)

def delete_all_indices(es: Elasticsearch, skip_system: bool = True):
    indices = es.indices.get_alias(index="*")
    for index in indices:
        if skip_system and index.startswith("."):
            continue
        es.indices.delete(index=index, ignore_unavailable=True)

def bulk_index(es: Elasticsearch, docs: List[Dict], chunk_size: int = 100):
    ensure_index(es)
    actions = (
        {"_index": INDEX_NAME, "_id": d["path"], "_source": d}
        for d in docs
    )
    helpers.bulk(es, actions, chunk_size=chunk_size)

def index_single(es: Elasticsearch, path: str):
    doc = doc_from_path(path)
    if not doc:
        return
    ensure_index(es)
    es.index(index=INDEX_NAME, id=doc["path"], document=doc)

def delete_single(es: Elasticsearch, path: str):
    # delete by id (we use path as id)
    try:
        es.delete(index=INDEX_NAME, id=path)
    except Exception:
        pass

def reindex_all(folder_paths: List[str], es: Optional[Elasticsearch] = None, delete_existing: bool = True):
    if es is None:
        es = get_es_client()
    if delete_existing:
        delete_all_indices(es)
    docs = read_folder(folder_paths)
    bulk_index(es, docs)
    return len(docs)

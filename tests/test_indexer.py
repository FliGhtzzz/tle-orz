import tempfile
import os
from unittest.mock import MagicMock
import pytest
from app.indexer import doc_from_path, read_folder, bulk_index, ensure_index

def test_doc_from_path(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("print('hello')", encoding="utf-8")
    doc = doc_from_path(str(f))
    assert doc["filename"] == "a.py"
    assert "content" in doc
    assert "hello" in doc["content"]

def test_read_folder(tmp_path, monkeypatch):
    # create files and nested folder
    p = tmp_path / "sub"
    p.mkdir()
    (tmp_path / "a.py").write_text("x")
    (p / "b.py").write_text("y")
    res = read_folder([str(tmp_path)])
    assert any(d["filename"] == "a.py" for d in res)
    assert any(d["filename"] == "b.py" for d in res)

def test_bulk_index_calls_helpers(monkeypatch):
    es = MagicMock()
    # simulate ensure_index doesn't raise
    docs = [{"filename":"a.py","path":"p","size":1,"created":None,"modified":None,"content":"c"}]
    monkeypatch.setattr("app.indexer.ensure_index", lambda e: None)
    # patch helpers.bulk to capture calls
    called = {}
    def fake_bulk(es_arg, actions, chunk_size=100):
        called['actions'] = list(actions)
        return (1, [])
    monkeypatch.setattr("app.indexer.helpers.bulk", fake_bulk)
    bulk_index(es, docs)
    assert called['actions']

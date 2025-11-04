from elasticsearch import Elasticsearch
from .config import load_config
from .utils import key_word_generating
from typing import List, Dict
import math

cfg = load_config()

ES_URL = cfg["es"]["url"]
INDEX_NAME = cfg["index"]["name"]

def _format_hyperlink(path: str, text: str) -> str:
    # OSC8 hyperlink format: \x1b]8;;<uri>\x1b\\<text>\x1b]8;;\x1b\\
    # Use file:// URI
    uri = f"file://{path}"
    return f"\x1b]8;;{uri}\x1b\\{text}\x1b]8;;\x1b\\"

def _quick_scores_for_keyword(es: Elasticsearch, kw: str, field: str, size: int = 10) -> List[float]:
    """
    對單一 keyword 在 single field 做小量搜尋，回傳 top-N 的 scores（空表示沒命中）。
    用於判斷該 keyword 是否 '模糊'（噪音）。
    """
    # 對 filename 我們優先用 prefix + exact，對 content 用 match_phrase + match(fuzzy)
    if field == "filename":
        q = {
            "bool": {
                "should": [
                    {"prefix": {"filename": {"value": kw, "boost": 4.0}}},
                    {"term": {"filename.keyword": {"value": kw, "boost": 6.0}}},
                    {"match": {"filename": {"query": kw, "fuzziness": "AUTO", "boost": 2.0}}}
                ]
            }
        }
    else:
        q = {
            "bool": {
                "should": [
                    {"match_phrase": {"content": {"query": kw, "slop": 2, "boost": 3.0}}},
                    {"match": {"content": {"query": kw, "fuzziness": "AUTO", "boost": 1.0}}}
                ]
            }
        }

    resp = es.search(index=INDEX_NAME, query=q, size=size, _source=False)
    scores = [h.get("_score", 0.0) for h in resp.get("hits", {}).get("hits", [])]
    return scores

def _is_keyword_too_vague(es: Elasticsearch, kw: str, vague_count_threshold: int = 500,
                          top_sample: int = 8, score_closeness_ratio: float = 0.12) -> bool:
    """
    判斷關鍵字是否 '過於模糊'：
    - 若該關鍵字對 filename 或 content 的 count 非常大 (count > vague_count_threshold) -> 視為模糊
    - 或 top-sample 的 scores 差異很小（top 尖峰不明顯）且命中數也不少 -> 視為模糊
    這裡結合 count + top-K score 分布。
    """
    # 快速 count（content 上做 count）
    q_count = {"match": {"content": {"query": kw}}}
    try:
        cnt = es.count(index=INDEX_NAME, query=q_count).get("count", 0)
    except Exception:
        # 若 count 失敗（例如 index 不存在），視為不模糊（保守）
        cnt = 0

    if cnt >= vague_count_threshold:
        return True

    # 取 top sample scores（content）
    scores = _quick_scores_for_keyword(es, kw, field="content", size=top_sample)
    if not scores:
        return False

    # 如果 top score 很小或 top-k 分數都差不多 -> 視為模糊
    max_score = max(scores)
    min_score = min(scores)
    if max_score <= 0.0:
        return True

    # 若 top-k 差異太小，表示沒有明顯高分文件（噪音）
    if (max_score - min_score) / max_score < score_closeness_ratio and len(scores) >= 5:
        return True

    return False

def search_query(es: Elasticsearch,
                 query_text: str,
                 top_n: int = 10,
                 scope: str = "both",           # "both" | "filename" | "content"
                 vague_count_threshold: int = 500,
                 min_should_match_ratio: float = 0.6
                 ) -> Dict:
    """
    重新設計的搜尋：
    - scope: 哪些欄位要搜尋（filename / content / both）
    - 先產生 keywords，對每個 keyword 做快速模糊判斷，若太模糊則捨棄
    - 把剩下的 keywords 統一組成 single combined bool query，使用 should clauses
      並以 minimum_should_match(基於關鍵字數量與 min_should_match_ratio) 來優先匹配到更多關鍵字的文檔
    - filename 的 clause 有較高的 boost（prefix/exact）
    - content 的 clause 有 match_phrase (slop) 與 fallback fuzzy match
    - 回傳格式: {"query_text": ..., "keywords_used": [...], "hits": [...]}
    """
    if top_n is None:
        top_n = cfg["search"]["top_n"]
    keywords = key_word_generating(query_text)
    if not keywords:
        return {"query_text": query_text, "keywords_used": [], "hits": []}

    # 過濾太短或空白的 tokens（也可以在 key_word_generating 改）
    keywords = [k for k in keywords if k and k.strip()]

    # 1) 對每個 keyword 做快速模糊判斷（filename + content）
    kept = []
    for kw in keywords:
        # 如果使用者指定只查 filename 或只查 content，就只根據那個 field 判斷
        if scope == "filename":
            vague = _is_keyword_too_vague(es, kw, vague_count_threshold=vague_count_threshold)
        elif scope == "content":
            vague = _is_keyword_too_vague(es, kw, vague_count_threshold=vague_count_threshold)
        else:
            # 若兩者皆查，雙向判斷（若在任一重要欄位極模糊即可丟棄）
            vague = _is_keyword_too_vague(es, kw, vague_count_threshold=vague_count_threshold)
        if not vague:
            kept.append(kw)
        else:
            # skip vague keyword
            pass

    if not kept:
        # 如果全部被丟棄，退回使用原先至少一個 keyword 的保守查詢（避免回傳空）
        kept = keywords[:1]

    # 2) 建構 combined query
    # 每個 keyword 會有 filename-clauses 與 content-clauses（視 scope 而定）
    should_clauses = []
    for kw in kept:
        if scope in ("both", "filename"):
            # filename：term(exact) > prefix > fuzzy
            should_clauses.append({"term": {"filename.keyword": {"value": kw, "boost": 6.0}}})
            should_clauses.append({"prefix": {"filename": {"value": kw, "boost": 4.0}}})
            should_clauses.append({"match": {"filename": {"query": kw, "fuzziness": "AUTO", "boost": 2.0}}})
        if scope in ("both", "content"):
            # content：phrase (slop)，在內容少時可命中；再給一個 fuzzy fallback
            should_clauses.append({"match_phrase": {"content": {"query": kw, "slop": 2, "boost": 3.0}}})
            should_clauses.append({"match": {"content": {"query": kw, "fuzziness": "AUTO", "boost": 1.0}}})

    # minimum_should_match：設定為保留關鍵字數量的比例（至少要 match 到多少個 keyword）
    # 注意：should clauses 的數量不是等於 keyword 數 (因為每 keyword 有多個 clause)
    # 所以用一個更語意化的策略：要求在「keywords」層面至少 match 到某比例的 keywords。
    # Elasticsearch 不能直接在 keyword 層面指定 minimum_should_match，故採用下面的折衷：
    # - 計算預期每個 keyword 投入的 clause 數（approx_clauses_per_kw），再乘以 min_should_match_ratio
    approx_clauses_per_kw = 4 if scope == "both" else 2
    kws = len(kept)
    min_kw_match = max(1, math.ceil(kws * min_should_match_ratio))
    min_should = max(1, min_kw_match * (approx_clauses_per_kw // 2))  # 保守估計
    # (上面是為了轉換到 clause-level 的 minimum_should_match)

    main_query = {
        "bool": {
            "should": should_clauses,
            "minimum_should_match": min_should
        }
    }

    # 3) 執行最終查詢（一次）
    resp = es.search(
        index=INDEX_NAME,
        query=main_query,
        highlight={
            "fields": {"content": {}},
            "pre_tags": [cfg["highlight"]["pre_tag"]],
            "post_tags": [cfg["highlight"]["post_tag"]]
        },
        size=top_n
    )

    hits_out = []
    for hit in resp.get("hits", {}).get("hits", []):
        src = hit["_source"]
        h = {
            "filename": src.get("filename"),
            "path": src.get("path"),
            "path_link": _format_hyperlink(src.get("path"), src.get("path")),
            "score": hit.get("_score"),
            "highlight": None
        }
        if "highlight" in hit and "content" in hit["highlight"]:
            h["highlight"] = hit["highlight"]["content"][0]
        hits_out.append(h)

    return {
        "query_text": query_text,
        "keywords_all": keywords,
        "keywords_used": kept,
        "hits": hits_out,
        "total": resp.get("hits", {}).get("total", {})
    }

def get_es_client():
    return Elasticsearch(ES_URL)

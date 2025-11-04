import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "es": {"url": "http://localhost:9200"},
    "index": {"name": "testing_local_files", "max_content_size_bytes": 200000},
    "files": {"folders": [], "exts": [".py"]},
    "highlight": {"pre_tag": "\033[1m", "post_tag": "\033[0m"},
    "search": {"top_n": 5}
}

def load_config(path: str = "config.yaml"):
    p = Path(path)
    if not p.exists():
        return DEFAULT_CONFIG
    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # merge with default (simple)
    def merge(d, default):
        out = default.copy()
        for k, v in d.items():
            if isinstance(v, dict) and k in out:
                out[k] = merge(v, out[k])
            else:
                out[k] = v
        return out
    return merge(cfg, DEFAULT_CONFIG)

import argparse
from .config import load_config
from .indexer import reindex_all, get_es_client
from .watcher import start_watching
from .search import search_query, get_es_client as get_es_search_client

cfg = load_config()

def cmd_init(args):
    folders = cfg["files"]["folders"]
    es = get_es_client()
    count = reindex_all(folders, es=es, delete_existing=True)
    print(f"indexed {count} documents into {cfg['index']['name']}")

def cmd_watch(args):
    folders = cfg["files"]["folders"]
    es = get_es_client()
    start_watching(folders, es=es)

def cmd_query(args):
    es = get_es_search_client()
    results = search_query(es, args.query, top_n_per_keyword=args.top or None)
    # pretty print
    for kw, hits in results.items():
        print(f"\n=== keyword: {kw} ===")
        if not hits:
            print("no hits")
            continue
        for h in hits:
            print(f"file: {h['filename']}")
            print(f"path: {h['path_link']}")
            print(f"score: {h['score']}")
            if h['highlight']:
                print(f"highlight: {h['highlight']}")
            print("-" * 30)

def main():
    parser = argparse.ArgumentParser(prog="file_search")
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init")
    p_init.set_defaults(func=cmd_init)

    p_watch = sub.add_parser("watch")
    p_watch.set_defaults(func=cmd_watch)

    p_query = sub.add_parser("query")
    p_query.add_argument("query", help="query text")
    p_query.add_argument("--top", type=int, default=None, help="top n per keyword")
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)

if __name__ == "__main__":
    main()

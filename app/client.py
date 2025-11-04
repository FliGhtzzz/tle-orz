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
    es = get_es_client()  # 取得 ES client
    results = search_query(
        es,
        query_text=args.query,
        top_n=args.top or None,
        scope="both"  # 可改成 "filename" 或 "content"
    )

    print(f"\nQuery: {results['query_text']}")
    print(f"All generated keywords: {', '.join(results['keywords_all'])}")
    print(f"Keywords used (filtered): {', '.join(results['keywords_used'])}")
    print(f"Total hits: {results.get('total', {}).get('value', 'unknown')}")
    print("=" * 50)

    if not results['hits']:
        print("No results found.")
        return

    for h in results['hits']:
        print(f"file: {h['filename']}")
        print(f"path: {h['path_link']}")
        print(f"score: {h['score']:.3f}")
        if h['highlight']:
            print(f"highlight: {h['highlight']}")
        print("-" * 50)

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

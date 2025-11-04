import os
from datetime import datetime
from elasticsearch import Elasticsearch, helpers

INDEX_NAME = "testing_local_files"
PROCESSING_EXT = (".py",)


def read_folder(folder_path):
    docs = []

    for root, _, files in os.walk(folder_path):
        for name in files:
            path = os.path.join(root, name)

            if not name.endswith(PROCESSING_EXT):
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                print("讀取錯誤:", path, e)
                continue

            doc = {
                "filename": name,
                "path": path,
                "content": content,
                "modify": datetime.fromtimestamp(os.path.getmtime(path))
            }
            docs.append(doc)

    return docs


if __name__ == '__main__':
    es = Elasticsearch("http://localhost:9200")
    print(es)

    # 取得所有索引
    indices = es.indices.get_alias(index="*")
    for index in indices:
        # 跳過內建索引（通常以 '.' 開頭）
        if index.startswith("."):
            print(f"skip system index: {index}")
            continue
        print(f"delete index: {index}")
        es.indices.delete(index=index)

    # build indexes
    folder = r"C:\我是D槽\python"
    docs = read_folder(folder)
    print(f"read folder '{folder}' done")

    actions = (
        {"_index": INDEX_NAME, "_source": doc}
        for doc in docs
    )
    helpers.bulk(es, actions, chunk_size=100)
    print("bulk done")
    print("\033[1m" + "─" * 30 + "\033[0m")

    # queries
    while True:
        query_text = input("query for: ")
        if not query_text: continue
        if query_text.lower() in ("q", "quit"):
            break

        resp = es.search(
            index=INDEX_NAME,
            query={
                "match": {
                    "content": query_text
                }
            },
            highlight={"fields": {"content": {}}, "pre_tags": ["\033[1m"], "post_tags": ["\033[0m"]},
            size=5  # 回傳前 5 筆
        )

        for hit in resp["hits"]["hits"]:
            print(f"file: {hit['_source']['filename']}")
            print(f"path: {hit['_source']['path']}")
            print(f"score: {hit['_score']}")
            print(f"highlight: {hit["highlight"]["content"][0]}")
            print()
        print("\033[1m" + "─" * 30 + "\033[0m")

import os,sys,time,hashlib
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tika import parser
import userInputToLLM as userSend

_host =  "http://localhost:9200"


'''  意義不明
BULK_SIZE = 100
_folder = r'C:/Users/kzzz/Desktop/test_ES'
_index_name = "test"
def build_index(es,index_name):
    mapping = {
        "properties": {
            "path": {"type": "keyword"},
            "filename": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "filetype": {"type": "keyword"},
            "filesize": {"type": "long"},
            "modified_at": {"type": "date"},
            "content": {"type": "text"}
        }
    }
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name,mappings=mapping)
        print(f"有 index: {index_name} 了")
    else:
        print(f"已經有 {index_name} 了啦")

def file_id_from_path(p: str):
    return hashlib.sha1(p.encode("utf-8")).hexdigest()

def doc_for_file(path:str):
    stat = os.stat(path)
    doc = {
        "path": str(Path(path).resolve()),
        "filename": Path(path).name,
        "filetype": Path(path).suffix.lower().lstrip('.'),
        "filesize": stat.st_size,
        "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
        "content": file_to_text(path)
    }
    return doc

def index_folder(es,folder,index_name):
    actions = []
    count = 0
    for root,dirs,files in os.walk(folder):
        for fn in files:
            p = os.path.join(root,fn)
            doc = doc_for_file(p)
            action = {
                "_op_type": "index",
                "_index": index_name,
                "_id": file_id_from_path(doc["path"]),
                "_source": doc
            }
            actions.append(action)
            count += 1
            if len(actions)>=BULK_SIZE:
                bulk(es,actions)
                print(f'上傳 {count} 筆了')
                actions = []
    if actions:
        bulk(es,actions)
        print(f'總共有 {count} 筆')

def file_to_text(path:str,LLM):
    ext = Path(path).suffix.lower()
    if ext in {'.txt','.md','.py','.csv', '.json', '.log', '.html'}:
        try:
            with open(path,'r',encoding='utf-8',errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
    try:
        parsed = parser.from_file(path)
        content = parsed.get('content')
        if content:
            return content
    except Exception as e:
        print(f'tika燒雞了喔 {path} {e}')
    return ""
'''

def connect():
    try :
        es = Elasticsearch(_host)
    except :
        print('你肯定有啥沒弄好')
    if not es.ping():
        print("你ES沒開阿")
    return es


def test_search(es,index_name,query_text,size=10):
    body = {
        "query": {
            "match": {
                "content": query_text
            }
        },
        'size' : size
    }
    res = es.search(index=index_name,body=body)
    print(f"我搜到 {res['hits']['total']} 筆")
    count = 0
    for hit in res['hits']['hits'][:10]:
        count+=1
        print(f'{count}. ,{hit["_source"]["content"]}, 分數 : {hit["score"]}')


if __name__ == '__main__':

    api_base, provider, model, api_key = userSend.get_llm_imformation()
    LLM = userSend.LLM(api_base, provider, model, api_key)

    es = connect()

    input_info = userSend.user_input()
    reply = LLM.send_to_llm(*input_info)
    test_search(es,_index_name,reply)
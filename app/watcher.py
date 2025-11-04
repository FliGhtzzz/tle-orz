import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileMovedEvent, FileDeletedEvent
from .indexer import index_single, delete_single, EXTS, get_es_client
from .config import load_config
from pathlib import Path

cfg = load_config()

class ESFileHandler(FileSystemEventHandler):
    def __init__(self, es):
        super().__init__()
        self.es = es

    @staticmethod
    def _should_handle(path):
        p = Path(path)
        return p.suffix in tuple(cfg["files"]["exts"])

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory: return
        if not self._should_handle(event.src_path): return
        print(f"created: {event.src_path} -> indexing")
        index_single(self.es, event.src_path)

    def on_modified(self, event: FileModifiedEvent):
        if event.is_directory: return
        if not self._should_handle(event.src_path): return
        print(f"modified: {event.src_path} -> reindex")
        index_single(self.es, event.src_path)

    def on_moved(self, event: FileMovedEvent):
        if event.is_directory: return
        # delete old id, index at new path
        print(f"moved: {event.src_path} -> {event.dest_path}")
        delete_single(self.es, event.src_path)
        if self._should_handle(event.dest_path):
            index_single(self.es, event.dest_path)

    def on_deleted(self, event: FileDeletedEvent):
        if event.is_directory: return
        print(f"deleted: {event.src_path} -> deleting from ES")
        delete_single(self.es, event.src_path)

def start_watching(folder_paths: list, es=None):
    if es is None:
        es = get_es_client()
    event_handler = ESFileHandler(es)
    observer = Observer()
    for folder in folder_paths:
        observer.schedule(event_handler, folder, recursive=True)
    observer.start()
    print("watcher started")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

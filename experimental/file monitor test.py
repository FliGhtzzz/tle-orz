import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_created(self,event):
        print(f"檔案 {event.src_path} 被建立，準備加入Elastic Search")
    def on_modified(self,event):
        print(f"檔案 {event.src_path} 被修改，準備修改後加入Elastic Search")
    def on_moved(self,event):
        print(f"檔案 {event.src_path} 被移動到 {event.dest_path}，準備重新加入Elastic Search")
    def on_deleted(self,event):
        print(f'檔案 {event.src_path} 被刪除，準備從 Elastic Search中刪除')

monitor_file = r"C:\我是D槽\python"
event_handler = MyHandler()
observer = Observer()
observer.schedule(event_handler, monitor_file, recursive=True)
observer.start()

if __name__ == '__main__':
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

from typing import List
import re

def key_word_generating(text: str) -> List[str]:
    """
    假設的關鍵字生成器：簡單實作：
    - 以非英數字分隔並去重
    - 同時回傳原句（可做 phrase 搜尋）
    你可以把這個 function 換成更進階的 tokenizer。
    """
    tokens = re.split(r'\W+', text)
    tokens = [t for t in tokens if t]
    uniq = []
    for t in tokens:
        if t not in uniq:
            uniq.append(t)
    out = []
    if text.strip():
        out.append(text.strip())
    out.extend(uniq)
    return out

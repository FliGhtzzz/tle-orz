import base64

from litellm import completion
import userInputToLLM as llm 

def getLLM():
    api_base, provider, model, api_key = userSend.get_llm_imformation()
    prompt = ''
    LLM = llm.LLM(api_base, provider, model, api_key,prompt)
    return LLM

def fileToText(file_path,LLM):
    ext = os.path.splitext(path)[1]
    content = ''
    if ext in {'.jpg','.jpeg','.png','.gif','.bmp','.webp','.ico','.svg'}:
        content=LLM.send_to_llm(file_path=file_path)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    
    return content
    




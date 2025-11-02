import base64

from litellm import completion

# 取得使用者LLM的資訊用來初始化
def get_llm_imformation():
    #type = input('你用哪個平台的LLM? openai/gemini/lmstudio/ollama... ')
    #model= input('你用哪個模型?')
    type = 'lmstudio'  #開發測試用
    model = 'qwen/qwen2.5-vl-7b'  #開發測試用
    api_base = ''
    provider = ''
    api_key = ''
    if type == 'openai':
        api_base = 'http://api.openai.com/v1'
        provider = 'openai'
        api_key = input('你的api key?')
    elif type == 'gemini':
        api_base = 'https://generativelanguage.googleapis.com/v1beta/openai/'
        provider = 'gemini'
        api_key = input('你的api key?')
    elif type == 'lmstudio':
        #api_base = input('你的URL?')
        api_base='http://192.168.0.105:1234/v1'  #開發測試用
        provider = 'openai'
        api_key = 'lmstudio'
    elif type == 'ollama':
        api_base = input('你的URL?')
        provider = 'ollama'
        api_key = 'ollama'
    return [api_base, provider,model, api_key]

# 使用者輸入想找的檔案
def user_input():
    file_path = ''
    if input('你要上傳檔案嗎 Y/N') == 'Y':
        file_path = input('檔案絕對路徑:')
    text = input('你想找甚麼檔案?')
    return [text,file_path]

def image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        base64_bytes = base64.b64encode(f.read()).decode('utf-8')
    return base64_bytes


# 用來操控LLM的物件
class LLM():
    api_base=''
    api_key=''
    provider=''
    model=''
    conversation =[{
        'role':'system',
        'content':'使用者輸入：{input_text}將以上使用者輸入的文字或問題轉換成多組關鍵字用以檔案搜尋，關鍵字越多越好，可以使用任何符號、任何語言，輸出依照以下格式(以半形空白分隔): apple 114514 城堡(這是範例，不是你應該輸出的內容)。並且不要輸出任何額外內容，請只輸出一行關鍵字。請先一步一步慢慢思考，回想與使用者輸入的文字、問題相關的任何內容，並且嘗試揣測使用者的意圖，最後一行按照以上格式輸出你最有把握的關鍵字組合。'
    }]
    def __init__(self, api_base,provider, model,api_key):
        self.api_base = api_base
        self.model = model
        self.provider = provider
        self.api_key = api_key

    def send_to_llm(self,text,file_path=''):
        if self.provider == '' or self.model == '':
            return '資料有遺漏，填寫完整再使用'

        if file_path == '':
            self.conversation.append({
                'role': 'user',
                'content': text
            })
        else:
            self.conversation.append({
                'role' : 'user',
                'content' : [
                    {'type' : 'text', 'text' : text},
                    {'type' : 'image_url', 'image_url' : f"data:image/png;base64,{image_to_base64(file_path)}"},
                ]
            })

        result= completion(
            model=f"{self.provider}/{self.model}",
            api_base=self.api_base,
            api_key=self.api_key,
            messages=self.conversation
        )
        self.conversation.append({
            'role' : 'assistant',
            'content' : result['choices'][0]['message']['content']
        })
        return result['choices'][0]['message']['content']

if __name__ == '__main__':
    api_base,provider,model,api_key = get_llm_imformation()
    LLM = LLM(api_base,provider,model,api_key)
    while True:
        input_info = user_input()
        reply = LLM.send_to_llm(*input_info)
        print(reply)

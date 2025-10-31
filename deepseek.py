import requests

def query_celebrity_timeline(celebrity_name):
    api_key = "您的_API_Key"
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": f"请按照 {{ year: 1893, age: 0, place: '湘潭·韶山', lat: 27.922, lon: 112.528, title: '出生', detail: '出生于湖南省湘潭县韶山冲。' }} 这样的JSON格式列出{celebrity_name}的生平时间线"
            }
        ],
        "temperature": 0.3
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# 使用示例
result = query_celebrity_timeline("刘德华")
print(result)
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# 初始化客户端
client = OpenAI(
    api_key=os.getenv("MOONSHOT_API_KEY"),  # 请确保设置了环境变量
    base_url="https://api.moonshot.cn/v1"
)
celebrity_name = "苏轼"

# 发起聊天完成请求
try:
    prompt = (
        "请根据维基百科、百科资料和常识，生成 " + celebrity_name + " 的生平轨迹"
    )
    response = client.chat.completions.create(
        model="moonshot-v1-8k",
        messages=[
            {"role": "system", "content": (
                "你是一个历史资料整理助手。请通过函数工具严格返回事件数组 events。"
                "每个事件必须包含 year, age, place, lat, lon, title, detail 字段；"
                "若无法确定年龄或经纬度，请将对应字段填为空字符串 \"\"；"
                "不要任何多余文字或解释。"
            )},
            {"role": "user", "content": prompt},
],
        temperature=0.3,
        max_tokens=8192,
        top_p=1,
        stream=True
    )
    
    # 处理流式响应
    for chunk in response:
        choice = chunk.choices[0]
        if choice.delta and hasattr(choice.delta, "reasoning_content"):
            reasoning_content = getattr(choice.delta, "reasoning_content", None)
            if reasoning_content:
                print(reasoning_content, end="")
        if choice.delta and choice.delta.content is not None:
            print(choice.delta.content, end="")
    print()  # 换行
    
except Exception as e:
    print(f"请求失败: {e}")

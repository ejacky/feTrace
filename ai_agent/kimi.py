import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any, Dict

load_dotenv()
# 初始化客户端
client = OpenAI(
    api_key=os.getenv("MOONSHOT_API_KEY"),  # 请确保设置了环境变量
    base_url="https://api.moonshot.cn/v1"
)

# 发起聊天完成请求

system_prompt = """
请使用如下 JSON 格式输出你的回复：
 
{
    "year": "事件发生年份",
    "age": "事件发生年龄",
    "place": "事件发生地点",
    "title": "什么事件",
    "detail": "事件详情",
    "lat": "纬度",
    "lon": "经度"
}

"""

def get_person_timeline(celebrity_name: str) -> Dict[str, Any]:
    """
    获取人物时间线数据
    """ 
 
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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
    ],
        temperature=0.6,
        response_format={"type": "json_object"},
        max_tokens=1024*5, # 最大输出token数，最大输入 + 输出总长度是 8192
    )       

    return {"events": json.loads(response.choices[0].message.content)["events"]}

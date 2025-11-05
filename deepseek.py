"""
DeepSeek API 访问工具

- 从配置文件读取 API Key（项目根目录 config.json 中的 DEEPSEEK_API_KEY），并兼容环境变量
- 提供 get_person_timeline(name) 方法给 index.py 使用，返回符合 people.json 结构的条目
"""

import os
import json
from typing import Any, Dict, List, Optional
import logging
import config

try:
    import requests  # 需通过 pip 安装：pip install requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from requests.exceptions import Timeout, RequestException
except Exception:
    requests = None
    HTTPAdapter = None
    Retry = None
    Timeout = Exception
    RequestException = Exception

ROOT = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT, 'config.json')

# 模块级日志：避免重复添加处理器
logger = logging.getLogger('deepseek')
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] deepseek: %(message)s'))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


def _get_api_key() -> Optional[str]:
    # 统一从 config.py 获取
    key = config.get_deepseek_api_key()
    return key


_SESSION = None

def _get_timeouts():
    # 从 config 获取超时，提供默认值
    try:
        connect = int(config.get('DEEPSEEK_CONNECT_TIMEOUT', 5))
        read = int(config.get('DEEPSEEK_READ_TIMEOUT', 30))
        return (connect, read)
    except Exception:
        return (5, 15)

def _get_retry_params():
    try:
        total = int(config.get('DEEPSEEK_RETRY_TOTAL', 2))
        connect = int(config.get('DEEPSEEK_RETRY_CONNECT', total))
        read = int(config.get('DEEPSEEK_RETRY_READ', total))
        status = int(config.get('DEEPSEEK_RETRY_STATUS', total))
        backoff = float(config.get('DEEPSEEK_BACKOFF_FACTOR', 0.6))
        return {
            'total': total,
            'connect': connect,
            'read': read,
            'status': status,
            'backoff': backoff,
        }
    except Exception:
        return {
            'total': 2,
            'connect': 2,
            'read': 2,
            'status': 2,
            'backoff': 0.6,
        }

def _get_session():
    """获取带重试的 Session（若可用）。"""
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    if requests is None:
        return None
    s = requests.Session()
    try:
        if HTTPAdapter and Retry:
            params = _get_retry_params()
            retry = Retry(
                total=params['total'],
                connect=params['connect'],
                read=params['read'],
                status=params['status'],
                backoff_factor=params['backoff'],
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"],
            )
            adapter = HTTPAdapter(max_retries=retry)
            s.mount("https://", adapter)
            s.mount("http://", adapter)
    except Exception:
        # 回退到无重试的 Session
        pass
    _SESSION = s
    return s


def _normalize_events(payload_text: str) -> List[Dict[str, Any]]:
    """尝试从返回文本中解析事件数组。
    期望格式为 JSON 数组 [{ year, age, place, lat, lon, title, detail }, ...]
    """
    try:
        # 粗略查找 JSON 起始位置，尽量容错
        start_idx = min([
            i for i in [payload_text.find('['), payload_text.find('{')]
            if i >= 0
        ])
        if start_idx < 0:
            return []
        text = payload_text[start_idx:].strip()
        data = json.loads(text)
        if isinstance(data, dict) and 'events' in data and isinstance(data['events'], list):
            return data['events']
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def query_celebrity_timeline(celebrity_name: str) -> Dict[str, Any]:
    """调用后端服务，根据人名返回原始响应（未归一化）。"""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "missing_api_key"}
    if requests is None:
        return {"error": "missing_requests"}

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        "你是一个历史资料整理助手。\n"
        "请根据维基百科、百科资料和常识，生成 " + celebrity_name + " 的生平轨迹，\n"
        "输出 JSON 数组，每个元素包含以下字段：\n"
        "year, age, place, lat, lon, title, detail。\n"
        "请严格输出为 JSON，不要任何多余文字。"
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        sess = _get_session()
        if sess is None:
            return {"error": "missing_requests"}
        # 分离连接/读取超时，适度缩短阻塞
        timeout = _get_timeouts()
        resp = sess.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Timeout as e:
        return {"error": f"timeout: {e}"}
    except RequestException as e:
        return {"error": f"request_failed: {e}"}


def get_person_timeline(name: str) -> Dict[str, Any]:
    """供 index.py 使用：返回符合 people.json 结构的单人物条目。
    结构：{ name, style, events }
    - style 可为空或给默认颜色
    - events 为数组，字段包含 year/age/place/lat/lon/title/detail（若缺失则尽量留空）
    """
    raw = query_celebrity_timeline(name)
    # 错误或不可用时返回空数据，避免阻断前端，并记录错误日志
    if 'error' in raw:
        try:
            logger.error("DeepSeek 请求失败：name=%s, error=%s", name, raw.get('error'))
        except Exception:
            pass
        return {"name": name, "style": None, "events": []}

    try:
        # DeepSeek 响应常见结构：choices[0].message.content
        content = (
            ((raw.get('choices') or [{}])[0].get('message') or {}).get('content')
            or json.dumps(raw)
        )
        events = _normalize_events(content)
    except Exception:
        logger.warning("DeepSeek 响应解析失败，使用空事件：name=%s", name)
        events = []

    # 默认样式（粉色系），与现有页面风格保持一致
    style = {"markerColor": "#e91e63", "lineColor": "#f06292"}
    return {"name": name, "style": style, "events": events}

if __name__ == '__main__':
    # 简单自测：读取配置并尝试请求
    who = os.environ.get('TEST_NAME', '毛主席')
    item = get_person_timeline(who)
    print(json.dumps(item, ensure_ascii=False, indent=2))

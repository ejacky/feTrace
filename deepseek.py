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
import re

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


def _get_tools_schema() -> List[Dict[str, Any]]:
    """函数工具的 JSON Schema，用于强制返回结构化事件数组。"""
    return [{
        "type": "function",
        "function": {
            "name": "produce_events",
            "description": "Return timeline events array for the specified person.",
            "parameters": {
                "type": "object",
                "properties": {
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "year": {"type": "string"},
                                "age": {"type": "string"},  # 必填：无法确定则填 ""
                                "place": {"type": "string"},
                                "lat": {"type": ["number", "string"]},  # 必填：缺失则填 ""
                                "lon": {"type": ["number", "string"]},  # 必填：缺失则填 ""
                                "title": {"type": "string"},
                                "detail": {"type": "string"},
                            },
                            "required": ["year", "age", "place", "lat", "lon", "title"]
                        }
                    }
                },
                "required": ["events"]
            }
        }
    }]


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
        "请根据维基百科、百科资料和常识，生成 " + celebrity_name + " 的生平轨迹"
    )
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": (
                "你是一个历史资料整理助手。请通过函数工具严格返回事件数组 events。"
                "每个事件必须包含 year, age, place, lat, lon, title, detail 字段；"
                "若无法确定年龄或经纬度，请将对应字段填为空字符串 \"\"；"
                "不要任何多余文字或解释。"
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "tools": _get_tools_schema(),
        "tool_choice": "required"
    }

    try:
        sess = _get_session()
        if sess is None:
            return {"error": "missing_requests"}
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
        # 优先解析函数工具调用的 JSON 参数
        msg = ((raw.get('choices') or [{}])[0].get('message') or {})
        tool_calls = msg.get('tool_calls') or []
        events: List[Dict[str, Any]] = []
        if tool_calls:
            args_text = (((tool_calls[0] or {}).get('function') or {}).get('arguments')) or "{}"
            args_obj = json.loads(args_text)
            events = (args_obj.get('events') or [])
        else:
            content = msg.get('content') or json.dumps(raw)
            events = _normalize_events(content)
    except Exception:
        logger.warning("DeepSeek 响应解析失败，使用空事件：name=%s", name)
        events = []

    # 最终补全 age/lat/lon
    events = _augment_events(events)

    style = {"markerColor": "#e91e63", "lineColor": "#f06292"}
    return {"name": name, "style": style, "events": events}


_GEOCODE_CACHE: Dict[str, Optional[Dict[str, float]]] = {}

def _parse_int_year(year_text: str) -> Optional[int]:
    m = re.search(r"\d{4}", str(year_text))
    return int(m.group(0)) if m else None

def _infer_birth_year(events: List[Dict[str, Any]]) -> Optional[int]:
    for e in events:
        title = str(e.get("title", ""))
        detail = str(e.get("detail", ""))
        y = _parse_int_year(e.get("year", ""))
        if y and ("出生" in title or "出生" in detail or "诞生" in title):
            return y
    return None

def _fill_missing_age(events: List[Dict[str, Any]]) -> None:
    birth_year = _infer_birth_year(events)
    if birth_year is None:
        return
    for e in events:
        if not str(e.get("age", "")).strip():
            y = _parse_int_year(e.get("year", ""))
            if y and y >= birth_year:
                e["age"] = str(y - birth_year)

def _geocode_place(place: str) -> Optional[Dict[str, float]]:
    p = (place or "").strip()
    if not p:
        return None
    if p in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[p]
    sess = _get_session()
    if sess is None:
        _GEOCODE_CACHE[p] = None
        return None
    try:
        resp = sess.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": p, "format": "json", "limit": 1},
            headers={"User-Agent": "feTrace/1.0"},
            timeout=_get_timeouts()
        )
        resp.raise_for_status()
        arr = resp.json() or []
        if arr:
            lat = float(arr[0].get("lat"))
            lon = float(arr[0].get("lon"))
            _GEOCODE_CACHE[p] = {"lat": lat, "lon": lon}
            return _GEOCODE_CACHE[p]
    except Exception:
        pass
    _GEOCODE_CACHE[p] = None
    return None

def _augment_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 填充年龄
    _fill_missing_age(events)
    # 填充经纬度（保守限流）
    max_calls = int(config.get("GEOCODE_MAX_CALLS", 3))
    calls = 0
    for e in events:
        lat_empty = str(e.get("lat", "")).strip() == ""
        lon_empty = str(e.get("lon", "")).strip() == ""
        if (lat_empty or lon_empty) and calls < max_calls and bool(config.get("GEOCODE_ENABLED", True)):
            coords = _geocode_place(str(e.get("place", "")))
            calls += 1
            if coords:
                e["lat"] = coords["lat"]
                e["lon"] = coords["lon"]
            else:
                # 若地理编码失败，确保有占位符
                e["lat"] = e.get("lat", "")
                e["lon"] = e.get("lon", "")
    return events

if __name__ == '__main__':
    # 简单自测：读取配置并尝试请求
    who = os.environ.get('TEST_NAME', '朱德')
    item = get_person_timeline(who)
    print(json.dumps(item, ensure_ascii=False, indent=2))

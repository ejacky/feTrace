"""
项目统一配置入口。

- 支持环境变量覆盖（优先级高）
- 其次读取项目根目录的 config.json
- 为常用配置提供默认值
"""

import os
import json
from typing import Any, Dict, Optional

ROOT = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT, 'config/config.json')


def _load_config() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def get(key: str, default: Optional[Any] = None) -> Any:
    # 环境变量优先
    if key in os.environ:
        val = os.environ.get(key)
        return val
    cfg = _load_config()
    return cfg.get(key, default)


def get_port() -> int:
    val = get('PORT', '8001')
    try:
        return int(val)
    except Exception:
        return 8001


def get_flush_interval_sec() -> int:
    val = get('FLUSH_INTERVAL_SEC', '30')
    try:
        return int(val)
    except Exception:
        return 30


def get_deepseek_api_key() -> Optional[str]:
    key = get('DEEPSEEK_API_KEY', None)
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None
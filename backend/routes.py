import json
from urllib.parse import parse_qs
from typing import Dict, Any
import deepseek


def handle_people(handler, cache, fallback: Dict[str, Any]):
    payload = cache.get_people_or_fallback(fallback)
    handler._set_headers(200)
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))


def handle_person(handler, cache, fallback: Dict[str, Any], logger=None):
    qs = parse_qs((handler.path.split('?', 1)[1] if '?' in handler.path else '') or '')
    name = (qs.get('name') or [''])[0].strip()
    if not name:
        handler._set_headers(400)
        handler.wfile.write(json.dumps({"error": "missing name"}, ensure_ascii=False).encode('utf-8'))
        return
    logger.info("查询人物：name=%s", name)
    source = cache.get_people_or_fallback(fallback)
    persons = (source or {}).get('persons') or []
    found = None
    for p in persons:
        if str(p.get('name', '')).strip() == name:
            found = p
            break
    if not found:
        try:
            found = deepseek.get_person_timeline(name)
        except Exception:
            found = None
    if found and len(found.get('events', [])) > 0:
        try:
            cache.upsert_person(found, fallback)
            if logger:
                logger.info("缓存已更新并标记落盘：name=%s, events=%d", name, len(found.get('events', [])))
        except Exception:
            pass
    if not found or len(found.get('events', [])) == 0:
        found = {"name": name, "style": None, "events": []}
    handler._set_headers(200)
    handler.wfile.write(json.dumps(found, ensure_ascii=False).encode('utf-8'))


def handle_names(handler, cache):
    names = cache.get_names()
    handler._set_headers(200)
    handler.wfile.write(json.dumps(names, ensure_ascii=False).encode('utf-8'))
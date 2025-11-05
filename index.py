"""
简易本地接口服务：当 people.json 无数据时，提供 /api/people 的回退数据。

- 端口：8001
- 接口：GET /api/people
  1) 若同目录下存在 people.json 且 persons 非空，直接返回该文件内容
  2) 否则返回内置的示例数据
  3) 设置 CORS 头以允许前端从不同端口访问
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import threading
import time
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
from deepseek import get_person_timeline
import deepseek

ROOT = os.path.dirname(__file__)
DOC_DIR = os.path.join(ROOT, 'doc')

try:
    import xlrd  # 解析 .xls
except Exception:
    xlrd = None

# 内存缓存
CACHE: Dict[str, Any] = {
    'people': None,      # 完整 people 数据（dict，含 persons）
    'names': [],         # 合并后的姓名列表（excel + people.json）
    'dirty': False,      # 是否有待落盘的变更
}

CACHE_LOCK = threading.Lock()


def read_people_json():
    path = os.path.join(ROOT, 'people.json')
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception:
        return None


def is_empty(data):
    try:
        persons = (data or {}).get('persons')
        return not persons or len(persons) == 0
    except Exception:
        return True


# 内置示例数据（结构与 people.json 保持一致）
FALLBACK = {
    "persons": [
        {
            "name": "毛泽东",
            "style": {"markerColor": "#f97316", "lineColor": "#fb923c"},
            "events": [
                {"year": 1893, "age": 0, "place": "湘潭·韶山", "lat": 27.922, "lon": 112.528, "title": "出生", "detail": "出生于湖南省湘潭县韶山冲。"},
                {"year": 1921, "age": 28, "place": "上海", "lat": 31.2304, "lon": 121.4737, "title": "参加建党", "detail": "参与中国共产党成立相关活动。"},
                {"year": 1935, "age": 42, "place": "遵义", "lat": 27.733, "lon": 106.917, "title": "遵义会议", "detail": "在遵义会议上确立领导地位。"},
                {"year": 1949, "age": 56, "place": "北京", "lat": 39.9042, "lon": 116.4074, "title": "新中国成立", "detail": "中华人民共和国成立，迁至北京工作。"}
            ]
        },
        {
            "name": "毛晓彤",
            "style": {"markerColor": "#e91e63", "lineColor": "#f06292"},
            "events": [
                {"year": 1988, "age": 0, "place": "天津", "lat": 39.084, "lon": 117.199, "title": "出生", "detail": "出生于天津。"},
                {"year": 2006, "age": 18, "place": "北京", "lat": 39.9042, "lon": 116.4074, "title": "就读表演", "detail": "在北京系统学习表演。"},
                {"year": 2014, "age": 26, "place": "横店（浙江·金华）", "lat": 29.156, "lon": 120.032, "title": "横店拍摄", "detail": "参与多部剧集拍摄工作。"},
                {"year": 2017, "age": 29, "place": "上海", "lat": 31.2304, "lon": 121.4737, "title": "作品播出", "detail": "多部作品在沪上平台播出。"}
            ]
        }
    ]
}


class Handler(BaseHTTPRequestHandler):
    ROOT = os.path.dirname(__file__)
    MIME = {
        '.html': 'text/html; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.svg': 'image/svg+xml',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

    def _set_headers(self, code=200, content_type='application/json', cors=True):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        if cors:
            # CORS 允许跨端口访问（仅对 API 必须，静态资源也无害）
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _safe_path(self, url_path: str):
        # 将 URL 路径安全映射到本地文件路径，防止目录穿越
        rel = url_path.lstrip('/') or 'index.html'
        fs_path = os.path.normpath(os.path.join(self.ROOT, rel))
        if not fs_path.startswith(self.ROOT):
            return None
        return fs_path

    def _serve_file(self, fs_path: str):
        if not fs_path or not os.path.isfile(fs_path):
            self._set_headers(404, 'text/plain; charset=utf-8', cors=False)
            self.wfile.write(b'Not Found')
            return
        ext = os.path.splitext(fs_path)[1].lower()
        ctype = self.MIME.get(ext, 'application/octet-stream')
        try:
            with open(fs_path, 'rb') as f:
                data = f.read()
            self._set_headers(200, ctype, cors=False)
            self.wfile.write(data)
        except Exception:
            self._set_headers(500, 'text/plain; charset=utf-8', cors=False)
            self.wfile.write(b'Internal Server Error')

    def do_OPTIONS(self):
        # 处理预检请求
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/people':
            data = CACHE.get('people')
            if not data or is_empty(data):
                payload = FALLBACK
            else:
                payload = data
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        elif parsed.path == '/api/person':
            # 按需返回单个人物数据
            qs = parse_qs(parsed.query or '')
            name = (qs.get('name') or [''])[0].strip()
            if not name:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "missing name"}, ensure_ascii=False).encode('utf-8'))
                return
            source = CACHE.get('people') or FALLBACK
            persons = (source or {}).get('persons') or []
            found = None
            for p in persons:
                if str(p.get('name', '')).strip() == name:
                    found = p
                    break
            if not found:
                # 尝试从 deepseek.py 获取数据
                try:
                    found = deepseek.get_person_timeline(name)
                except Exception:
                    pass
            # 若从 deepseek 获得有效数据，写入内存缓存并标记待落盘
            if found and len(found.get('events', [])) > 0:
                try:
                    with CACHE_LOCK:
                        base = CACHE.get('people') or FALLBACK
                        persons = (base or {}).get('persons') or []
                        # 以名字去重，大小写不敏感
                        idx = None
                        for i, p in enumerate(persons):
                            if str(p.get('name', '')).strip().lower() == name.lower():
                                idx = i
                                break
                        if idx is None:
                            persons.append(found)
                        else:
                            persons[idx] = found
                        # 回写到 CACHE['people']
                        if base is FALLBACK:
                            # 若当前 people 使用 FALLBACK，则生成新结构
                            CACHE['people'] = { 'persons': persons }
                        else:
                            CACHE['people']['persons'] = persons
                        # 更新 names 去重
                        names = set([n.lower() for n in (CACHE.get('names') or [])])
                        if name.lower() not in names:
                            CACHE['names'].append(name)
                        # 标记脏写
                        CACHE['dirty'] = True
                except Exception:
                    # 缓存写入失败不影响响应
                    pass
            if len(found.get('events', [])) == 0:
                # 不返回 404，统一返回空数据以便前端处理
                found = {"name": name, "style": None, "events": []}
            self._set_headers(200)
            self.wfile.write(json.dumps(found, ensure_ascii=False).encode('utf-8'))
        elif parsed.path == '/api/names':
            # 返回合并的姓名列表（Excel + people.json），由内存缓存提供
            names = CACHE.get('names') or []
            self._set_headers(200)
            self.wfile.write(json.dumps(names, ensure_ascii=False).encode('utf-8'))
        else:
            # 静态文件渲染：支持 / 、/index.html 以及项目内其他资源
            if parsed.path in ('/', ''):
                fs_path = self._safe_path('index.html')
            else:
                fs_path = self._safe_path(parsed.path)
            self._serve_file(fs_path)


def _load_excel_names() -> List[str]:
    names: List[str] = []
    # 优先使用 doc/peoples.xls；否则选择 doc 目录下首个 .xls 文件
    candidates: List[str] = []
    preferred = os.path.join(DOC_DIR, 'peoples.xls')
    if os.path.exists(preferred):
        candidates.append(preferred)
    if os.path.isdir(DOC_DIR):
        for f in os.listdir(DOC_DIR):
            if f.lower().endswith('.xls'):
                p = os.path.join(DOC_DIR, f)
                if p not in candidates:
                    candidates.append(p)
    if not candidates or not xlrd:
        return []
    path = candidates[0]
    try:
        wb = xlrd.open_workbook(path)
        sh = wb.sheet_by_index(0)
        # 寻找姓名列
        name_col = 0
        if sh.nrows:
            header = [str(sh.cell_value(0, c)).strip().lower() for c in range(sh.ncols)]
            for i, h in enumerate(header):
                if ('姓名' in h) or ('人物' in h) or ('人名' in h) or ('name' in h):
                    name_col = i
                    break
        # 读取非空姓名
        for r in range(1, sh.nrows):
            val = sh.cell_value(r, name_col)
            if isinstance(val, str) and val.strip():
                names.append(val.strip())
    except Exception:
        return []
    # 去重
    seen = set()
    uniq = []
    for n in names:
        low = n.lower()
        if low in seen:
            continue
        seen.add(low)
        uniq.append(n)
    return uniq


def preload_cache():
    # 预加载 people.json
    people_data = read_people_json()
    CACHE['people'] = people_data if (people_data and not is_empty(people_data)) else FALLBACK
    # 预加载 Excel 名单
    excel_names = _load_excel_names()
    # 合并 people.json 的人名
    json_names = []
    try:
        json_names = [p.get('name') for p in (CACHE['people'] or {}).get('persons', []) if p.get('name')]
    except Exception:
        json_names = []
    merged = []
    seen = set()
    for n in (excel_names + json_names):
        if not n:
            continue
        low = str(n).lower()
        if low in seen:
            continue
        seen.add(low)
        merged.append(n)
    CACHE['names'] = merged
    with CACHE_LOCK:
        CACHE['dirty'] = False


def _save_people_json_atomic(data: Dict[str, Any]):
    # 原子写入 people.json：先写临时文件再替换
    path = os.path.join(ROOT, 'people.json')
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        # 写入失败时尽量清理临时文件
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _periodic_flush(interval_sec: int = 30):
    # 后台线程：定期将内存中的 people 写入到 people.json
    while True:
        time.sleep(interval_sec)
        try:
            with CACHE_LOCK:
                if not CACHE.get('dirty'):
                    continue
                people = CACHE.get('people') or FALLBACK
                data = people if isinstance(people, dict) else { 'persons': [] }
                # 重置脏标记，避免频繁写入；失败则在下次循环重试
                CACHE['dirty'] = False
            _save_people_json_atomic(data)
        except Exception:
            # 若失败，不抛出，下一次循环继续尝试
            pass


def run(server_class=HTTPServer, handler_class=Handler):
    port = int(os.environ.get('PORT', '8001'))
    server_address = ('', port)
    try:
        # 启动前预加载数据到内存
        preload_cache()
        httpd = server_class(server_address, handler_class)
        # 启动后台定时落盘线程（守护线程）
        t = threading.Thread(target=_periodic_flush, kwargs={'interval_sec': 30}, daemon=True)
        t.start()
        print(f"API server listening on http://localhost:{port}/api/people")
        httpd.serve_forever()
    except Exception as e:
        # 显式打印错误，便于诊断启动失败
        print("Failed to start API server:", repr(e))


if __name__ == '__main__':
    run()
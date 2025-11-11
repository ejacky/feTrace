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
import logging
from urllib.parse import urlparse
from typing import Dict, Any
import config
import routes
from cache import Cache

ROOT = os.path.dirname(__file__)  # 项目根目录
# 文档目录优先使用 docs，否则回退为 doc（兼容旧结构）
DATA_DIR = os.path.join(ROOT, 'data') if os.path.isdir(os.path.join(ROOT, 'data')) else os.path.join(ROOT, 'doc')

PROJ_ROOT = os.path.dirname(ROOT)
# 模块级缓存对象（封装）
CACHE_OBJ = Cache()

# 内存缓存
CACHE: Dict[str, Any] = {
    'people': None,      # 完整 people 数据（dict，含 persons）
    'names': [],         # 合并后的姓名列表（excel + people.json）
    'dirty': False,      # 是否有待落盘的变更
}

CACHE_LOCK = threading.Lock()


def read_people_json():
    path = os.path.join(ROOT, 'data', 'people.json')
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
    # 静态资源根目录改为项目根目录，默认渲染 frontend/index.html
    ROOT = os.path.dirname(os.path.dirname(__file__))
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
        rel = url_path.lstrip('/') or 'frontend/index.html'
        fs_path = os.path.normpath(os.path.join(PROJ_ROOT, rel))
        if not fs_path.startswith(PROJ_ROOT):
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
        if parsed.path == '/api/person':
            routes.handle_person(self, CACHE_OBJ, FALLBACK, logger=logger)
        elif parsed.path == '/api/names':
            routes.handle_names(self, CACHE_OBJ)
        elif parsed.path == '/api/people':
            routes.handle_people(self, CACHE_OBJ, FALLBACK)
        else:
            # 静态文件渲染：支持 / 、/index.html 以及项目内其他资源
            if parsed.path in ('/', ''):
                fs_path = self._safe_path('index.html')
            else:
                fs_path = self._safe_path(parsed.path)
            self._serve_file(fs_path)


def preload_cache():
    # 封装后的缓存预加载（people 与 names）
    CACHE_OBJ.preload(ROOT, DATA_DIR, FALLBACK)

def _start_flush_background():
    # 使用封装的缓存对象启动后台周期落盘线程
    CACHE_OBJ.start_flush_thread(interval_sec=config.get_flush_interval_sec(), logger=logger)


def run(server_class=HTTPServer, handler_class=Handler):
    # 日志配置
    global logger
    logger = logging.getLogger('api')
    if not logger.handlers:
        _h = logging.StreamHandler()
        _h.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] api: %(message)s'))
        logger.addHandler(_h)
    logger.setLevel(logging.INFO)

    port = config.get_port()
    server_address = ('', port)
    try:
        # 启动前预加载数据到内存
        preload_cache()
        httpd = server_class(server_address, handler_class)
        # 启动后台定时落盘（封装线程）
        _start_flush_background()
        logger.info("API server listening on http://localhost:%s/api/people", port)
        httpd.serve_forever()
    except Exception as e:
        # 显式打印错误，便于诊断启动失败
        logger.error("Failed to start API server: %s", repr(e))


if __name__ == '__main__':
    run()
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
from urllib.parse import urlparse


def read_people_json():
    path = os.path.join(os.path.dirname(__file__), 'people.json')
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
    def _set_headers(self, code=200, content_type='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        # CORS 允许跨端口访问
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        # 处理预检请求
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/people':
            data = read_people_json()
            if not data or is_empty(data):
                payload = FALLBACK
            else:
                payload = data
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}, ensure_ascii=False).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=Handler):
    port = int(os.environ.get('PORT', '8001'))
    server_address = ('', port)
    try:
        httpd = server_class(server_address, handler_class)
        print(f"API server listening on http://localhost:{port}/api/people")
        httpd.serve_forever()
    except Exception as e:
        # 显式打印错误，便于诊断启动失败
        print("Failed to start API server:", repr(e))


if __name__ == '__main__':
    run()
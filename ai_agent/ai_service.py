"""
AI Agent Service - 提供人物时间线数据的 HTTP 服务
基于原始的 deepseek.py 实现，增加 REST API 接口
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 将 parent 目录添加到路径，以便导入 backend 中的模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from deepseek import get_person_timeline as original_get_person_timeline
    HAS_DEEPEEK_MODULE = True
except ImportError:
    HAS_DEEPEEK_MODULE = False
    logger = logging.getLogger(__name__)
    logger.error("无法导入 deepseek 模块，请确保 backend/deepseek.py 文件存在")

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ai_service')

def mock_get_person_timeline(name: str) -> Dict[str, Any]:
    """当 DeepSeek 模块不可用时，提供模拟数据。"""
    logger.warning(f"DeepSeek 模块不可用，返回模拟数据")
    return {
        "name": name,
        "style": {
            "markerColor": "#e91e63",
            "lineColor": "#f06292"
        },
        "events": [
            {
                "year": 1900,
                "age": 0,
                "place": "Beijing, China",
                "lat": 39.9042,
                "lon": 116.4074,
                "title": f"出生",
                "detail": f"{name} 在北京出生"
            },
            {
                "year": 1920,
                "age": 20,
                "place": "Shanghai, China",
                "lat": 31.2304,
                "lon": 121.4737,
                "title": f"求学",
                "detail": f"{name} 在上海学习"
            }
        ]
    }

def get_person_timeline(name: str) -> Dict[str, Any]:
    """调用原始 deepseek 模块获取时间线数据。"""
    if not HAS_DEEPEEK_MODULE:
        return mock_get_person_timeline(name)
    
    try:
        result = original_get_person_timeline(name)
        logger.info(f"Successfully retrieved timeline data for {name}")
        return result
    except Exception as e:
        logger.error(f"Failed to get person data for {name}: {e}")
        return {
            "name": name,
            "error": f"Failed to fetch data: {str(e)}"
        }

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点。"""
    return jsonify({
        "status": "healthy",
        "service": "ai_agent",
        "deepseek_available": HAS_DEEPEEK_MODULE
    })

@app.route('/api/timeline', methods=['GET', 'OPTIONS'])
def get_timeline():
    """
    获取人物时间线数据
    
    Query 参数:
    - name: 人物姓名 (必填)
    
    返回格式:
    {
        "name": "人物名",
        "style": {
            "markerColor": "#e91e63",
            "lineColor": "#f06292"
        },
        "events": [
            {
                "year": 1900,
                "age": 0,
                "place": "Beijing, China",
                "lat": 39.9042,
                "lon": 116.4074,
                "title": "出生",
                "detail": "在北京出生"
            }
        ]
    }
    """
    try:
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response, 200

        name = request.args.get('name')
        if not name:
            return jsonify({
                "error": "Missing required parameter: name"
            }), 400

        logger.info(f"Received timeline request for: {name}")
        result = get_person_timeline(name.strip())
        
        # Enable CORS for actual request
        response = jsonify(result)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response

    except Exception as e:
        logger.error(f"Error processing timeline request: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/api/batch-timeline', methods=['POST'])
def batch_timeline():
    """
    批量获取多个人的时间线数据
    
    请求体:
    {
        "names": ["人物1", "人物2", ...]
    }
    
    返回格式:
    {
        "results": [
            { "name": "人物1", ...timeline_data... },
            { "name": "人物2", "error": "..." ... }
        ]
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                "error": "Request body must be JSON"
            }), 400

        data = request.get_json()
        names = data.get('names', [])
        
        if not names or not isinstance(names, list):
            return jsonify({
                "error": "Invalid or missing names array"
            }), 400

        if len(names) > 10:  # 限制批量请求数量
            return jsonify({
                "error": "Too many names, maximum 10 allowed"
            }), 400

        logger.info(f"Received batch timeline request for {len(names)} names")
        
        results = []
        for name in names:
            result = get_person_timeline(name)
            results.append(result)

        return jsonify({"results": results})

    except Exception as e:
        logger.error(f"Error processing batch timeline request: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """处理 404 错误。"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested URL was not found on the server."
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """处理 500 错误。"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred on the server."
    }), 500

if __name__ == '__main__':
    # 获取服务端口
    port = int(os.environ.get('AI_AGENT_PORT', 8002))
    host = os.environ.get('AI_AGENT_HOST', '0.0.0.0')
    debug = os.environ.get('AI_AGENT_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting AI Agent Service on {host}:{port}")
    logger.info(f"DeepSeek module available: {HAS_DEEPEEK_MODULE}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)
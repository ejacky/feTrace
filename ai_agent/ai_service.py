"""
AI Agent Service - 提供人物时间线数据的 HTTP 服务
支持 DeepSeek 和 Kimi (Moonshot) 两种 AI 提供商，可通过配置切换
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

# AI 提供商配置
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'kimi').lower()  # 默认使用 kimi

# 导入两个 AI 提供商模块
try:
    from deepseek import get_person_timeline as deepseek_timeline
    HAS_DEEPEEK_MODULE = True
except ImportError:
    HAS_DEEPEEK_MODULE = False
    deepseek_timeline = None

try:
    from kimi import get_person_timeline as kimi_timeline
    HAS_KIMI_MODULE = True
except ImportError:
    HAS_KIMI_MODULE = False
    kimi_timeline = None

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ai_service')

def mock_get_person_timeline(name: str, provider: str = "unknown") -> Dict[str, Any]:
    """当 AI 模块不可用时，提供模拟数据。"""
    logger.warning(f"{provider} 模块不可用，返回模拟数据")
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
    """根据配置的 AI 提供商获取时间线数据，默认使用 Kimi。"""
    global AI_PROVIDER
    
    logger.info(f"使用 AI 提供商: {AI_PROVIDER}")
    
    if AI_PROVIDER == "kimi":
        if not HAS_KIMI_MODULE or not kimi_timeline:
            return mock_get_person_timeline(name, "Kimi")
        try:
            result = kimi_timeline(name)
            logger.info(f"成功从 Kimi 获取时间线数据: {name}")
            return result
        except Exception as e:
            logger.error(f"Kimi 获取数据失败 {name}: {e}")
            return {"name": name, "error": f"Failed to fetch data from Kimi: {str(e)}"}
            
    elif AI_PROVIDER == "deepseek":
        if not HAS_DEEPEEK_MODULE or not deepseek_timeline:
            return mock_get_person_timeline(name, "DeepSeek")
        try:
            result = deepseek_timeline(name)
            logger.info(f"成功从 DeepSeek 获取时间线数据: {name}")
            return result
        except Exception as e:
            logger.error(f"DeepSeek 获取数据失败 {name}: {e}")
            return {"name": name, "error": f"Failed to fetch data from DeepSeek: {str(e)}"}
    else:
        logger.error(f"未知的 AI 提供商: {AI_PROVIDER}")
        return mock_get_person_timeline(name, "Unknown")

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点。"""
    return jsonify({
        "status": "healthy",
        "service": "ai_agent",
        "ai_provider": AI_PROVIDER,
        "providers_available": {
            "kimi": HAS_KIMI_MODULE,
            "deepseek": HAS_DEEPEEK_MODULE
        }
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
    logger.info(f"AI Provider: {AI_PROVIDER}")
    logger.info(f"Kimi module available: {HAS_KIMI_MODULE}")
    logger.info(f"DeepSeek module available: {HAS_DEEPEEK_MODULE}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)
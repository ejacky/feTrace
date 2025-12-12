# AI Agent Service - Python AI Service for Timeline Data

This service provides a RESTful HTTP wrapper around the original Python DeepSeek implementation, allowing cross-language communication with the Go backend.

## 🚀 Features

- **RESTful API**: HTTP endpoints for timeline data retrieval
- **Cross-language support**: Python AI service accessible from any language
- **Health monitoring**: Built-in health checks and monitoring
- **Bulk operations**: Support for batch timeline requests
- **Automatic fallback**: Mock data when DeepSeek service is unavailable
- **Containerized**: Docker support for easy deployment
- **CORS enabled**: Cross-origin resource sharing support

## 📋 API Endpoints

### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "ai_agent",
  "deepseek_available": true
}
```

### Get Timeline Data
```
GET /api/timeline?name=人物名
```

Response:
```json
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
```

### Batch Timeline Request
```
POST /api/batch-timeline
Content-Type: application/json

{
  "names": ["人物1", "人物2", "人物3"]
}
```

## 🛠 Installation

### Prerequisites
- Python 3.9+
- pip package manager

### Direct Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env

# Edit configuration
vim .env
```

### Docker Installation
```bash
# Build and run with docker-compose
docker-compose up -d
```

## ⚙ Configuration

Environment variables:

```bash
# Service Configuration
AI_AGENT_PORT=8002
AI_AGENT_HOST=0.0.0.0
AI_AGENT_DEBUG=False

# DeepSeek API
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_CONNECT_TIMEOUT=15
DEEPSEEK_READ_TIMEOUT=40

# Geocoding
GEOCODE_ENABLED=True
GEOCODE_MAX_CALLS=3
```

## 🚀 Usage

### Direct Run
```bash
# Start the service
python ai_service.py

# Test the API
curl -X GET "http://localhost:8002/api/timeline?name=苏轼"
```

### Docker Run
```bash
# Start with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 💡 Integration with Go Backend

The Go backend automatically detects and uses the AI Agent service when configured:

1. **Set environment variables in Go backend:**
   ```bash
   export USE_AI_AGENT_SERVICE=true
   export AI_AGENT_SERVICE_URL=http://localhost:8002
   ```

2. **Or update config file:**
   ```json
   {
     "USE_AI_AGENT_SERVICE": true,
     "AI_AGENT_SERVICE_URL": "http://localhost:8002"
   }
   ```

3. **The Go backend will use AI Agent service instead of direct DeepSeek API calls**

## 🔄 Service Architecture

```
Frontend (Browser)
       ↓
Go Backend (Go HTTP Server)
       ↓  (HTTP)
AI Agent Service (Python Flask)
       ↓  (Python module)
Original DeepSeek Implementation
       ↓  (HTTPS)
DeepSeek API
```

## 🎯 Benefits

1. **Maintain Python expertise**: Keep complex DeepSeek logic in Python
2. **Cross-language compatibility**: Any language can call the Python service
3. **Service isolation**: AI operations run in separate process
4. **Better debugging**: Dedicated Python logging and error handling
5. **Containerization**: Easy deployment and scaling
6. **Health monitoring**: Built-in service health checks

## 📊 Performance

- **Fast responses**: Local HTTP calls instead of external API
- **Batch processing**: Support for multiple requests in one call
- **Connection pooling**: Efficient HTTP client implementation
- **Caching**: Can be integrated with Go backend caching layer

## 🛡 Security

- **CORS configuration**: Flexible cross-origin settings
- **Input validation**: Proper request parameter validation
- **Error handling**: Secure error messages without sensitive data
- **Container isolation**: Docker container for service isolation

## 🐛 Troubleshooting

### Common Issues

1. **Module Not Found**
   ```bash
   # Ensure backend/deepseek.py exists
   ls ../backend/deepseek.py
   ```

2. **Port Already in Use**
   ```bash
   # Check if port 8002 is already used
   netstat -tulnp | grep 8002
   ```

3. **DeepSeek API Key Missing**
   ```bash
   # Set the API key in .env file
   echo "DEEPSEEK_API_KEY=your-key-here" >> .env
   ```

### Logs
Check logs for detailed error information:
```bash
# Direct run
tail -f ai_agent.log  # if log file configured

# Docker
docker-compose logs -f ai-agent
```

## 🔗 Related Services

- **Go Backend**: `/backend_go/main.go` - Main application server
- **Original DeepSeek**: `/backend/deepseek.py` - Original Python implementation
- **Configuration**: Both services support cross-configuration for seamless integration
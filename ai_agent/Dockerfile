FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/ ../backend/

# 复制 AI agent 代码
COPY ai_agent/ ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建非 root 用户
RUN useradd -m -u 1000 aiservice && chown -R aiservice:aiservice /app
USER aiservice

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["python", "ai_service.py"]
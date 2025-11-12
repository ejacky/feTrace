# 基础镜像
FROM python:3.11-slim

# 工作目录
WORKDIR /app

# 复制项目（保留必要文件）
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY requirements.txt ./requirements.txt

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露后端端口（默认 8001）
EXPOSE 8001

# 启动后端服务（托管静态 + API）
CMD ["python", "backend/index.py"]
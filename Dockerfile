FROM m.daocloud.io/docker.io/library/python:3.11-slim

WORKDIR /app

COPY backend/ .

# 提高超时并切换镜像源（可选：阿里、清华，二选一）
ENV PIP_DEFAULT_TIMEOUT=120
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 如你更偏向阿里镜像，可改为：
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

# 安装依赖，带超时参数（双保险）
RUN pip install --no-cache-dir -r requirements.txt --timeout 120

EXPOSE 8001
CMD ["python", "index.py"]
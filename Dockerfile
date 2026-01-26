FROM python:3.11-slim-bookworm

# 安装系统依赖（Playwright需要）
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 复制应用文件
COPY run.py .
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/
# 创建 token_flow_graphs 目录（确保存在）
RUN mkdir -p ./token_flow_graphs
# 复制 Token Flow Graph 文件（如果存在）
# 注意：如果源目录不存在，构建会失败
# 解决方案：确保 token_flow_graphs 目录存在（即使是空的）
COPY token_flow_graphs/ ./token_flow_graphs/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 5001

# 设置环境变量
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["python3", "run.py"]

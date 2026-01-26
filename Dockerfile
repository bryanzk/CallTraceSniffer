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
# 解决方案：在项目根目录运行: mkdir -p token_flow_graphs（即使是空目录）
# 使用通配符匹配，如果目录不存在则跳过（需要先创建空目录）
COPY token_flow_graphs ./token_flow_graphs/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 5001

# 设置环境变量
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 启动命令
# 优先使用 gunicorn（生产环境），如果失败则回退到 Flask 开发服务器
# Railway 会自动设置 PORT 环境变量
CMD sh -c 'if command -v gunicorn > /dev/null 2>&1; then \
    gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --threads 2 --timeout 300 --access-logfile - --error-logfile - --log-level info "run:app"; \
else \
    python3 run.py; \
fi'

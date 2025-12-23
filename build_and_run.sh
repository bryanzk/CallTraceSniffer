#!/bin/bash
# Docker构建和运行脚本

set -e

echo "🔨 BlockSec分析工具 - Docker部署"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 未找到Docker，请先安装Docker"
    echo "   安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "⚠️  未找到docker-compose，将使用docker build和docker run"
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# 停止并删除旧容器（如果存在）
echo "清理旧容器..."
docker stop blocksec-analyzer 2>/dev/null || true
docker rm blocksec-analyzer 2>/dev/null || true

# 构建镜像
echo ""
echo "🔨 构建Docker镜像..."
if [ "$USE_COMPOSE" = true ]; then
    docker-compose build || docker compose build
else
    docker build -t blocksec-analyzer:latest .
fi

# 启动容器
echo ""
echo "🚀 启动容器..."
if [ "$USE_COMPOSE" = true ]; then
    docker-compose up -d || docker compose up -d
else
    docker run -d \
        --name blocksec-analyzer \
        -p 5001:5001 \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/logs:/app/logs" \
        --restart unless-stopped \
        blocksec-analyzer:latest
fi

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if docker ps | grep -q blocksec-analyzer; then
    echo ""
    echo "✅ 应用已成功启动！"
    echo ""
    echo "📊 服务信息:"
    echo "   访问地址: http://localhost:5001"
    echo "   容器名称: blocksec-analyzer"
    echo ""
    echo "📝 常用命令:"
    echo "   查看日志: docker logs -f blocksec-analyzer"
    echo "   停止服务: docker stop blocksec-analyzer"
    echo "   启动服务: docker start blocksec-analyzer"
    echo "   删除容器: docker rm -f blocksec-analyzer"
    if [ "$USE_COMPOSE" = true ]; then
        echo "   使用Compose停止: docker-compose down"
    fi
else
    echo "❌ 容器启动失败，查看日志:"
    docker logs blocksec-analyzer
    exit 1
fi


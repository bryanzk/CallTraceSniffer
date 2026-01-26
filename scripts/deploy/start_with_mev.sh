#!/bin/bash
# 启动 Web 服务（包含 MEV Block Viewer）

set -e

echo "🚀 启动 CallTraceSniffer Web 服务（包含 MEV Block Viewer）..."
echo ""

# 检查是否在项目根目录
if [ ! -f "run.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查 token_flow_graphs 目录
if [ ! -d "token_flow_graphs" ]; then
    echo "⚠️  警告: token_flow_graphs 目录不存在，MEV Block Viewer 功能将不可用"
    echo "   可以稍后添加区块分析数据"
fi

# 启动 Flask 应用
echo "📡 启动 Flask 应用..."
echo "   访问地址: http://localhost:5001"
echo "   MEV 区块查看器:"
echo "     - http://localhost:5001/mev/block/24274722"
echo "     - http://localhost:5001/mev/block/24279007"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

python3 run.py

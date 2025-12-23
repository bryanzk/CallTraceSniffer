#!/bin/bash
# 启动Web应用的脚本

echo "🚀 启动 BlockSec 交易分析工具 Web界面"
echo ""

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "✓ 发现虚拟环境，激活中..."
    source venv/bin/activate
else
    echo "⚠️  未发现虚拟环境，使用系统Python"
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import flask" 2>/dev/null || {
    echo "❌ Flask未安装，正在安装..."
    pip install Flask==3.0.0
}

python3 -c "import playwright" 2>/dev/null || {
    echo "❌ Playwright未安装，正在安装..."
    pip install playwright==1.40.0
    playwright install chromium
}

echo ""
echo "✓ 依赖检查完成"
echo ""
echo "🌐 启动Web服务器..."
echo "   访问地址: http://localhost:5001"
echo "   注意: 如果5001端口被占用，请修改app.py中的端口号"
echo "   按 Ctrl+C 停止服务器"
echo ""

python3 run.py


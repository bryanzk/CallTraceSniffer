#!/bin/bash
# 测试运行脚本

set -e

echo "🧪 运行单元测试"
echo ""

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  建议在虚拟环境中运行测试"
    echo "   运行: source venv/bin/activate"
    echo ""
fi

# 检查pytest是否安装
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest未安装"
    echo "   运行: pip install -r requirements.txt"
    exit 1
fi

# 运行测试
echo "运行所有测试..."
pytest "$@"

# 如果提供了--cov参数，显示覆盖率报告
if [[ "$*" == *"--cov"* ]]; then
    echo ""
    echo "📊 覆盖率报告已生成"
    echo "   查看HTML报告: open htmlcov/index.html"
fi


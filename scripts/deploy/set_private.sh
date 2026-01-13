#!/bin/bash
# 将GitHub仓库设置为私有的脚本

set -e

REPO="bryanzk/CallTraceSniffer"

echo "🔒 将GitHub仓库设置为私有"
echo ""
echo "仓库: $REPO"
echo ""

# 检查是否安装了GitHub CLI
if command -v gh &> /dev/null; then
    echo "✓ 检测到GitHub CLI"
    echo ""
    
    # 检查是否已登录
    if gh auth status &> /dev/null; then
        echo "✓ GitHub CLI已登录"
        echo ""
        read -p "是否使用GitHub CLI将仓库设为私有? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "正在设置..."
            gh repo edit "$REPO" --visibility private --accept-visibility-change-consequences
            echo ""
            echo "✅ 仓库已设置为私有！"
            echo ""
            echo "验证: 访问 https://github.com/$REPO"
            echo "如果看到登录提示，说明设置成功"
            exit 0
        fi
    else
        echo "⚠️  GitHub CLI未登录"
        echo "运行 'gh auth login' 登录"
    fi
fi

echo ""
echo "📝 请通过GitHub网页界面设置："
echo ""
echo "1. 访问: https://github.com/$REPO/settings"
echo "2. 滚动到 'Danger Zone'"
echo "3. 点击 'Change visibility'"
echo "4. 选择 'Make private'"
echo "5. 确认操作"
echo ""
echo "详细说明请查看: SET_PRIVATE_REPO.md"


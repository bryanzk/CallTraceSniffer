#!/bin/bash
# GitHub推送脚本

set -e

echo "🚀 准备推送到GitHub"
echo ""

# 检查是否已设置远程仓库
if git remote | grep -q origin; then
    echo "✓ 远程仓库已配置:"
    git remote -v
    echo ""
    read -p "是否使用现有远程仓库? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "请先运行: git remote remove origin"
        exit 1
    fi
else
    echo "⚠️  未配置远程仓库"
    echo ""
    echo "请选择推送方式:"
    echo "1) HTTPS (需要Personal Access Token)"
    echo "2) SSH (需要配置SSH key)"
    echo ""
    read -p "请选择 (1/2): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[1]$ ]]; then
        read -p "请输入GitHub用户名: " GITHUB_USER
        read -p "请输入仓库名称 (默认: CallTraceSniffer): " REPO_NAME
        REPO_NAME=${REPO_NAME:-CallTraceSniffer}
        git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
        echo "✓ 已添加HTTPS远程仓库"
    elif [[ $REPLY =~ ^[2]$ ]]; then
        read -p "请输入GitHub用户名: " GITHUB_USER
        read -p "请输入仓库名称 (默认: CallTraceSniffer): " REPO_NAME
        REPO_NAME=${REPO_NAME:-CallTraceSniffer}
        git remote add origin "git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
        echo "✓ 已添加SSH远程仓库"
    else
        echo "❌ 无效选择"
        exit 1
    fi
fi

# 确保分支名为main
git branch -M main 2>/dev/null || true

# 推送
echo ""
echo "📤 推送到GitHub..."
git push -u origin main

echo ""
echo "✅ 推送成功！"
echo ""
echo "🌐 您的仓库地址:"
git remote get-url origin



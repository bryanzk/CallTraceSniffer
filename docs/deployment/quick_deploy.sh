#!/bin/bash
# 快速部署脚本示例
# 用于快速配置远程访问

set -e

echo "=========================================="
echo "CallTraceSniffer 远程访问快速部署"
echo "=========================================="
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "不支持的操作系统: $OSTYPE"
    exit 1
fi

# 获取本机 IP
if [ "$OS" == "linux" ]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
elif [ "$OS" == "macos" ]; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")
fi

echo "检测到本机 IP: $LOCAL_IP"
echo ""

# 选择部署方式
echo "请选择部署方式:"
echo "1) Docker Compose (推荐)"
echo "2) 直接运行 Python"
echo "3) 使用 Nginx 反向代理"
echo "4) 使用 ngrok 内网穿透"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "使用 Docker Compose 部署..."
        if ! command -v docker &> /dev/null; then
            echo "错误: 未安装 Docker"
            exit 1
        fi
        if ! command -v docker-compose &> /dev/null; then
            echo "错误: 未安装 Docker Compose"
            exit 1
        fi
        
        echo "启动服务..."
        docker-compose up -d
        
        echo ""
        echo "✅ 服务已启动！"
        echo "访问地址:"
        echo "  - Web UI: http://$LOCAL_IP:5001"
        echo "  - API: http://$LOCAL_IP:5001/api/analyze"
        echo ""
        echo "查看日志: docker-compose logs -f"
        echo "停止服务: docker-compose down"
        ;;
        
    2)
        echo ""
        echo "直接运行 Python..."
        if ! command -v python3 &> /dev/null; then
            echo "错误: 未安装 Python 3"
            exit 1
        fi
        
        # 检查虚拟环境
        if [ ! -d "venv" ]; then
            echo "创建虚拟环境..."
            python3 -m venv venv
        fi
        
        echo "激活虚拟环境并安装依赖..."
        source venv/bin/activate
        pip install -r requirements.txt --quiet
        
        echo ""
        echo "✅ 准备完成！"
        echo "运行以下命令启动服务:"
        echo "  source venv/bin/activate"
        echo "  python run.py"
        echo ""
        echo "访问地址:"
        echo "  - Web UI: http://$LOCAL_IP:5001"
        echo "  - API: http://$LOCAL_IP:5001/api/analyze"
        ;;
        
    3)
        echo ""
        echo "配置 Nginx 反向代理..."
        
        if ! command -v nginx &> /dev/null; then
            echo "错误: 未安装 Nginx"
            echo "安装 Nginx:"
            if [ "$OS" == "linux" ]; then
                echo "  sudo apt update && sudo apt install nginx"
            elif [ "$OS" == "macos" ]; then
                echo "  brew install nginx"
            fi
            exit 1
        fi
        
        read -p "请输入域名或 IP (直接回车使用 $LOCAL_IP): " domain
        domain=${domain:-$LOCAL_IP}
        
        # 复制配置文件
        CONFIG_FILE="/etc/nginx/sites-available/calltrace"
        if [ -f "docs/deployment/nginx.conf.example" ]; then
            echo "创建 Nginx 配置..."
            sudo cp docs/deployment/nginx.conf.example "$CONFIG_FILE"
            sudo sed -i "s/your-domain.com/$domain/g" "$CONFIG_FILE"
            
            # 创建符号链接
            sudo ln -sf "$CONFIG_FILE" /etc/nginx/sites-enabled/calltrace
            
            # 测试配置
            echo "测试 Nginx 配置..."
            sudo nginx -t
            
            if [ $? -eq 0 ]; then
                echo "重启 Nginx..."
                sudo systemctl restart nginx 2>/dev/null || sudo service nginx restart 2>/dev/null
                
                echo ""
                echo "✅ Nginx 配置完成！"
                echo "访问地址:"
                echo "  - Web UI: http://$domain"
                echo "  - API: http://$domain/api/analyze"
                echo ""
                echo "注意: 确保 Flask 服务正在运行 (端口 5001)"
            else
                echo "❌ Nginx 配置有误，请检查"
            fi
        else
            echo "错误: 找不到 nginx.conf.example 文件"
            exit 1
        fi
        ;;
        
    4)
        echo ""
        echo "使用 ngrok 内网穿透..."
        
        if ! command -v ngrok &> /dev/null; then
            echo "错误: 未安装 ngrok"
            echo "安装 ngrok:"
            if [ "$OS" == "linux" ]; then
                echo "  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
                echo "  tar xvzf ngrok-v3-stable-linux-amd64.tgz"
                echo "  sudo mv ngrok /usr/local/bin/"
            elif [ "$OS" == "macos" ]; then
                echo "  brew install ngrok/ngrok/ngrok"
            fi
            exit 1
        fi
        
        read -p "请输入 ngrok authtoken (如果已配置可跳过): " authtoken
        if [ ! -z "$authtoken" ]; then
            ngrok config add-authtoken "$authtoken"
        fi
        
        echo ""
        echo "✅ 准备完成！"
        echo "请按以下步骤操作:"
        echo "1. 在另一个终端启动 Flask 服务:"
        echo "   python run.py"
        echo ""
        echo "2. 然后运行:"
        echo "   ngrok http 5001"
        echo ""
        echo "3. ngrok 会显示一个公网地址，分享给同事即可"
        ;;
        
    *)
        echo "无效的选项"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "更多部署选项请查看: docs/deployment/REMOTE_ACCESS_OPTIONS.md"

# 远程访问部署选项

本文档介绍如何让同事远程访问 CallTraceSniffer 服务的多种部署方式，支持 Web UI 和 API 调用两种访问方式。

## 目录

1. [快速概览](#快速概览)
2. [方式一：本地部署 + 端口映射](#方式一本地部署--端口映射)
3. [方式二：Docker 部署（推荐）](#方式二docker-部署推荐)
4. [方式三：云服务器部署](#方式三云服务器部署)
5. [方式四：Nginx 反向代理](#方式四nginx-反向代理)
6. [方式五：内网穿透工具](#方式五内网穿透工具)
7. [方式六：VPN/内网访问](#方式六vpnn内网访问)
8. [方式七：容器编排平台](#方式七容器编排平台)
9. [安全建议](#安全建议)
10. [API 使用说明](#api-使用说明)

---

## 快速概览

| 部署方式 | 适用场景 | 难度 | 成本 | 推荐度 |
|---------|---------|------|------|--------|
| 本地部署 + 端口映射 | 开发测试 | ⭐ | 免费 | ⭐⭐ |
| Docker 部署 | 快速部署 | ⭐⭐ | 免费 | ⭐⭐⭐⭐⭐ |
| 云服务器部署 | 生产环境 | ⭐⭐⭐ | 付费 | ⭐⭐⭐⭐ |
| Nginx 反向代理 | 生产环境 | ⭐⭐⭐⭐ | 免费/付费 | ⭐⭐⭐⭐⭐ |
| 内网穿透 | 临时访问 | ⭐⭐ | 免费/付费 | ⭐⭐⭐ |
| VPN/内网 | 企业内网 | ⭐⭐⭐ | 免费/付费 | ⭐⭐⭐⭐ |
| 容器编排 | 大规模部署 | ⭐⭐⭐⭐⭐ | 付费 | ⭐⭐⭐ |

---

## 方式一：本地部署 + 端口映射

### 适用场景
- 开发测试环境
- 临时访问需求
- 本地机器有公网 IP

### 步骤

#### 1. 启动服务

```bash
# 方式1：直接运行
python run.py

# 方式2：使用启动脚本
./start_web.sh
```

#### 2. 配置防火墙

**macOS:**
```bash
# 允许 5001 端口入站连接
sudo pfctl -f /etc/pf.conf
```

**Linux:**
```bash
# Ubuntu/Debian
sudo ufw allow 5001/tcp
sudo ufw reload

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

**Windows:**
```powershell
# 在 PowerShell (管理员) 中运行
New-NetFirewallRule -DisplayName "CallTraceSniffer" -Direction Inbound -LocalPort 5001 -Protocol TCP -Action Allow
```

#### 3. 获取服务器 IP 地址

```bash
# Linux/macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# 或使用
hostname -I  # Linux
ipconfig getifaddr en0  # macOS
```

#### 4. 访问服务

- **Web UI**: `http://<服务器IP>:5001`
- **API**: `http://<服务器IP>:5001/api/analyze`

### 优点
- 简单快速
- 无需额外配置

### 缺点
- 需要公网 IP 或内网访问
- 安全性较低
- 不适合生产环境

---

## 方式二：Docker 部署（推荐）

### 适用场景
- 快速部署
- 环境隔离
- 跨平台部署

### 步骤

#### 1. 使用 Docker Compose（推荐）

```bash
# 修改 docker-compose.yml，确保端口映射正确
# 默认已经配置为 5001:5001

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 2. 修改端口映射（如果需要）

编辑 `docker-compose.yml`:

```yaml
services:
  blocksec-analyzer:
    ports:
      - "8080:5001"  # 将本地 8080 映射到容器 5001
```

#### 3. 配置防火墙（同上）

#### 4. 访问服务

- **Web UI**: `http://<服务器IP>:5001` (或你配置的端口)
- **API**: `http://<服务器IP>:5001/api/analyze`

### 优点
- 环境一致
- 易于管理
- 支持快速重启

### 缺点
- 需要 Docker 环境
- 仍需要配置防火墙

---

## 方式三：云服务器部署

### 适用场景
- 生产环境
- 需要稳定访问
- 团队协作

### 支持的云平台

#### 1. 阿里云 / 腾讯云 / AWS / Azure

**步骤：**

1. **创建云服务器实例**
   - 选择 Ubuntu 20.04+ 或 CentOS 7+
   - 至少 2GB 内存，2 核 CPU
   - 配置安全组，开放 5001 端口

2. **SSH 连接到服务器**
   ```bash
   ssh user@your-server-ip
   ```

3. **安装 Docker（如果使用 Docker 部署）**
   ```bash
   # Ubuntu
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # 安装 Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

4. **上传项目文件**
   ```bash
   # 使用 scp
   scp -r /path/to/CallTraceSniffer user@server:/home/user/
   
   # 或使用 git
   git clone <your-repo-url>
   ```

5. **启动服务**
   ```bash
   cd CallTraceSniffer
   docker-compose up -d
   ```

6. **配置安全组规则**
   - 在云平台控制台配置安全组
   - 添加入站规则：端口 5001，协议 TCP，源地址 0.0.0.0/0（或限制特定 IP）

7. **访问服务**
   - **Web UI**: `http://<云服务器公网IP>:5001`
   - **API**: `http://<云服务器公网IP>:5001/api/analyze`

### 优点
- 稳定可靠
- 公网访问
- 易于扩展

### 缺点
- 需要付费
- 需要维护服务器

---

## 方式四：Nginx 反向代理

### 适用场景
- 生产环境
- 需要 HTTPS
- 多服务管理

### 步骤

#### 1. 安装 Nginx

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

#### 2. 配置 Nginx

创建配置文件 `/etc/nginx/sites-available/calltrace`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或使用 IP 地址

    # Web UI 和 API 代理
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API 专用路径（可选）
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 3. 启用配置

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/calltrace /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 4. 配置 HTTPS（可选，推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

#### 5. 访问服务

- **Web UI**: `http://your-domain.com` 或 `https://your-domain.com`
- **API**: `http://your-domain.com/api/analyze`

### 优点
- 支持 HTTPS
- 可以隐藏真实端口
- 支持负载均衡
- 更好的安全性

### 缺点
- 配置较复杂
- 需要域名（HTTPS）

---

## 方式五：内网穿透工具

### 适用场景
- 临时访问
- 开发测试
- 无公网 IP

### 选项 1: ngrok（最简单）

#### 步骤

1. **注册并安装 ngrok**
   ```bash
   # 下载 ngrok
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   tar xvzf ngrok-v3-stable-linux-amd64.tgz
   sudo mv ngrok /usr/local/bin/
   
   # 或使用 Homebrew (macOS)
   brew install ngrok/ngrok/ngrok
   ```

2. **获取 authtoken**
   - 访问 https://dashboard.ngrok.com/get-started/your-authtoken
   - 复制 authtoken

3. **配置 ngrok**
   ```bash
   ngrok config add-authtoken <your-authtoken>
   ```

4. **启动隧道**
   ```bash
   # 启动服务（在另一个终端）
   python run.py
   
   # 启动 ngrok 隧道
   ngrok http 5001
   ```

5. **获取访问地址**
   - ngrok 会显示类似 `https://abc123.ngrok.io` 的地址
   - 分享此地址给同事

#### 访问
- **Web UI**: `https://abc123.ngrok.io`
- **API**: `https://abc123.ngrok.io/api/analyze`

### 选项 2: frp（自建服务器）

#### 步骤

1. **服务器端配置**（需要一台有公网 IP 的服务器）

   下载 frp: https://github.com/fatedier/frp/releases

   `frps.ini`:
   ```ini
   [common]
   bind_port = 7000
   ```

2. **客户端配置**（本地机器）

   `frpc.ini`:
   ```ini
   [common]
   server_addr = your-server-ip
   server_port = 7000

   [calltrace]
   type = tcp
   local_ip = 127.0.0.1
   local_port = 5001
   remote_port = 6000
   ```

3. **启动**
   ```bash
   # 服务器端
   ./frps -c frps.ini
   
   # 客户端
   ./frpc -c frpc.ini
   ```

4. **访问**
   - **Web UI**: `http://your-server-ip:6000`
   - **API**: `http://your-server-ip:6000/api/analyze`

### 选项 3: Cloudflare Tunnel（免费）

#### 步骤

1. **安装 cloudflared**
   ```bash
   # Linux
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   chmod +x cloudflared-linux-amd64
   sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
   ```

2. **创建隧道**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create calltrace
   ```

3. **配置隧道**
   编辑 `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /path/to/credentials.json
   
   ingress:
     - hostname: calltrace.yourdomain.com
       service: http://localhost:5001
     - service: http_status:404
   ```

4. **启动隧道**
   ```bash
   cloudflared tunnel run calltrace
   ```

### 优点
- 无需公网 IP
- 快速部署
- 支持 HTTPS（ngrok, Cloudflare）

### 缺点
- 免费版有限制
- 可能不稳定
- 需要额外服务

---

## 方式六：VPN/内网访问

### 适用场景
- 企业内网
- 需要安全访问
- 已有 VPN 基础设施

### 步骤

#### 1. 配置 VPN 服务器（如果还没有）

可以使用：
- **WireGuard**（推荐，简单快速）
- **OpenVPN**
- **Tailscale**（最简单，基于 WireGuard）

#### 2. Tailscale 示例（最简单）

1. **安装 Tailscale**
   ```bash
   # 服务器端和客户端都安装
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. **登录**
   ```bash
   sudo tailscale up
   ```

3. **获取 Tailscale IP**
   ```bash
   tailscale ip
   ```

4. **访问服务**
   - **Web UI**: `http://<tailscale-ip>:5001`
   - **API**: `http://<tailscale-ip>:5001/api/analyze`

### 优点
- 安全性高
- 稳定可靠
- 适合企业环境

### 缺点
- 需要 VPN 配置
- 所有用户需要加入 VPN

---

## 方式七：容器编排平台

### 适用场景
- 大规模部署
- 需要高可用
- 企业级应用

### 选项 1: Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署服务
docker stack deploy -c docker-compose.yml calltrace
```

### 选项 2: Kubernetes

创建 `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calltrace-sniffer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: calltrace-sniffer
  template:
    metadata:
      labels:
        app: calltrace-sniffer
    spec:
      containers:
      - name: calltrace
        image: blocksec-analyzer:latest
        ports:
        - containerPort: 5001
---
apiVersion: v1
kind: Service
metadata:
  name: calltrace-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5001
  selector:
    app: calltrace-sniffer
```

### 优点
- 高可用
- 自动扩展
- 企业级特性

### 缺点
- 配置复杂
- 需要专业知识
- 资源消耗大

---

## 安全建议

### 1. 使用 HTTPS

- 使用 Nginx + Let's Encrypt
- 或使用内网穿透工具的 HTTPS

### 2. 配置访问控制

#### 使用 Nginx 基础认证

```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:5001;
}
```

创建密码文件：
```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd username
```

#### 使用 IP 白名单

```nginx
location / {
    allow 192.168.1.0/24;  # 允许内网
    allow 10.0.0.0/8;      # 允许特定网段
    deny all;              # 拒绝其他
    proxy_pass http://127.0.0.1:5001;
}
```

### 3. 限制 API 访问频率

在 Flask 应用中添加限流：

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze_tx():
    # ...
```

### 4. 防火墙配置

只开放必要端口：
```bash
# 只允许特定 IP 访问
sudo ufw allow from 192.168.1.0/24 to any port 5001
```

### 5. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新 Docker 镜像
docker-compose pull
docker-compose up -d
```

---

## API 使用说明

### API 端点

#### 1. 分析单个交易

```bash
curl -X POST http://your-server:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
  }'
```

#### 2. 分析模拟交易

```bash
curl -X POST http://your-server:5001/api/analyze-simulation \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_url": "https://blocksec.com/explorer/tx/eth/0x..."
  }'
```

#### 3. 批量分析

```bash
curl -X POST http://your-server:5001/api/analyze-batch \
  -F "file=@tx_hashes.csv"
```

#### 4. 获取 IR V1 JSON

```bash
curl -X POST http://your-server:5001/api/ir_parse \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
  }'
```

#### 5. 下载结果

```bash
curl -X POST http://your-server:5001/api/download-result \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
    "output_type": "ir_v1"
  }' \
  --output result.json
```

### Python 客户端示例

```python
import requests

BASE_URL = "http://your-server:5001"

# 分析交易
response = requests.post(
    f"{BASE_URL}/api/analyze",
    json={"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"}
)
result = response.json()
print(result)
```

### JavaScript 客户端示例

```javascript
const BASE_URL = 'http://your-server:5001';

// 分析交易
async function analyzeTx(txHash) {
  const response = await fetch(`${BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tx_hash: txHash }),
  });
  const result = await response.json();
  return result;
}
```

---

## 推荐方案

### 开发测试环境
- **推荐**: Docker 部署 + ngrok 内网穿透
- **原因**: 快速、简单、无需公网 IP

### 生产环境
- **推荐**: 云服务器 + Docker + Nginx + HTTPS
- **原因**: 稳定、安全、可扩展

### 企业内网
- **推荐**: VPN + Docker 部署
- **原因**: 安全、稳定、符合企业规范

---

## 故障排除

### 问题 1: 无法访问服务

1. **检查服务是否运行**
   ```bash
   # Docker
   docker ps
   docker-compose ps
   
   # 直接运行
   ps aux | grep python
   ```

2. **检查端口是否监听**
   ```bash
   netstat -tuln | grep 5001
   # 或
   lsof -i :5001
   ```

3. **检查防火墙**
   ```bash
   sudo ufw status
   ```

### 问题 2: API 返回错误

1. **查看日志**
   ```bash
   # Docker
   docker logs blocksec-analyzer
   
   # 直接运行
   tail -f logs/app.log
   ```

2. **检查请求格式**
   - 确保使用 POST 方法
   - 确保 Content-Type 为 application/json
   - 确保 tx_hash 格式正确（0x 开头，66 字符）

### 问题 3: 性能问题

1. **增加资源限制**
   ```yaml
   # docker-compose.yml
   services:
     blocksec-analyzer:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
   ```

2. **使用负载均衡**
   - 部署多个实例
   - 使用 Nginx 负载均衡

---

## 总结

根据你的具体需求选择合适的部署方式：

- **快速测试**: ngrok
- **简单部署**: Docker Compose
- **生产环境**: 云服务器 + Nginx + HTTPS
- **企业内网**: VPN + Docker
- **大规模**: Kubernetes

如有问题，请查看项目文档或提交 Issue。

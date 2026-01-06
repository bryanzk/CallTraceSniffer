# 免费云平台部署指南

本文档介绍如何在免费云平台上部署 CallTraceSniffer 服务，包括 Vercel、Cloudflare 以及其他支持 Playwright 的免费平台。

## ⚠️ 重要限制说明

**关键问题：Playwright 浏览器自动化**

本项目使用了 **Playwright** 来抓取 BlockSec 页面的数据，这需要：
- 完整的浏览器二进制文件（Chromium）
- 系统级依赖（libasound2, libatk, 等）
- 较长的执行时间（可能超过 serverless 函数的超时限制）

这些要求在传统的 serverless 平台（如 Vercel、Cloudflare Workers）上**很难满足**。

---

## 平台对比

| 平台 | Python 支持 | Playwright 支持 | 免费额度 | 推荐度 | 说明 |
|------|-----------|----------------|---------|--------|------|
| **Vercel** | ✅ 有限 | ❌ 困难 | 100GB/月 | ⭐⭐ | 需要特殊配置 |
| **Cloudflare Workers** | ❌ 不支持 | ❌ 不支持 | 10万请求/月 | ⭐ | 仅支持 JS/TS |
| **Cloudflare Tunnel** | ✅ | ✅ | 免费 | ⭐⭐⭐⭐ | 需要本地运行 |
| **Railway** | ✅ | ✅ | $5/月免费额度 | ⭐⭐⭐⭐⭐ | 最佳选择 |
| **Render** | ✅ | ✅ | 免费（有限制） | ⭐⭐⭐⭐ | 需要定期唤醒 |
| **Fly.io** | ✅ | ✅ | 免费（有限制） | ⭐⭐⭐⭐ | 需要信用卡 |
| **Replit** | ✅ | ✅ | 免费 | ⭐⭐⭐ | 适合开发测试 |

---

## 方案一：Cloudflare Tunnel（推荐，完全免费）

这是**最简单且完全免费**的方案，适合快速让同事访问。

### 优点
- ✅ 完全免费
- ✅ 支持 HTTPS
- ✅ 无需公网 IP
- ✅ 配置简单
- ✅ 支持 Playwright

### 缺点
- ⚠️ 需要本地或服务器运行服务
- ⚠️ 本地机器需要保持运行

### 步骤

#### 1. 安装 cloudflared

```bash
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

#### 2. 登录 Cloudflare

```bash
cloudflared tunnel login
```

这会打开浏览器，选择你的域名（如果没有域名，可以注册一个免费的）。

#### 3. 创建隧道

```bash
cloudflared tunnel create calltrace
```

这会生成一个隧道 ID 和凭证文件。

#### 4. 配置隧道

创建配置文件 `~/.cloudflared/config.yml`:

```yaml
tunnel: <你的隧道ID>
credentials-file: /Users/你的用户名/.cloudflared/<隧道ID>.json

ingress:
  - hostname: calltrace.yourdomain.com  # 替换为你的域名
    service: http://localhost:5001
  - service: http_status:404
```

#### 5. 启动服务

```bash
# 终端1: 启动 Flask 服务
python run.py
# 或
docker-compose up

# 终端2: 启动 Cloudflare Tunnel
cloudflared tunnel run calltrace
```

#### 6. 访问

- **Web UI**: `https://calltrace.yourdomain.com`
- **API**: `https://calltrace.yourdomain.com/api/analyze`

### 持久化运行（可选）

使用 systemd 或 launchd 让隧道在后台运行：

**macOS (launchd):**

创建 `~/Library/LaunchAgents/com.cloudflare.tunnel.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>calltrace</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

加载服务：
```bash
launchctl load ~/Library/LaunchAgents/com.cloudflare.tunnel.plist
```

---

## 方案二：Railway（推荐，最佳体验）

Railway 提供 $5/月的免费额度，非常适合部署需要 Playwright 的应用。

### 优点
- ✅ 支持 Python 和 Playwright
- ✅ 自动部署（GitHub 集成）
- ✅ 提供 HTTPS 域名
- ✅ 环境变量管理
- ✅ 日志查看

### 缺点
- ⚠️ 免费额度有限（$5/月）
- ⚠️ 需要信用卡（但不会扣费，除非超出免费额度）

### 步骤

#### 1. 注册 Railway

访问 https://railway.app/，使用 GitHub 账号登录。

#### 2. 创建新项目

1. 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择你的仓库

#### 4. 配置部署

Railway 会自动检测到 `Dockerfile`，直接使用 Docker 部署。

如果需要自定义，可以设置环境变量：
- `FLASK_ENV=production`
- `PORT=5001` (Railway 会自动设置)

#### 5. 配置 Playwright

Railway 的 Dockerfile 已经包含了 Playwright 的安装，应该可以直接工作。

如果遇到问题，可以在 Railway 的部署日志中查看。

#### 6. 获取访问地址

部署完成后，Railway 会提供一个 `*.railway.app` 的域名。

- **Web UI**: `https://your-app.railway.app`
- **API**: `https://your-app.railway.app/api/analyze`

### 成本控制

Railway 免费额度：
- $5/月免费额度
- 超出后按使用量付费
- 可以设置支出限制

建议：
- 监控使用量
- 设置支出警报
- 如果只是测试，可以随时暂停服务

---

## 方案三：Render（免费但有限制）

Render 提供免费计划，但免费服务会在 15 分钟无活动后休眠。

### 优点
- ✅ 完全免费（有限制）
- ✅ 支持 Python 和 Playwright
- ✅ 自动部署
- ✅ HTTPS 支持

### 缺点
- ⚠️ 免费服务会休眠（首次访问需要唤醒）
- ⚠️ 执行时间限制（免费版 750 小时/月）

### 步骤

#### 1. 注册 Render

访问 https://render.com/，使用 GitHub 账号登录。

#### 2. 创建 Web Service

1. 点击 "New +" → "Web Service"
2. 连接你的 GitHub 仓库
3. 配置：
   - **Name**: `calltrace-sniffer`
   - **Environment**: `Docker`
   - **Region**: 选择最近的区域
   - **Branch**: `main` 或 `master`
   - **Root Directory**: `/` (项目根目录)

#### 3. 环境变量

在 "Environment" 标签页添加：
```
FLASK_ENV=production
PORT=5001
```

#### 4. 部署

点击 "Create Web Service"，Render 会自动构建和部署。

#### 5. 获取地址

部署完成后会得到一个 `*.onrender.com` 的域名。

- **Web UI**: `https://your-app.onrender.com`
- **API**: `https://your-app.onrender.com/api/analyze`

### 防止休眠（可选）

免费服务会在 15 分钟无活动后休眠。可以使用外部服务定期 ping：

```bash
# 使用 cron-job.org 或类似服务
# 每 10 分钟访问一次你的服务
curl https://your-app.onrender.com/
```

---

## 方案四：Fly.io（免费但需要信用卡）

Fly.io 提供免费额度，适合部署需要完整环境的应用。

### 优点
- ✅ 支持 Docker
- ✅ 全球边缘部署
- ✅ 免费额度充足

### 缺点
- ⚠️ 需要信用卡（验证用，不扣费）
- ⚠️ 配置稍复杂

### 步骤

#### 1. 安装 flyctl

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh
```

#### 2. 登录

```bash
fly auth login
```

#### 3. 初始化项目

```bash
fly launch
```

这会创建一个 `fly.toml` 配置文件。

#### 4. 配置 fly.toml

编辑 `fly.toml`:

```toml
app = "calltrace-sniffer"
primary_region = "iad"  # 选择区域

[build]
  dockerfile = "Dockerfile"

[env]
  FLASK_ENV = "production"
  PORT = "5001"

[[services]]
  internal_port = 5001
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

#### 5. 部署

```bash
fly deploy
```

#### 6. 访问

```bash
fly open
```

或访问 `https://your-app.fly.dev`

---

## 方案五：Vercel（有限支持）

Vercel 对 Python 的支持有限，而且 Playwright 在 serverless 环境中很难运行。

### 挑战

1. **Playwright 二进制文件太大**：无法包含在 serverless 函数中
2. **执行时间限制**：Vercel 免费版函数执行时间限制为 10 秒（Hobby）或 60 秒（Pro）
3. **系统依赖**：Playwright 需要系统级依赖

### 可能的解决方案

#### 方案 A: 使用 Playwright 的远程浏览器

可以使用 Playwright 的远程浏览器服务（如 Browserless），但这需要额外费用。

#### 方案 B: 分离架构

将 Playwright 部分分离到其他服务（如 Railway），API 部分部署到 Vercel。

**不推荐**：配置复杂，成本可能更高。

---

## 方案六：Cloudflare Workers（不支持）

Cloudflare Workers 主要支持 JavaScript/TypeScript，对 Python 支持非常有限，且不支持 Playwright。

**不推荐用于此项目**。

---

## 推荐方案对比

### 🥇 最佳选择：Railway
- **原因**: 最佳体验，支持完整功能，自动部署
- **成本**: $5/月免费额度
- **适合**: 生产环境或长期使用

### 🥈 次佳选择：Cloudflare Tunnel
- **原因**: 完全免费，配置简单
- **成本**: 免费
- **适合**: 快速测试，临时访问

### 🥉 第三选择：Render
- **原因**: 免费，但会休眠
- **成本**: 免费（有限制）
- **适合**: 开发测试，低流量场景

---

## 快速开始脚本

### Railway 一键部署

1. Fork 或推送代码到 GitHub
2. 访问 https://railway.app/
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择仓库，Railway 会自动部署

### Cloudflare Tunnel 快速设置

```bash
# 1. 安装
brew install cloudflared  # macOS
# 或下载 Linux 版本

# 2. 登录
cloudflared tunnel login

# 3. 创建隧道
cloudflared tunnel create calltrace

# 4. 配置（编辑 ~/.cloudflared/config.yml）
# 见上面的配置示例

# 5. 启动
# 终端1
python run.py

# 终端2
cloudflared tunnel run calltrace
```

---

## 成本对比

| 方案 | 月成本 | 限制 |
|------|--------|------|
| Cloudflare Tunnel | **免费** | 需要本地运行 |
| Railway | **$0-5** | $5 免费额度 |
| Render | **免费** | 会休眠，750小时/月 |
| Fly.io | **免费** | 需要信用卡验证 |
| Vercel | **免费** | 不支持 Playwright |
| Cloudflare Workers | **免费** | 不支持 Python |

---

## 安全建议

无论使用哪个平台，都建议：

1. **使用 HTTPS**：所有平台都提供免费 HTTPS
2. **设置访问控制**：使用 API Key 或 IP 白名单
3. **监控使用量**：避免超出免费额度
4. **定期更新**：保持依赖和系统更新

---

## 故障排除

### Playwright 在云平台无法运行

**问题**: Playwright 需要浏览器二进制文件和系统依赖。

**解决方案**:
1. 确保 Dockerfile 包含所有依赖（项目已配置）
2. 检查平台是否支持 Docker
3. 查看部署日志中的错误信息

### 服务休眠（Render）

**问题**: Render 免费服务会在 15 分钟无活动后休眠。

**解决方案**:
1. 使用外部服务定期 ping
2. 升级到付费计划
3. 使用 Railway 或 Fly.io

### 超时问题

**问题**: API 请求超时（Playwright 需要较长时间）。

**解决方案**:
1. 增加平台超时设置
2. 优化 Playwright 等待时间
3. 使用异步处理（队列系统）

---

## 总结

对于需要 Playwright 的应用：

✅ **推荐**: Railway（最佳体验）或 Cloudflare Tunnel（完全免费）
❌ **不推荐**: Vercel、Cloudflare Workers（不支持或支持有限）

选择建议：
- **快速测试**: Cloudflare Tunnel
- **生产环境**: Railway
- **长期免费**: Render + 防休眠脚本

更多部署选项请参考 [REMOTE_ACCESS_OPTIONS.md](./REMOTE_ACCESS_OPTIONS.md)

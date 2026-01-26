# Railway 部署指南

本文档介绍如何在 Railway 上部署 CallTraceSniffer 服务。

## 🚀 快速部署

### 1. 准备工作

1. **注册 Railway 账号**
   - 访问 https://railway.app/
   - 使用 GitHub 账号登录

2. **准备代码仓库**
   - 确保代码已推送到 GitHub
   - 确保包含 `Dockerfile` 和 `railway.json`

### 2. 部署步骤

#### 方式一：通过 GitHub 部署（推荐）

1. **创建新项目**
   - 登录 Railway 控制台
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择你的仓库

2. **自动部署**
   - Railway 会自动检测到 `Dockerfile`
   - 自动开始构建和部署
   - 等待部署完成（通常 5-10 分钟）

3. **获取访问地址**
   - 部署完成后，Railway 会生成一个域名
   - 格式: `your-app-name.up.railway.app`
   - 例如: `calltracesniffer-production.up.railway.app`

#### 方式二：通过 Railway CLI

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 部署
railway up
```

### 3. 环境变量配置

在 Railway 控制台中，可以设置环境变量：

1. 进入项目 → Settings → Variables
2. 添加以下变量（可选）:

```
FLASK_ENV=production
PORT=5001
```

**注意**: Railway 会自动设置 `PORT` 环境变量，应用会自动读取。

### 4. 自定义域名（可选）

1. 进入项目 → Settings → Domains
2. 点击 "Generate Domain" 或添加自定义域名
3. Railway 会自动配置 HTTPS

---

## 📋 配置文件说明

### railway.json

项目已包含 `railway.json` 配置文件：

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "sh -c 'if command -v gunicorn > /dev/null 2>&1; then gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --threads 2 --timeout 300 --access-logfile - --error-logfile - --log-level info run:app; else python3 run.py; fi'",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Dockerfile

Railway 使用项目的 `Dockerfile` 进行构建，确保：
- 包含所有系统依赖
- 安装了 Playwright 和浏览器
- 暴露了正确的端口（5001）

---

## 🔍 查看日志

### 在 Railway 控制台

1. 进入项目
2. 点击 "Deployments" 标签
3. 选择最新的部署
4. 查看构建日志和运行日志

### 使用 Railway CLI

```bash
railway logs
```

---

## 🛠️ 常见问题

### 问题 1: 构建失败

**可能原因**:
- Dockerfile 配置错误
- 依赖安装失败
- Playwright 浏览器安装失败

**解决方案**:
1. 查看构建日志，找到具体错误
2. 检查 `Dockerfile` 是否正确
3. 确保 `requirements.txt` 中的依赖版本正确

### 问题 2: 服务无法访问

**可能原因**:
- 端口配置错误
- 服务未正常启动

**解决方案**:
1. 检查 Railway 的日志
2. 确保应用监听 `0.0.0.0` 而不是 `127.0.0.1`
3. 检查 `PORT` 环境变量是否正确

### 问题 3: Playwright 无法运行

**可能原因**:
- 浏览器二进制文件未正确安装
- 系统依赖缺失

**解决方案**:
1. 检查 `Dockerfile` 中的 Playwright 安装步骤
2. 确保所有系统依赖都已安装（见 Dockerfile）

### 问题 4: 请求超时

**可能原因**:
- Playwright 加载页面时间过长
- Railway 免费版有超时限制

**解决方案**:
1. Railway 免费版函数执行时间限制为 60 秒
2. 如果 Playwright 需要更长时间，考虑：
   - 优化等待时间
   - 升级到付费计划
   - 使用异步处理

---

## 💰 成本管理

### 免费额度

Railway 提供 **$5/月** 的免费额度，包括：
- 计算资源（CPU、内存）
- 网络流量
- 存储空间

### 监控使用量

1. 进入项目 → Settings → Usage
2. 查看当前使用量
3. 设置支出警报

### 节省成本

1. **优化资源使用**
   - 使用合适的实例大小
   - 避免不必要的长时间运行

2. **设置支出限制**
   - 在 Settings → Billing 中设置支出上限
   - 超出限制后服务会自动暂停

3. **定期检查**
   - 监控使用量
   - 及时清理不需要的服务

---

## 🔄 更新部署

### 自动更新

如果通过 GitHub 部署，每次推送代码到主分支，Railway 会自动重新部署。

### 手动更新

1. 在 Railway 控制台点击 "Redeploy"
2. 或使用 CLI: `railway up`

---

## 🔐 安全建议

1. **环境变量**
   - 不要在代码中硬编码敏感信息
   - 使用 Railway 的环境变量功能

2. **HTTPS**
   - Railway 自动提供 HTTPS
   - 使用自定义域名时也会自动配置

3. **访问控制**
   - 考虑添加 API Key 验证
   - 限制访问频率

---

## 📊 性能优化

### 1. 实例大小

Railway 会根据使用情况自动调整，也可以手动设置：
- 进入 Settings → Service
- 选择合适的实例大小

### 2. 缓存策略

- 使用 Railway 的持久化存储
- 缓存 Playwright 浏览器实例（如果可能）

### 3. 异步处理

对于长时间运行的任务，考虑：
- 使用队列系统
- 异步处理请求
- 返回任务 ID，客户端轮询结果

---

## 🔗 相关资源

- [Railway 官方文档](https://docs.railway.app/)
- [Railway Discord 社区](https://discord.gg/railway)
- [API 使用指南](./API_USAGE.md)
- [免费云平台部署](./FREE_CLOUD_DEPLOYMENT.md)

---

## 📝 部署检查清单

部署前确保：

- [ ] 代码已推送到 GitHub
- [ ] `Dockerfile` 存在且正确
- [ ] `railway.json` 存在（可选）
- [ ] `requirements.txt` 包含所有依赖
- [ ] 环境变量已配置（如需要）
- [ ] 测试了本地 Docker 构建

部署后检查：

- [ ] 服务状态为 "Running"
- [ ] 可以访问 Web UI
- [ ] API 端点正常响应
- [ ] 日志中没有错误
- [ ] HTTPS 正常工作

---

## 🎉 部署成功！

部署完成后，你可以：

1. **访问 Web UI**: `https://your-app.up.railway.app`
2. **调用 API**: `https://your-app.up.railway.app/api/analyze`
3. **分享给同事**: 提供 API 地址和使用文档

详细 API 使用说明请参考 [API_USAGE.md](./API_USAGE.md)

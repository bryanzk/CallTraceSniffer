# MEV Block Viewer 快速部署指南

## 🚀 快速部署（3 种方式）

### 方式 1: Docker Compose（推荐）

```bash
cd /Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 访问服务
# 主页: http://localhost:5001
# 区块 24274722: http://localhost:5001/mev/block/24274722
# 区块 24279007: http://localhost:5001/mev/block/24279007
```

### 方式 2: 本地 Python 环境

```bash
cd /Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer

# 安装依赖（如果还没安装）
pip install -r requirements.txt

# 启动服务
./scripts/deploy/start_with_mev.sh

# 或直接运行
python3 run.py
```

### 方式 3: 使用构建脚本

```bash
cd /Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer

# 使用 Docker 构建脚本
chmod +x scripts/deploy/build_and_run.sh
./scripts/deploy/build_and_run.sh
```

## 🌐 远程访问配置

### 选项 1: 端口映射 + 防火墙

```bash
# 确保防火墙允许端口 5001
# macOS: 系统偏好设置 > 安全性与隐私 > 防火墙
# Linux: sudo ufw allow 5001/tcp

# 通过 IP 访问
http://your-server-ip:5001/mev/block/24274722
```

### 选项 2: Cloudflare Tunnel（推荐，免费）

参考: `docs/deployment/REMOTE_ACCESS_OPTIONS.md`

配置后访问: `https://your-domain.cf/mev/block/24274722`

### 选项 3: Railway / Fly.io 部署

参考: 
- `docs/deployment/RAILWAY_DEPLOYMENT.md`
- `docs/deployment/FREE_CLOUD_DEPLOYMENT.md`

## 📊 可用区块

当前已分析的区块：

- **区块 24274722**: `/mev/block/24274722`
  - 14 笔 MEV 交易
  - 总利润: +106.31 USD
  - 包含: 12 笔套利、1 笔清算、1 笔三明治攻击

- **区块 24279007**: `/mev/block/24279007`
  - 14 笔 MEV 交易
  - 总利润: +505.40 USD
  - 包含: 13 笔套利、1 笔清算

## 🔍 验证部署

```bash
# 测试主页
curl http://localhost:5001/

# 测试区块 24274722
curl http://localhost:5001/mev/block/24274722

# 测试 SVG 资源
curl http://localhost:5001/mev/block/24274722/0x2998e5203a0afe3b9c_flow.svg
```

## 📝 添加新区块

1. 使用 MCP 工具查询区块 MEV
2. 获取所有交易的 Token Flow Graph
3. 生成 HTML 文件到 `token_flow_graphs/block_<number>/`
4. 重启服务（如果使用 Docker）: `docker-compose restart`

## 🛠️ 故障排查

### 404 错误
- 检查 `token_flow_graphs/block_<number>/index.html` 是否存在
- 确认 Docker 容器中文件已复制

### SVG 无法显示
- 检查 SVG 文件路径
- 确认文件在同一目录

### 远程无法访问
- 检查防火墙设置
- 确认端口映射正确
- 使用 Cloudflare Tunnel 或反向代理

## 📚 详细文档

- [MEV Block Viewer 完整文档](docs/deployment/MEV_BLOCK_VIEWER.md)
- [Docker 部署指南](docs/deployment/README_DOCKER.md)
- [远程访问选项](docs/deployment/REMOTE_ACCESS_OPTIONS.md)

---

**快速开始**: `docker-compose up -d` 然后访问 `http://localhost:5001/mev/block/24274722`

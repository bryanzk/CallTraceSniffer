# MEV 区块 Token Flow Graph 查看器部署指南

## 📋 概述

本功能提供了 MEV 区块分析的 Token Flow Graph 可视化查看器，可以通过 Web 界面远程访问。

## 🚀 快速访问

部署后，可以通过以下 URL 访问：

- **区块 24274722**: `http://your-server:5001/mev/block/24274722`
- **区块 24279007**: `http://your-server:5001/mev/block/24279007`

## 📁 文件结构

```
CallTraceSniffer/
└── token_flow_graphs/
    ├── block_24274722/
    │   ├── index.html          # 主展示页面
    │   └── *.svg               # Token Flow Graph SVG 文件
    └── block_24279007/
        ├── index.html
        └── *.svg
```

## 🔧 部署步骤

### 1. 确保文件已生成

确保 `token_flow_graphs/` 目录下有所需的区块分析文件。

### 2. 使用 Docker 部署（推荐）

#### 方式 1: 使用构建脚本

```bash
cd /Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer
chmod +x scripts/deploy/build_and_run.sh
./scripts/deploy/build_and_run.sh
```

#### 方式 2: 使用 Docker Compose

```bash
docker-compose up -d
```

#### 方式 3: 手动构建和运行

```bash
# 构建镜像
docker build -t blocksec-analyzer:latest .

# 运行容器
docker run -d \
  --name blocksec-analyzer \
  -p 5001:5001 \
  --restart unless-stopped \
  blocksec-analyzer:latest
```

### 3. 验证部署

访问以下 URL 验证部署是否成功：

- 主页: `http://your-server:5001/`
- 区块 24274722: `http://your-server:5001/mev/block/24274722`
- 区块 24279007: `http://your-server:5001/mev/block/24279007`

## 🌐 远程访问配置

### 方式 1: 端口映射（本地部署）

如果服务器在本地，需要确保防火墙允许端口 5001：

```bash
# macOS
# 在系统偏好设置 > 安全性与隐私 > 防火墙中允许 Python 或 Docker

# Linux
sudo ufw allow 5001/tcp
```

然后通过 `http://your-ip:5001/mev/block/24274722` 访问。

### 方式 2: 使用 Cloudflare Tunnel（推荐）

参考 [REMOTE_ACCESS_OPTIONS.md](./REMOTE_ACCESS_OPTIONS.md) 配置 Cloudflare Tunnel。

配置后，可以通过 Cloudflare 提供的域名访问：
- `https://your-domain.cf/mev/block/24274722`

### 方式 3: 使用 Railway / Fly.io 部署

参考以下文档：
- [Railway 部署指南](./RAILWAY_DEPLOYMENT.md)
- [免费云平台部署](./FREE_CLOUD_DEPLOYMENT.md)

部署后，通过平台提供的域名访问。

## 📊 功能特性

### 区块汇总统计
- MEV 交易总数
- 总利润统计
- 按类型分类（套利、清算、三明治攻击）

### 交易详情
- 每笔交易的详细信息
- 利润、成本、收入数据
- Token Flow Graph 可视化

### 交互式查看
- 响应式设计，支持移动端
- 清晰的交易分类标识
- 完整的交易哈希和链接

## 🔍 API 路由

### 查看区块 MEV 分析

**GET** `/mev/block/<block_number>`

返回指定区块的 MEV Token Flow Graph 展示页面。

**示例**:
```bash
curl http://localhost:5001/mev/block/24274722
```

### 获取资源文件

**GET** `/mev/block/<block_number>/<filename>`

返回指定区块的资源文件（SVG 等）。

**示例**:
```bash
curl http://localhost:5001/mev/block/24274722/0x2998e5203a0afe3b9c_flow.svg
```

## 🛠️ 添加新区块分析

要添加新的区块分析：

1. 使用 MCP 服务器查询区块 MEV：
   ```bash
   # 在 Cursor 中使用 MCP 工具
   get_eigenphi_block_mev(block_number=24280000)
   ```

2. 获取所有交易的 Token Flow Graph：
   ```bash
   # 使用脚本批量获取
   python3 /tmp/fetch_block_24280000_graphs.py
   ```

3. 生成 HTML 展示页面：
   ```bash
   # 创建 token_flow_graphs/block_24280000/index.html
   ```

4. 重新部署服务（如果使用 Docker）：
   ```bash
   docker-compose restart
   ```

## 🔒 安全注意事项

1. **文件访问限制**: 路由只允许访问 SVG 文件，防止路径遍历攻击
2. **文件存在检查**: 访问前检查文件是否存在，避免信息泄露
3. **生产环境**: 建议在生产环境中配置 HTTPS 和访问控制

## 📝 故障排查

### 问题 1: 404 错误

**原因**: 区块分析文件不存在

**解决方案**:
1. 检查 `token_flow_graphs/block_<number>/index.html` 是否存在
2. 确认文件路径正确
3. 检查 Docker 容器中文件是否已复制

### 问题 2: SVG 图片无法显示

**原因**: 资源文件路径错误

**解决方案**:
1. 检查 HTML 中的 SVG 文件路径是否正确
2. 确认所有 SVG 文件都在同一目录下
3. 检查文件权限

### 问题 3: 远程无法访问

**原因**: 防火墙或网络配置问题

**解决方案**:
1. 检查防火墙规则
2. 确认端口映射正确
3. 使用 Cloudflare Tunnel 或其他反向代理

## 📚 相关文档

- [Docker 部署指南](./README_DOCKER.md)
- [远程访问选项](./REMOTE_ACCESS_OPTIONS.md)
- [Railway 部署指南](./RAILWAY_DEPLOYMENT.md)
- [免费云平台部署](./FREE_CLOUD_DEPLOYMENT.md)

## 🎯 示例访问

部署成功后，访问示例：

- **本地访问**: `http://localhost:5001/mev/block/24274722`
- **远程访问**: `http://your-server-ip:5001/mev/block/24274722`
- **Cloudflare**: `https://your-domain.cf/mev/block/24274722`
- **Railway**: `https://your-app.railway.app/mev/block/24274722`

---

**最后更新**: 2026-01-25

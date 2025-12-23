# Docker快速开始指南

## 前提条件

1. **安装Docker**
   - macOS: 下载 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - Linux: `sudo apt-get install docker.io docker-compose`
   - Windows: 下载 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

2. **验证安装**
   ```bash
   docker --version
   docker-compose --version  # 或 docker compose version
   ```

## 一键启动（推荐）

```bash
# 给脚本执行权限（首次）
chmod +x build_and_run.sh

# 运行脚本
./build_and_run.sh
```

脚本会自动：
1. ✅ 检查Docker是否安装
2. ✅ 清理旧容器
3. ✅ 构建Docker镜像
4. ✅ 启动容器
5. ✅ 验证服务状态

## 手动启动

### 方式1: Docker Compose（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

### 方式2: Docker命令

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

## 访问应用

启动成功后，打开浏览器访问: **http://localhost:5001**

## 验证部署

```bash
# 检查容器状态
docker ps | grep blocksec-analyzer

# 查看日志
docker logs blocksec-analyzer

# 测试API
curl http://localhost:5001/
```

## 常见问题

### Q: 端口5001被占用？
A: 修改docker-compose.yml中的端口映射，或使用：
```bash
docker run -d -p 8080:5001 blocksec-analyzer:latest
```

### Q: 构建失败？
A: 检查网络连接，确保能访问Docker Hub和pip源

### Q: 容器启动后立即退出？
A: 查看日志：`docker logs blocksec-analyzer`

## 下一步

- 查看完整文档: [README_DOCKER.md](README_DOCKER.md)
- 查看Web界面使用: [README_WEB.md](README_WEB.md)


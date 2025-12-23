# BlockSec分析工具 - Docker部署指南

## 快速开始

### 方式1: 使用构建脚本（推荐）

```bash
chmod +x build_and_run.sh
./build_and_run.sh
```

### 方式2: 使用Docker Compose

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式3: 手动Docker命令

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

启动成功后，在浏览器中访问: **http://localhost:5001**

## 常用命令

### 查看日志
```bash
# 实时查看日志
docker logs -f blocksec-analyzer

# 查看最近100行日志
docker logs --tail 100 blocksec-analyzer
```

### 容器管理
```bash
# 停止容器
docker stop blocksec-analyzer

# 启动容器
docker start blocksec-analyzer

# 重启容器
docker restart blocksec-analyzer

# 删除容器
docker rm -f blocksec-analyzer

# 进入容器
docker exec -it blocksec-analyzer /bin/bash
```

### 镜像管理
```bash
# 查看镜像
docker images | grep blocksec-analyzer

# 删除镜像
docker rmi blocksec-analyzer:latest

# 重新构建（不使用缓存）
docker build --no-cache -t blocksec-analyzer:latest .
```

## 数据持久化

容器中的数据目录已挂载到本地：
- `./data` - 数据目录
- `./logs` - 日志目录

## 端口配置

默认端口是5001，如需修改：

1. **使用docker-compose.yml**:
```yaml
ports:
  - "8080:5001"  # 将本地8080映射到容器5001
```

2. **使用docker run**:
```bash
docker run -d -p 8080:5001 blocksec-analyzer:latest
```

## 环境变量

可以通过环境变量配置：

```bash
docker run -d \
  -p 5001:5001 \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  blocksec-analyzer:latest
```

## 故障排除

### 问题1: 端口被占用
```bash
# 检查端口占用
lsof -i :5001

# 修改端口映射
docker run -d -p 8080:5001 blocksec-analyzer:latest
```

### 问题2: 容器启动失败
```bash
# 查看详细日志
docker logs blocksec-analyzer

# 检查容器状态
docker ps -a | grep blocksec-analyzer
```

### 问题3: Playwright浏览器问题
```bash
# 进入容器检查
docker exec -it blocksec-analyzer /bin/bash
playwright install chromium
```

### 问题4: 权限问题
```bash
# 确保数据目录有写权限
chmod -R 777 data logs
```

## 更新应用

```bash
# 停止旧容器
docker stop blocksec-analyzer
docker rm blocksec-analyzer

# 重新构建（使用缓存）
docker build -t blocksec-analyzer:latest .

# 启动新容器
docker run -d --name blocksec-analyzer -p 5001:5001 blocksec-analyzer:latest
```

## 生产环境部署

### 使用Docker Compose（推荐）

```bash
# 后台运行
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

### 添加健康检查

已在docker-compose.yml中配置健康检查，可以通过以下命令查看：

```bash
docker inspect blocksec-analyzer | grep -A 10 Health
```

## 性能优化

### 限制资源使用

在docker-compose.yml中添加：

```yaml
services:
  blocksec-analyzer:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 安全建议

1. **不要在生产环境使用debug模式**
2. **使用反向代理（如Nginx）**
3. **配置防火墙规则**
4. **定期更新镜像**

## 分发应用

### 导出镜像
```bash
# 保存镜像为tar文件
docker save blocksec-analyzer:latest | gzip > blocksec-analyzer.tar.gz
```

### 导入镜像
```bash
# 加载镜像
docker load < blocksec-analyzer.tar.gz

# 运行
docker run -d -p 5001:5001 blocksec-analyzer:latest
```

### 推送到Docker Hub
```bash
# 登录
docker login

# 打标签
docker tag blocksec-analyzer:latest yourusername/blocksec-analyzer:latest

# 推送
docker push yourusername/blocksec-analyzer:latest
```

## 系统要求

- Docker 20.10+
- Docker Compose 1.29+ (可选)
- 至少2GB可用内存
- 至少5GB可用磁盘空间


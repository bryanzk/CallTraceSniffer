# 部署脚本

此目录包含项目部署和运行相关的脚本。

## 脚本列表

| 脚本 | 用途 | 使用方法 |
|------|------|----------|
| `build_and_run.sh` | Docker 构建并运行 | `./scripts/deploy/build_and_run.sh` |
| `start_web.sh` | 启动 Web 服务器 | `./scripts/deploy/start_web.sh` |
| `push_to_github.sh` | 推送代码到 GitHub | `./scripts/deploy/push_to_github.sh` |
| `set_private.sh` | 设置仓库为私有 | `./scripts/deploy/set_private.sh` |

## 快速使用

### Docker 部署
```bash
cd /path/to/CallTraceSniffer
./scripts/deploy/build_and_run.sh
```

### 本地开发
```bash
cd /path/to/CallTraceSniffer
./scripts/deploy/start_web.sh
```

## 注意事项

- 运行脚本前请确保在项目根目录
- 部分脚本可能需要 `chmod +x` 添加执行权限
- Docker 脚本需要安装 Docker 环境

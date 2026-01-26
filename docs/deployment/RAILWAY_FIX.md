# Railway 部署错误修复指南

## 问题：Application failed to respond

### 问题原因

1. **缺少生产级 WSGI 服务器**: Flask 开发服务器不适合生产环境
2. **token_flow_graphs 目录问题**: 如果目录不存在，Docker 构建可能失败
3. **端口配置问题**: Railway 的 PORT 环境变量可能未正确读取

## 修复方案

### 1. 添加 gunicorn 作为生产服务器

**文件**: `requirements.txt`

```txt
gunicorn>=21.2.0  # 生产环境 WSGI 服务器
```

### 2. 更新 Dockerfile 使用 gunicorn

**文件**: `Dockerfile`

```dockerfile
# 启动命令
# 优先使用 gunicorn（生产环境），如果失败则回退到 Flask 开发服务器
CMD sh -c 'if command -v gunicorn > /dev/null 2>&1; then \
    gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --threads 2 --timeout 300 --access-logfile - --error-logfile - --log-level info "run:app"; \
else \
    python3 run.py; \
fi'
```

### 3. 确保 token_flow_graphs 目录存在

在构建前，确保 `token_flow_graphs` 目录存在（即使是空的）：

```bash
mkdir -p token_flow_graphs
```

### 4. 更新 run.py 支持 gunicorn

**文件**: `run.py`

```python
#!/usr/bin/env python3
"""
应用入口点
支持直接运行和 gunicorn 等 WSGI 服务器
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from calltrace.app import app

# 导出 app 对象供 gunicorn 使用
__all__ = ['app']

if __name__ == '__main__':
    # 支持 Railway 等平台的 PORT 环境变量
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## 验证步骤

### 1. 本地测试 gunicorn

```bash
# 安装依赖
pip install -r requirements.txt

# 测试 gunicorn 启动
gunicorn --bind 0.0.0.0:5001 --workers 2 --threads 2 "run:app"
```

### 2. 本地 Docker 测试

```bash
# 确保 token_flow_graphs 目录存在
mkdir -p token_flow_graphs

# 构建镜像
docker build -t calltrace-sniffer:test .

# 运行容器
docker run -p 5001:5001 -e PORT=5001 calltrace-sniffer:test
```

### 3. Railway 部署后检查

1. **查看 Railway 日志**:
   - 进入 Railway 控制台
   - 查看 Deployments → 最新部署 → Logs
   - 确认没有错误信息

2. **检查应用状态**:
   - 确认服务状态为 "Running"
   - 检查健康检查是否通过

3. **测试端点**:
   ```bash
   curl https://your-app.up.railway.app/
   ```

## 常见错误和解决方案

### 错误 1: ModuleNotFoundError

**症状**: `ModuleNotFoundError: No module named 'calltrace'`

**原因**: Python 路径问题

**解决方案**: 确保 `run.py` 中正确设置了 `sys.path`

### 错误 2: Port already in use

**症状**: `Address already in use`

**原因**: 端口冲突

**解决方案**: Railway 会自动设置 PORT 环境变量，确保应用读取它

### 错误 3: token_flow_graphs 目录不存在

**症状**: `COPY failed: file not found`

**原因**: 源目录不存在

**解决方案**: 
```bash
# 在项目根目录创建空目录
mkdir -p token_flow_graphs
git add token_flow_graphs/
git commit -m "添加 token_flow_graphs 目录"
```

### 错误 4: gunicorn 未找到

**症状**: `gunicorn: command not found`

**原因**: gunicorn 未安装

**解决方案**: 确保 `requirements.txt` 包含 `gunicorn>=21.2.0`

## Railway 环境变量配置

在 Railway 控制台设置以下环境变量（如果需要）：

- `FLASK_ENV=production`
- `PORT` (Railway 自动设置，无需手动配置)
- `PYTHONUNBUFFERED=1` (已在 Dockerfile 中设置)

## 性能优化建议

1. **Worker 数量**: 根据 Railway 实例大小调整
   - 小实例: `--workers 1`
   - 中等实例: `--workers 2`
   - 大实例: `--workers 4`

2. **超时设置**: 根据最长请求时间调整
   - 默认: `--timeout 300` (5分钟)
   - 如果分析需要更长时间，可以增加

3. **日志级别**: 生产环境使用 `--log-level info`

## 相关文件

- `Dockerfile` - Docker 构建配置
- `run.py` - 应用入口点
- `requirements.txt` - Python 依赖
- `src/calltrace/app.py` - Flask 应用

## 参考文档

- [Railway 部署指南](./RAILWAY_DEPLOYMENT.md)
- [Gunicorn 文档](https://docs.gunicorn.org/)

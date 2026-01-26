# SVG 图在 Railway 部署后无法显示的修复

## 问题描述

生成的 SVG 图在部署到 Railway 后无法显示。

## 问题原因

1. **MIME 类型未正确设置**: Flask 的 `send_from_directory` 可能没有正确识别 SVG 文件的 MIME 类型
2. **HTML 标签兼容性**: `<object>` 标签在某些情况下可能不如 `<img>` 标签可靠
3. **路径解析问题**: 在 Railway 部署时，相对路径解析可能存在问题

## 修复方案

### 1. 修复路由中的 MIME 类型设置

**文件**: `src/calltrace/api/routes.py`

- 将 `send_from_directory` 改为 `send_file`
- 显式设置 MIME 类型为 `image/svg+xml`
- 添加错误处理和日志记录

```python
@app.route('/mev/block/<int:block_number>/<path:filename>')
def mev_block_assets(block_number, filename):
    """MEV 区块资源文件（SVG等）"""
    from flask import send_file
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 构建文件路径（使用绝对路径）
    base_dir = os.path.join(os.path.dirname(__file__), '../../..')
    base_dir = os.path.abspath(base_dir)
    block_dir = os.path.join(base_dir, 'token_flow_graphs', f'block_{block_number}')
    
    # 安全检查：只允许访问 SVG 文件
    if not filename.endswith('.svg'):
        return _error_response('只允许访问 SVG 文件', 403)
    
    # 检查文件是否存在
    file_path = os.path.join(block_dir, filename)
    if not os.path.exists(file_path):
        logger.warning(f'SVG 文件不存在: {file_path}')
        return _error_response(f'文件 {filename} 不存在', 404)
    
    # 返回文件，显式设置 MIME 类型
    try:
        return send_file(
            file_path,
            mimetype='image/svg+xml',
            as_attachment=False
        )
    except Exception as e:
        logger.error(f'发送 SVG 文件失败: {e}')
        return _error_response(f'无法读取文件: {str(e)}', 500)
```

### 2. 修改 HTML 生成脚本使用 `<img>` 标签

**文件**: `scripts/generate_mev_block_html.py`

- 将 `<object>` 标签改为 `<img>` 标签
- 添加错误处理（如果图片加载失败，显示备选内容）

```python
html += '''
    </div>
    <div class="svg-container">
        <img src="''' + tx['tx_hash'][:20] + '''_flow.svg" alt="Token Flow Graph" style="width: 100%; height: auto; max-width: 100%;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <div style="display: none; padding: 20px; text-align: center; color: #999;">
            <p>SVG 图加载失败</p>
            <a href="''' + tx['tx_hash'][:20] + '''_flow.svg" target="_blank">直接打开 SVG 文件</a>
        </div>
    </div>
</div>'''
```

### 3. 更新 run.py 支持 Railway PORT 环境变量

**文件**: `run.py`

```python
if __name__ == '__main__':
    # 支持 Railway 等平台的 PORT 环境变量
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
```

### 4. 确保 Dockerfile 正确处理 token_flow_graphs 目录

**文件**: `Dockerfile`

```dockerfile
# 创建 token_flow_graphs 目录（确保存在）
RUN mkdir -p ./token_flow_graphs
# 复制 Token Flow Graph 文件
COPY token_flow_graphs/ ./token_flow_graphs/
```

## 验证步骤

1. **本地测试**:
   ```bash
   # 启动本地服务
   python run.py
   
   # 访问测试页面
   curl http://localhost:5001/mev/block/24279007
   
   # 测试 SVG 文件访问
   curl -I http://localhost:5001/mev/block/24279007/0x79d1082f9e3897db08_flow.svg
   # 应该返回 Content-Type: image/svg+xml
   ```

2. **Railway 部署后测试**:
   - 访问 `https://your-app.up.railway.app/mev/block/24279007`
   - 检查浏览器开发者工具的网络标签
   - 确认 SVG 文件的请求状态为 200
   - 确认响应头包含 `Content-Type: image/svg+xml`

3. **检查日志**:
   - 在 Railway 控制台查看日志
   - 确认没有 404 或 500 错误
   - 如果有错误，日志会显示文件路径信息

## 常见问题

### Q: SVG 文件仍然无法显示

**可能原因**:
- 文件路径不正确
- 文件在 Docker 镜像中不存在
- Railway 文件系统权限问题

**解决方案**:
1. 检查 Docker 构建日志，确认 `token_flow_graphs` 目录被正确复制
2. 在 Railway 控制台查看应用日志，查找文件路径相关的错误
3. 确认 SVG 文件确实存在于 `token_flow_graphs/block_<number>/` 目录中

### Q: 如何更新已生成的 HTML 文件？

如果已经生成的 HTML 文件使用的是 `<object>` 标签，可以：

1. **重新生成 HTML**（推荐）:
   ```bash
   python scripts/generate_mev_block_html.py <block_number>
   ```

2. **批量更新现有 HTML**:
   可以使用脚本批量替换 `<object>` 为 `<img>` 标签

### Q: Railway 部署后文件路径不正确

**解决方案**:
- 确保使用绝对路径解析（已在代码中修复）
- 检查 `base_dir` 的计算是否正确
- 在日志中查看实际的文件路径

## 相关文件

- `src/calltrace/api/routes.py` - Flask 路由处理
- `scripts/generate_mev_block_html.py` - HTML 生成脚本
- `run.py` - 应用入口点
- `Dockerfile` - Docker 构建配置

## 参考文档

- [Railway 部署指南](./RAILWAY_DEPLOYMENT.md)
- [MEV Block Viewer 文档](./MEV_BLOCK_VIEWER.md)

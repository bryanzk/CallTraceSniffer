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



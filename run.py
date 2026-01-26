#!/usr/bin/env python3
"""
应用入口点
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from calltrace.app import app

if __name__ == '__main__':
    # 支持 Railway 等平台的 PORT 环境变量
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)



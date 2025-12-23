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
    app.run(host='0.0.0.0', port=5001)


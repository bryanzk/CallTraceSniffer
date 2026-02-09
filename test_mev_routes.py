#!/usr/bin/env python3
"""测试 MEV 路由"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from calltrace.app import app

with app.app_context():
    from flask import url_for
    print('Flask 应用 MEV 路由测试:')
    print(f'  区块 24274722: {url_for("mev_block_viewer", block_number=24274722)}')
    print(f'  区块 24279007: {url_for("mev_block_viewer", block_number=24279007)}')
    print('\n访问方式:')
    print(f'  http://localhost:5001/mev/block/24274722')
    print(f'  http://localhost:5001/mev/block/24279007')

#!/usr/bin/env python3
"""
修复测试文件中的导入语句
"""
import os
import re

test_files = [
    'tests/unit/test_transfer_extraction.py',
    'tests/unit/test_swap_extraction.py',
    'tests/unit/test_execution_tree.py',
    'tests/unit/test_output_formatting.py',
    'tests/integration/test_integration.py',
]

for test_file in test_files:
    if not os.path.exists(test_file):
        continue
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # 修复损坏的导入语句
    # 移除重复的导入和损坏的行
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 跳过损坏的导入行
        if 'from calltrace.utils.address import' in line and not line.strip().endswith('import'):
            # 检查下一行是否也是导入
            if i + 1 < len(lines) and 'from calltrace.services.converter import TransactionConverter' in lines[i + 1]:
                # 合并这两行
                new_lines.append('import sys')
                new_lines.append('import os')
                new_lines.append("sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))")
                new_lines.append('')
                new_lines.append('from calltrace.services.converter import TransactionConverter')
                new_lines.append('from calltrace.utils.address import format_address, is_router_address')
                new_lines.append('from calltrace.config import config')
                new_lines.append('')
                new_lines.append('converter = TransactionConverter()')
                new_lines.append('ROUTER_ADDRESSES = config.ROUTER_ADDRESSES')
                i += 2
                continue
        # 跳过包含损坏导入的行
        if 'from calltrace.utils.address import' in line and line.strip().endswith('import'):
            i += 1
            continue
        if 'converter = TransactionConverter()' in line and 'extract_' in line:
            # 这是损坏的行，跳过
            i += 1
            continue
        new_lines.append(line)
        i += 1
    
    # 确保文件开头有正确的导入
    if new_lines and not new_lines[0].startswith('"""'):
        # 检查是否已有正确的导入
        has_import = any('from calltrace' in line for line in new_lines[:20])
        if not has_import:
            # 在文件开头添加导入
            header = [
                '"""',
                '测试文件',
                '"""',
                'import sys',
                'import os',
                "sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))",
                '',
                'import pytest',
                'from calltrace.services.converter import TransactionConverter',
                'from calltrace.utils.address import format_address, is_router_address',
                'from calltrace.config import config',
                '',
                'converter = TransactionConverter()',
                'ROUTER_ADDRESSES = config.ROUTER_ADDRESSES',
                ''
            ]
            new_lines = header + new_lines
    
    with open(test_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"Fixed {test_file}")

print("Done!")


#!/usr/bin/env python3
"""
更新测试文件中的导入路径
"""
import os
import re

test_files = [
    'tests/test_transfer_extraction.py',
    'tests/test_swap_extraction.py',
    'tests/test_execution_tree.py',
    'tests/test_output_formatting.py',
    'tests/test_integration.py',
]

replacements = [
    (r'from convert_to_test_case_v2 import', 'from calltrace.services.converter import TransactionConverter\nfrom calltrace.utils.address import'),
    (r'extract_transfers_from_data\(', 'converter.extract_transfers_from_data('),
    (r'extract_swaps_from_data\(', 'converter.extract_swaps_from_data('),
    (r'build_execution_tree_simplified\(', 'converter.build_execution_tree_simplified('),
    (r'generate_test_case_format\(', 'converter.generate_test_case_format('),
]

for test_file in test_files:
    if not os.path.exists(test_file):
        continue
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # 添加converter实例
    if 'converter = TransactionConverter()' not in content:
        # 在导入后添加
        content = content.replace(
            'from calltrace.utils.address import',
            'from calltrace.utils.address import\nfrom calltrace.services.converter import TransactionConverter\n\nconverter = TransactionConverter()'
        )
    
    # 替换函数调用
    for old, new in replacements[1:]:
        content = re.sub(old, new, content)
    
    with open(test_file, 'w') as f:
        f.write(content)
    
    print(f"Updated {test_file}")

print("Done!")


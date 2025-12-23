#!/usr/bin/env python3
"""
处理 case0 交易数据并生成对比报告
"""
import json
import sys
import os
# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import format_address

converter = TransactionConverter()

def process_case0():
    """处理case0数据"""
    # 读取BlockSec数据
    with open('case0_blocksec_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    trace_data = data.get('trace_data')
    if not trace_data:
        print("错误: 未找到 trace_data")
        return
    
    tx_hash = "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004"
    
    data_map = trace_data.get('dataMap', {})
    main_trace = trace_data.get('mainTrace', [])
    
    print("正在提取数据...")
    
    # 提取Transfers
    transfers = converter.extract_transfers_from_data(data_map)
    print(f"找到 {len(transfers)} 个 Transfer")
    
    # 提取Swaps
    swaps = converter.extract_swaps_from_data(data_map, main_trace)
    print(f"找到 {len(swaps)} 个 Swap")
    
    # 构建简化的ExecutionTree
    execution_tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
    print(f"构建执行树: {len(execution_tree['root_nodes'])} 个根节点")
    
    # 生成输出
    output = converter.generate_test_case_format(tx_hash, swaps, execution_tree, transfers)
    
    # 保存到文件
    output_file = 'case0_blocksec_output.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"\n✓ 已生成输出文件: {output_file}")
    
    return {
        'swaps': swaps,
        'transfers': transfers,
        'execution_tree': execution_tree,
        'output': output
    }

def compare_with_test_cases():
    """与test_cases.yaml中的结果对比"""
    # 读取test_cases.yaml中的case0数据
    with open('test_cases.yaml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取case0部分
    case0_start = content.find('========== case0')
    case0_end = content.find('========== case9', case0_start)
    if case0_end == -1:
        case0_end = len(content)
    
    case0_content = content[case0_start:case0_end].strip()
    
    # 处理BlockSec数据
    blocksec_result = process_case0()
    
    # 解析test_cases.yaml中的数据
    expected_swaps = 1
    expected_transfers = 3
    expected_router = 2
    expected_direct = 1
    expected_gas = 51000
    
    # 从test_cases.yaml中提取详细信息（简化解析）
    lines = case0_content.split('\n')
    expected_transfers_detail = []
    
    # 简单提取关键数字
    import re
    for line in lines:
        if 'Swaps:' in line:
            match = re.search(r'Swaps:\s*(\d+)', line)
            if match:
                expected_swaps = int(match.group(1))
        elif 'Transfers:' in line and 'total' in line:
            match = re.search(r'(\d+)\s+total', line)
            if match:
                expected_transfers = int(match.group(1))
            match = re.search(r'Gas Cost:\s*(\d+)', line)
            if match:
                expected_gas = int(match.group(1))
            match = re.search(r'Router:\s*(\d+)', line)
            if match:
                expected_router = int(match.group(1))
            match = re.search(r'Direct:\s*(\d+)', line)
            if match:
                expected_direct = int(match.group(1))
    
    # 生成对比报告
    print("\n" + "=" * 80)
    print("对比分析报告")
    print("=" * 80)
    
    print("\n【1. Swaps 对比】")
    print(f"Test Cases (期望): {expected_swaps} 个")
    print(f"BlockSec (实际): {len(blocksec_result['swaps'])} 个")
    
    if len(blocksec_result['swaps']) != expected_swaps:
        print(f"⚠️  差异: BlockSec识别了 {len(blocksec_result['swaps'])} 个swap，期望 {expected_swaps} 个")
    else:
        print("✓ 数量一致")
    
    print("\nBlockSec识别的Swaps:")
    for i, swap in enumerate(blocksec_result['swaps']):
        print(f"  [{i}] {format_address(swap.get('address', ''))} | {swap.get('method', '')} | Gas: {swap.get('gasUsed', 0)}")
    
    print("\n【2. Transfers 对比】")
    print(f"Test Cases (期望): {expected_transfers} 个 | Router: {expected_router} | Direct: {expected_direct} | Gas: {expected_gas}")
    
    actual_transfers = len(blocksec_result['transfers'])
    actual_router = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Router')
    actual_direct = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Direct')
    actual_virtual = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Virtual')
    actual_gas = sum(t.get('gasCost', 0) for t in blocksec_result['transfers'])
    
    print(f"BlockSec (实际): {actual_transfers} 个 | Router: {actual_router} | Direct: {actual_direct} | Virtual: {actual_virtual} | Gas: {actual_gas}")
    
    if actual_transfers != expected_transfers:
        print(f"⚠️  数量差异: BlockSec识别了 {actual_transfers} 个transfer，期望 {expected_transfers} 个")
    else:
        print("✓ 数量一致")
    
    if actual_router != expected_router:
        print(f"⚠️  Router数量差异: BlockSec识别了 {actual_router} 个，期望 {expected_router} 个")
    
    if actual_direct != expected_direct:
        print(f"⚠️  Direct数量差异: BlockSec识别了 {actual_direct} 个，期望 {expected_direct} 个")
    
    if abs(actual_gas - expected_gas) > 100:  # 允许小误差
        print(f"⚠️  Gas差异: BlockSec总Gas {actual_gas}，期望 {expected_gas}，差异 {actual_gas - expected_gas}")
    else:
        print("✓ Gas基本一致")
    
    print("\nBlockSec识别的Transfers:")
    for i, transfer in enumerate(blocksec_result['transfers']):
        print(f"  [{i}] {transfer.get('type', 'N/A')} | {format_address(transfer.get('from', ''))} → {format_address(transfer.get('to', ''))}")
        print(f"      Token: {format_address(transfer.get('token', ''))} | Amount: {transfer.get('amount', '0')} | Gas: {transfer.get('gasCost', 0)}")
    
    print("\n【3. ExecutionTree 对比】")
    expected_roots = 1
    actual_roots = len(blocksec_result['execution_tree']['root_nodes'])
    print(f"Test Cases (期望): {expected_roots} 个根节点")
    print(f"BlockSec (实际): {actual_roots} 个根节点")
    
    if actual_roots != expected_roots:
        print(f"⚠️  差异: BlockSec识别了 {actual_roots} 个根节点，期望 {expected_roots} 个")
    else:
        print("✓ 根节点数量一致")
    
    print("\n【4. 详细对比】")
    print("\nBlockSec输出:")
    print("-" * 80)
    print(blocksec_result['output'])
    print("-" * 80)
    
    print("\nTest Cases期望输出:")
    print("-" * 80)
    print(case0_content)
    print("-" * 80)

if __name__ == "__main__":
    compare_with_test_cases()


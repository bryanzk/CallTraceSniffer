#!/usr/bin/env python3
"""
处理所有case的BlockSec数据并生成对比报告
"""
import json
import sys
import os
import re
# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import format_address

converter = TransactionConverter()

CASES = ['case9', 'case12', 'case21', 'case33']

def process_case(case_name: str):
    """处理单个case的数据"""
    # 尝试多个可能的路径
    possible_paths = [
        f'{case_name}_blocksec_data.json',
        f'local/output/{case_name}_blocksec_data.json',
    ]
    
    data_file = None
    for path in possible_paths:
        if os.path.exists(path):
            data_file = path
            break
    
    if not data_file:
        print(f"错误: 未找到 {case_name}_blocksec_data.json (尝试了: {possible_paths})")
        return None
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 未找到 {data_file}")
        return None
    
    trace_data = data.get('trace_data')
    if not trace_data:
        print(f"错误: {case_name} 未找到 trace_data")
        return None
    
    tx_hash = data.get('tx_hash', '')
    
    data_map = trace_data.get('dataMap', {})
    main_trace = trace_data.get('mainTrace', [])
    
    # 提取Transfers
    transfers = converter.extract_transfers_from_data(data_map)
    
    # 提取Swaps
    swaps = converter.extract_swaps_from_data(data_map, main_trace)
    
    # 构建简化的ExecutionTree
    execution_tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
    
    # 生成输出
    output = converter.generate_test_case_format(tx_hash, swaps, execution_tree, transfers)
    
    # 保存到文件（尝试多个可能的路径）
    possible_output_paths = [
        f'{case_name}_blocksec_output.yaml',
        f'local/output/{case_name}_blocksec_output.yaml',
    ]
    
    output_file = possible_output_paths[0]  # 默认使用第一个
    # 如果数据文件在local/output，输出文件也在那里
    if 'local/output' in data_file:
        output_file = possible_output_paths[1]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"[{case_name}] ✓ 已生成输出文件: {output_file}")
    
    return {
        'case': case_name,
        'tx_hash': tx_hash,
        'swaps': swaps,
        'transfers': transfers,
        'execution_tree': execution_tree,
        'output': output
    }

def parse_test_cases():
    """解析test_cases.yaml中的期望值"""
    with open('test_cases.yaml', 'r', encoding='utf-8') as f:
        content = f.read()
    
    cases = {}
    
    # 分割各个case
    case_pattern = r'========== (case\d+) AFTER Op_5 =========='
    case_matches = list(re.finditer(case_pattern, content))
    
    for i, match in enumerate(case_matches):
        case_name = match.group(1)
        start_pos = match.start()
        end_pos = case_matches[i + 1].start() if i + 1 < len(case_matches) else len(content)
        case_content = content[start_pos:end_pos].strip()
        
        # 解析case内容
        case_data = {
            'content': case_content,
            'swaps': 0,
            'transfers': 0,
            'router': 0,
            'direct': 0,
            'virtual': 0,
            'gas': 0,
            'roots': 0
        }
        
        # 提取数字
        swaps_match = re.search(r'Swaps:\s*(\d+)', case_content)
        if swaps_match:
            case_data['swaps'] = int(swaps_match.group(1))
        
        transfers_match = re.search(r'Transfers:\s*(\d+)\s+total', case_content)
        if transfers_match:
            case_data['transfers'] = int(transfers_match.group(1))
        
        router_match = re.search(r'Router:\s*(\d+)', case_content)
        if router_match:
            case_data['router'] = int(router_match.group(1))
        
        direct_match = re.search(r'Direct:\s*(\d+)', case_content)
        if direct_match:
            case_data['direct'] = int(direct_match.group(1))
        
        virtual_match = re.search(r'Virtual:\s*(\d+)', case_content)
        if virtual_match:
            case_data['virtual'] = int(virtual_match.group(1))
        
        gas_match = re.search(r'Gas Cost:\s*(\d+)', case_content)
        if gas_match:
            case_data['gas'] = int(gas_match.group(1))
        
        roots_match = re.search(r'ExecutionTree:\s*(\d+)\s+root', case_content)
        if roots_match:
            case_data['roots'] = int(roots_match.group(1))
        
        cases[case_name] = case_data
    
    return cases

def compare_case(blocksec_result, expected_data):
    """对比单个case的结果"""
    case_name = blocksec_result['case']
    
    actual_swaps = len(blocksec_result['swaps'])
    actual_transfers = len(blocksec_result['transfers'])
    actual_router = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Router')
    actual_direct = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Direct')
    actual_virtual = sum(1 for t in blocksec_result['transfers'] if t.get('type') == 'Virtual')
    actual_gas = sum(t.get('gasCost', 0) for t in blocksec_result['transfers'])
    actual_roots = len(blocksec_result['execution_tree']['root_nodes'])
    
    expected_swaps = expected_data['swaps']
    expected_transfers = expected_data['transfers']
    expected_router = expected_data['router']
    expected_direct = expected_data['direct']
    expected_virtual = expected_data['virtual']
    expected_gas = expected_data['gas']
    expected_roots = expected_data['roots']
    
    comparison = {
        'case': case_name,
        'swaps': {
            'expected': expected_swaps,
            'actual': actual_swaps,
            'match': actual_swaps == expected_swaps
        },
        'transfers': {
            'expected': expected_transfers,
            'actual': actual_transfers,
            'match': actual_transfers == expected_transfers
        },
        'router': {
            'expected': expected_router,
            'actual': actual_router,
            'match': actual_router == expected_router
        },
        'direct': {
            'expected': expected_direct,
            'actual': actual_direct,
            'match': actual_direct == expected_direct
        },
        'virtual': {
            'expected': expected_virtual,
            'actual': actual_virtual,
            'match': actual_virtual == expected_virtual
        },
        'gas': {
            'expected': expected_gas,
            'actual': actual_gas,
            'match': abs(actual_gas - expected_gas) <= 100  # 允许小误差
        },
        'roots': {
            'expected': expected_roots,
            'actual': actual_roots,
            'match': actual_roots == expected_roots
        }
    }
    
    return comparison

def generate_comparison_report(all_comparisons):
    """生成对比报告"""
    report = []
    report.append("# 所有Case的BlockSec vs Test Cases对比报告\n")
    
    for comp in all_comparisons:
        case_name = comp['case']
        report.append(f"## {case_name}\n")
        
        # Swaps对比
        swaps = comp['swaps']
        status = "✓" if swaps['match'] else "⚠️"
        report.append(f"### Swaps")
        report.append(f"- {status} 期望: {swaps['expected']} | 实际: {swaps['actual']}")
        if not swaps['match']:
            report.append(f"  - 差异: {swaps['actual'] - swaps['expected']}")
        
        # Transfers对比
        transfers = comp['transfers']
        status = "✓" if transfers['match'] else "⚠️"
        report.append(f"\n### Transfers")
        report.append(f"- {status} 数量: 期望 {transfers['expected']} | 实际 {transfers['actual']}")
        
        router = comp['router']
        status = "✓" if router['match'] else "⚠️"
        report.append(f"- {status} Router: 期望 {router['expected']} | 实际 {router['actual']}")
        
        direct = comp['direct']
        status = "✓" if direct['match'] else "⚠️"
        report.append(f"- {status} Direct: 期望 {direct['expected']} | 实际 {direct['actual']}")
        
        virtual = comp['virtual']
        status = "✓" if virtual['match'] else "⚠️"
        report.append(f"- {status} Virtual: 期望 {virtual['expected']} | 实际 {virtual['actual']}")
        
        gas = comp['gas']
        status = "✓" if gas['match'] else "⚠️"
        report.append(f"- {status} Gas: 期望 {gas['expected']} | 实际 {gas['actual']} | 差异 {gas['actual'] - gas['expected']}")
        
        # ExecutionTree对比
        roots = comp['roots']
        status = "✓" if roots['match'] else "⚠️"
        report.append(f"\n### ExecutionTree")
        report.append(f"- {status} 根节点: 期望 {roots['expected']} | 实际 {roots['actual']}")
        
        report.append("\n---\n")
    
    # 总结
    report.append("\n## 总结\n")
    total_cases = len(all_comparisons)
    matches = {
        'swaps': sum(1 for c in all_comparisons if c['swaps']['match']),
        'transfers': sum(1 for c in all_comparisons if c['transfers']['match']),
        'router': sum(1 for c in all_comparisons if c['router']['match']),
        'direct': sum(1 for c in all_comparisons if c['direct']['match']),
        'virtual': sum(1 for c in all_comparisons if c['virtual']['match']),
        'gas': sum(1 for c in all_comparisons if c['gas']['match']),
        'roots': sum(1 for c in all_comparisons if c['roots']['match'])
    }
    
    report.append(f"| 项目 | 匹配数/总数 | 匹配率 |")
    report.append(f"|------|------------|--------|")
    report.append(f"| Swaps | {matches['swaps']}/{total_cases} | {matches['swaps']*100//total_cases}% |")
    report.append(f"| Transfers数量 | {matches['transfers']}/{total_cases} | {matches['transfers']*100//total_cases}% |")
    report.append(f"| Router类型 | {matches['router']}/{total_cases} | {matches['router']*100//total_cases}% |")
    report.append(f"| Direct类型 | {matches['direct']}/{total_cases} | {matches['direct']*100//total_cases}% |")
    report.append(f"| Virtual类型 | {matches['virtual']}/{total_cases} | {matches['virtual']*100//total_cases}% |")
    report.append(f"| Gas | {matches['gas']}/{total_cases} | {matches['gas']*100//total_cases}% |")
    report.append(f"| ExecutionTree根节点 | {matches['roots']}/{total_cases} | {matches['roots']*100//total_cases}% |")
    
    return '\n'.join(report)

def main():
    """主函数"""
    print("正在处理所有case...\n")
    
    # 处理所有case
    blocksec_results = []
    for case_name in CASES:
        result = process_case(case_name)
        if result:
            blocksec_results.append(result)
    
    print(f"\n✓ 处理了 {len(blocksec_results)} 个case\n")
    
    # 解析期望值
    print("正在解析test_cases.yaml中的期望值...")
    expected_data = parse_test_cases()
    
    # 对比
    print("正在生成对比报告...")
    all_comparisons = []
    for result in blocksec_results:
        case_name = result['case']
        if case_name in expected_data:
            comparison = compare_case(result, expected_data[case_name])
            all_comparisons.append(comparison)
    
    # 生成报告
    report = generate_comparison_report(all_comparisons)
    
    # 保存报告
    report_file = 'all_cases_comparison_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✓ 对比报告已保存到: {report_file}")
    print("\n" + "=" * 80)
    print("报告预览:")
    print("=" * 80)
    print(report)

if __name__ == "__main__":
    main()


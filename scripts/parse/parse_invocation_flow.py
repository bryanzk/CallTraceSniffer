#!/usr/bin/env python3
"""
解析并提取invocation flow中的所有嵌套调用
"""
import json
from typing import Dict, List, Any

def extract_call_info(node: Dict, data_map: Dict, depth: int = 0, max_depth: int = 20) -> Dict:
    """递归提取调用信息"""
    if depth > max_depth:
        return None
    
    result = {
        'depth': depth,
        'id': node.get('id'),
        'order': node.get('order'),
        'type': node.get('type'),
        'type_name': get_type_name(node.get('type')),
    }
    
    # 从dataMap中获取详细信息
    node_id = node.get('id')
    # dataMap的键是字符串，需要转换
    node_id_str = str(node_id) if node_id is not None else None
    if node_id_str and node_id_str in data_map:
        data = data_map[node_id_str]
        # 数据可能包含invocation对象
        if isinstance(data, dict):
            invocation = data.get('invocation', {})
            if isinstance(invocation, dict):
                result.update({
                    'from': invocation.get('fromAddress'),
                    'to': invocation.get('address'),
                    'value': invocation.get('value'),
                    'gasUsed': invocation.get('gasUsed'),
                    'input': invocation.get('callData'),
                    'output': invocation.get('output'),
                    'method': invocation.get('decodedMethod', {}).get('name') if isinstance(invocation.get('decodedMethod'), dict) else invocation.get('selector'),
                    'operation': invocation.get('operation'),
                    'selector': invocation.get('selector'),
                    'status': invocation.get('status'),
                    'revert': invocation.get('revert'),
                    'revertMessage': invocation.get('revertMessage'),
                })
            else:
                # 如果没有invocation，直接使用data
                result.update({
                    'from': data.get('from'),
                    'to': data.get('to'),
                    'value': data.get('value'),
                    'gas': data.get('gas'),
                    'gasUsed': data.get('gasUsed'),
                    'input': data.get('input'),
                    'output': data.get('output'),
                    'method': data.get('method'),
                    'label': data.get('label'),
                })
    
    # 递归处理子节点
    children = node.get('children', [])
    if children:
        result['children'] = []
        for child in children:
            child_info = extract_call_info(child, data_map, depth + 1, max_depth)
            if child_info:
                result['children'].append(child_info)
    
    return result

def get_type_name(type_code: int) -> str:
    """将类型代码转换为名称"""
    type_map = {
        0: 'CALL',
        1: 'CREATE',
        2: 'CREATE2',
        3: 'DELEGATECALL',
        4: 'STATICCALL',
        5: 'SELFDESTRUCT',
    }
    return type_map.get(type_code, f'UNKNOWN({type_code})')

def format_call_tree(node: Dict, indent: int = 0) -> str:
    """格式化调用树为可读文本"""
    lines = []
    prefix = '  ' * indent
    
    # 基本信息
    type_name = node.get('type_name', 'UNKNOWN')
    from_addr = node.get('from', 'N/A')[:10] + '...' if node.get('from') else 'N/A'
    to_addr = node.get('to', 'N/A')[:10] + '...' if node.get('to') else 'N/A'
    method = node.get('method', 'N/A')
    label = node.get('label', '')
    
    # 获取gas信息
    gas_used = node.get('gasUsed')
    gas_initial = node.get('gas')
    
    line = f"{prefix}[{type_name}] {from_addr} -> {to_addr}"
    if method and method != 'N/A':
        line += f" | {method}"
    if label:
        line += f" | {label}"
    if node.get('value'):
        line += f" | Value: {node.get('value')}"
    
    # 始终显示gas used，即使为0或None
    if gas_used is not None:
        line += f" | GasUsed: {gas_used}"
    else:
        line += f" | GasUsed: N/A"
    
    # 如果有初始gas，也显示
    if gas_initial is not None:
        line += f" | Gas: {gas_initial}"
    
    lines.append(line)
    
    # 递归处理子节点
    children = node.get('children', [])
    for child in children:
        lines.extend(format_call_tree(child, indent + 1).split('\n'))
    
    return '\n'.join(lines)

def main():
    # 读取数据
    with open('invocation_flow_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    trace_data = data.get('trace_data')
    if not trace_data:
        print("未找到trace数据")
        return
    
    data_map = trace_data.get('dataMap', {})
    main_trace = trace_data.get('mainTrace', [])
    
    print("=" * 80)
    print("INVOCATION FLOW - 嵌套调用结构")
    print("=" * 80)
    print(f"\n总节点数: {trace_data.get('mainTraceNodeCount', 'N/A')}")
    print(f"Trace1节点数: {trace_data.get('traceNodeCount1', 'N/A')}")
    print(f"Trace2节点数: {trace_data.get('traceNodeCount2', 'N/A')}")
    print(f"Trace3节点数: {trace_data.get('traceNodeCount3', 'N/A')}")
    print("\n" + "=" * 80)
    
    # 处理mainTrace
    if main_trace:
        print("\n=== MAIN TRACE ===")
        all_calls = []
        
        for root_node in main_trace:
            call_info = extract_call_info(root_node, data_map)
            if call_info:
                all_calls.append(call_info)
                print("\n" + format_call_tree(call_info))
        
        # 保存详细数据
        output_file = 'invocation_flow_parsed.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_calls, f, ensure_ascii=False, indent=2)
        
        print(f"\n\n详细数据已保存到: {output_file}")
        
        # 统计信息
        def count_nodes(node):
            count = 1
            for child in node.get('children', []):
                count += count_nodes(child)
            return count
        
        def sum_gas_used(node):
            """递归计算总gas使用量"""
            total = node.get('gasUsed', 0) or 0
            for child in node.get('children', []):
                total += sum_gas_used(child)
            return total
        
        def collect_gas_info(node, gas_list):
            """收集所有节点的gas信息"""
            gas_used = node.get('gasUsed')
            if gas_used is not None:
                gas_list.append({
                    'type': node.get('type_name'),
                    'from': node.get('from'),
                    'to': node.get('to'),
                    'method': node.get('method'),
                    'gasUsed': gas_used,
                    'depth': node.get('depth', 0)
                })
            for child in node.get('children', []):
                collect_gas_info(child, gas_list)
        
        total_nodes = sum(count_nodes(call) for call in all_calls)
        max_depth = max(
            (max_depth_in_tree(call) for call in all_calls),
            default=0
        )
        total_gas = sum(sum_gas_used(call) for call in all_calls)
        
        # 收集所有gas信息
        all_gas_info = []
        for call in all_calls:
            collect_gas_info(call, all_gas_info)
        
        # 按gas使用量排序
        all_gas_info.sort(key=lambda x: x.get('gasUsed', 0) or 0, reverse=True)
        
        print(f"\n统计信息:")
        print(f"  - 总调用节点数: {total_nodes}")
        print(f"  - 最大嵌套深度: {max_depth}")
        print(f"  - 根调用数: {len(all_calls)}")
        print(f"  - 总Gas使用量: {total_gas:,}")
        print(f"  - 有Gas信息的调用数: {len(all_gas_info)}")
        
        # 显示gas使用最多的前10个调用
        print(f"\nGas使用量最多的前10个调用:")
        for i, gas_info in enumerate(all_gas_info[:10], 1):
            from_addr = (gas_info['from'][:10] + '...') if gas_info.get('from') else 'N/A'
            to_addr = (gas_info['to'][:10] + '...') if gas_info.get('to') else 'N/A'
            method = gas_info.get('method', 'N/A')
            gas_used = gas_info.get('gasUsed', 0)
            print(f"  {i}. [{gas_info['type']}] {from_addr} -> {to_addr} | {method} | GasUsed: {gas_used:,}")
        
        # 保存gas统计信息
        gas_stats_file = 'invocation_flow_gas_stats.json'
        with open(gas_stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_gas': total_gas,
                'total_calls_with_gas': len(all_gas_info),
                'top_gas_consumers': all_gas_info[:20],
                'gas_by_type': {}
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nGas统计信息已保存到: {gas_stats_file}")

def max_depth_in_tree(node):
    """计算树的最大深度"""
    children = node.get('children', [])
    if not children:
        return node.get('depth', 0)
    return max(max_depth_in_tree(child) for child in children)

if __name__ == "__main__":
    main()


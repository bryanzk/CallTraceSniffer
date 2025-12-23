#!/usr/bin/env python3
"""
将 invocation flow 数据转换为 test_cases.yaml 格式
参考: 交易路径优化和执行编排的设计方案
"""
import json
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

# 常见的Router地址（可以根据实际情况扩展）
ROUTER_ADDRESSES = {
    '0x000000000004444c5dc75cb358380d2e3de08a90',  # Uniswap V4 Pool Manager
    '0xe6f5c83b9d2005bf14333d7e48d3002fff4c93a7',  # 可能是Router
}

# 常见的Token地址
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

def is_router_address(addr: str) -> bool:
    """判断是否为Router地址"""
    if not addr:
        return False
    return addr.lower() in [r.lower() for r in ROUTER_ADDRESSES]

def is_token_transfer(method: str) -> bool:
    """判断是否为代币转账方法"""
    transfer_methods = ['transfer', 'transferFrom', 'safeTransferFrom']
    return method and any(tm in method.lower() for tm in transfer_methods)

def extract_token_from_transfer(call: Dict) -> Optional[str]:
    """从transfer调用中提取token地址"""
    # 从input数据中提取token地址（通常是第一个参数）
    input_data = call.get('input', '')
    if input_data and input_data.startswith('0x') and len(input_data) >= 138:
        # transfer(address,uint256) 的格式
        # 第一个参数是to地址，但我们需要token地址
        # 通常token地址是call的to地址
        return call.get('to')
    return None

def extract_amount_from_transfer(call: Dict) -> Optional[str]:
    """从transfer调用中提取金额"""
    input_data = call.get('input', '')
    if input_data and input_data.startswith('0x') and len(input_data) >= 138:
        # transfer(address,uint256) - 第二个参数是amount
        try:
            # 提取第二个参数（从位置66开始，64个字符）
            amount_hex = input_data[130:194] if len(input_data) >= 194 else None
            if amount_hex:
                amount = int(amount_hex, 16)
                return str(amount)
        except:
            pass
    return None

def analyze_call_tree(node: Dict, depth: int = 0, parent: Optional[Dict] = None) -> Dict:
    """分析调用树，提取Swaps、ExecutionTree和Transfers信息"""
    result = {
        'swaps': [],
        'execution_tree': [],
        'transfers': [],
        'nodes': {}  # 用于构建执行树
    }
    
    def traverse(node: Dict, depth: int, parent_id: Optional[str] = None, node_map: Dict = None):
        """遍历调用树"""
        if node_map is None:
            node_map = {}
        
        node_id = node.get('to', 'N/A')
        if node_id == 'N/A' or not node_id:
            node_id = f"node_{node.get('id', 'unknown')}"
        
        # 构建节点信息（处理null值）
        method = node.get('method') or ''
        from_addr = node.get('from') or ''
        to_addr = node.get('to') or ''
        gas_used = node.get('gasUsed')
        if gas_used is None:
            gas_used = 0
        else:
            gas_used = gas_used or 0
        
        node_info = {
            'id': node_id,
            'form': determine_form(node),
            'method': method,
            'from': from_addr,
            'to': to_addr,
            'gasUsed': gas_used,
            'depth': depth,
            'parent': parent_id,
            'children': []
        }
        
        node_map[node_id] = node_info
        
        # 检查是否为Swap操作
        method = (node.get('method') or '').lower()
        if method and 'swap' in method:
            # 尝试识别swap的输入输出token
            swap_info = analyze_swap(node)
            if swap_info:
                result['swaps'].append(swap_info)
        
        # 检查是否为Transfer操作
        node_method = node.get('method') or ''
        if is_token_transfer(node_method):
            transfer_info = analyze_transfer(node, parent)
            if transfer_info:
                result['transfers'].append(transfer_info)
        
        # 递归处理子节点（跳过null节点）
        for child in node.get('children', []):
            if child and child.get('to'):  # 跳过无效节点
                child_id = traverse(child, depth + 1, node_id, node_map)
                if child_id and child_id != 'N/A':
                    node_info['children'].append(child_id)
        
        return node_id
    
    # 构建执行树
    root_nodes = []
    node_map = {}
    
    for root in [node]:  # 处理根节点
        root_id = traverse(root, 0, None, node_map)
        if root_id:
            root_nodes.append(root_id)
    
    result['nodes'] = node_map
    result['execution_tree'] = root_nodes
    
    return result

def determine_form(node: Dict) -> str:
    """确定节点的Form（Scope或Node）"""
    # 如果有子节点，通常是Scope
    if node.get('children'):
        return 'Scope'
    return 'Node'

def analyze_swap(node: Dict) -> Optional[Dict]:
    """分析Swap操作"""
    method = node.get('method', '')
    if 'swap' not in method.lower():
        return None
    
    # 尝试从input或子调用中提取token信息
    # 这里需要根据实际的swap方法签名来解析
    swap_info = {
        'address': node.get('to', ''),
        'form': determine_form(node),
        'method': method,
        'gasUsed': node.get('gasUsed', 0) or 0,
    }
    
    # 尝试识别输入输出token（简化处理）
    # 实际应该从input data或子调用中解析
    children = node.get('children', [])
    for child in children:
        if is_token_transfer(child.get('method', '')):
            token = child.get('to', '')
            if token:
                # 这里需要更复杂的逻辑来确定输入输出
                pass
    
    return swap_info

def analyze_transfer(node: Dict, parent: Optional[Dict] = None) -> Optional[Dict]:
    """分析Transfer操作"""
    if not is_token_transfer(node.get('method', '')):
        return None
    
    from_addr = node.get('from', '')
    to_addr = node.get('to', '')
    token = to_addr  # token地址通常是合约地址
    
    # 提取金额
    amount = extract_amount_from_transfer(node)
    if not amount:
        amount = '0'
    
    # 确定Transfer类型
    transfer_type = 'Direct'
    if is_router_address(from_addr) or is_router_address(to_addr):
        transfer_type = 'Router'
    elif from_addr == to_addr or not from_addr or not to_addr:
        transfer_type = 'Virtual'
    
    # 确定Gas Cost
    gas_cost = node.get('gasUsed', 0) or 0
    if transfer_type == 'Router':
        gas_cost = 23000  # 标准Router transfer gas
    elif transfer_type == 'Direct':
        gas_cost = 5000   # 标准Direct transfer gas
    elif transfer_type == 'Virtual':
        gas_cost = 0
    
    return {
        'from': from_addr,
        'to': to_addr,
        'token': token,
        'amount': amount,
        'type': transfer_type,
        'gasCost': gas_cost,
        'gasUsed': node.get('gasUsed', 0) or 0,
    }

def format_address(addr: str, length: int = 10) -> str:
    """格式化地址显示"""
    if not addr or addr == 'N/A':
        return 'N/A'
    if len(addr) > length + 3:
        return addr[:length] + '...'
    return addr

def generate_test_case_format(tx_hash: str, analysis: Dict) -> str:
    """生成test_cases.yaml格式的输出"""
    lines = []
    
    lines.append(f"========== case_after_op5 ==========")
    lines.append(f"TX: {tx_hash}")
    
    # Swaps部分
    swaps = analysis.get('swaps', [])
    lines.append(f"     📦 Swaps: {len(swaps)}")
    for i, swap in enumerate(swaps):
        addr = format_address(swap.get('address', ''))
        form = swap.get('form', 'Node')
        method = swap.get('method', '')
        lines.append(f"        [{i}] {addr} | Form: {form} | Method: {method}")
    
    # ExecutionTree部分
    execution_tree = analysis.get('execution_tree', [])
    nodes = analysis.get('nodes', {})
    lines.append(f"     🌳 ExecutionTree: {len(execution_tree)} root nodes")
    
    def format_tree_node(node_id: str, indent: int = 0):
        """格式化树节点"""
        if node_id not in nodes:
            return []
        node = nodes[node_id]
        prefix = '     ' + '   ' * indent
        children = node.get('children', [])
        children_str = f" [{len(children)} children]" if children else ""
        form = node.get('form', 'Node')
        addr = format_address(node_id)
        result = [f"{prefix}Root[{indent}]: {addr} Form:{form}{children_str}"]
        
        for i, child_id in enumerate(children):
            child_prefix = '     ' + '   ' * (indent + 1)
            child_node = nodes.get(child_id, {})
            child_form = child_node.get('form', 'Node')
            child_addr = format_address(child_id)
            result.append(f"{child_prefix}Child[{i}]: {child_addr} Form:{child_form}")
            # 递归处理子节点
            result.extend(format_tree_node(child_id, indent + 1))
        
        return result
    
    for i, root_id in enumerate(execution_tree):
        if i == 0:
            lines.extend(format_tree_node(root_id, 0))
        else:
            node = nodes.get(root_id, {})
            form = node.get('form', 'Node')
            addr = format_address(root_id)
            lines.append(f"     Root[{i}]: {addr} Form:{form}")
    
    # Transfers部分
    transfers = analysis.get('transfers', [])
    total_gas = sum(t.get('gasCost', 0) for t in transfers)
    router_count = sum(1 for t in transfers if t.get('type') == 'Router')
    direct_count = sum(1 for t in transfers if t.get('type') == 'Direct')
    virtual_count = sum(1 for t in transfers if t.get('type') == 'Virtual')
    
    lines.append(f"     🔗 Transfers: {len(transfers)} total | Gas Cost: {total_gas}")
    lines.append(f"        Router: {router_count} | Direct: {direct_count} | Virtual: {virtual_count}")
    lines.append("")
    
    for i, transfer in enumerate(transfers):
        from_addr = transfer.get('from', '')
        to_addr = transfer.get('to', '')
        token = transfer.get('token', '')
        amount = transfer.get('amount', '0')
        transfer_type = transfer.get('type', 'Direct')
        gas_cost = transfer.get('gasCost', 0)
        
        # 确定图标
        if transfer_type == 'Router':
            icon = "🔴"
        elif transfer_type == 'Virtual':
            icon = "🔵"
        else:
            icon = "🟢"
        
        from_display = format_address(from_addr)
        to_display = format_address(to_addr)
        token_display = format_address(token)
        
        # 判断是否为Router
        if is_router_address(from_addr):
            from_display = "🏦Router"
        if is_router_address(to_addr):
            to_display = "🏦Router"
        
        lines.append(f"        [{i}] {icon} 🏊{from_display} → 🏊{to_display}")
        lines.append(f"            Token: {token_display} | Amount: {amount}")
        lines.append(f"            Type: {transfer_type} | Cost: {gas_cost} gas")
        if i < len(transfers) - 1:
            lines.append("")
    
    return '\n'.join(lines)

def main():
    """主函数"""
    # 读取invocation flow数据
    try:
        with open('invocation_flow_parsed.json', 'r', encoding='utf-8') as f:
            calls_data = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到 invocation_flow_parsed.json 文件")
        return
    
    # 读取原始数据获取交易哈希
    try:
        with open('invocation_flow_data.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # 从call_info中提取交易哈希
            tx_hash = "0x404e80ee3d321a6db4673a06c42db85231e95aea5a88d74b5cf28b0b8f3218c3"
    except:
        tx_hash = "0x404e80ee3d321a6db4673a06c42db85231e95aea5a88d74b5cf28b0b8f3218c3"
    
    # 分析调用树
    all_analysis = []
    
    for root_call in calls_data:
        analysis = analyze_call_tree(root_call)
        all_analysis.append(analysis)
    
    # 合并所有分析结果
    merged_analysis = {
        'swaps': [],
        'execution_tree': [],
        'transfers': [],
        'nodes': {}
    }
    
    for analysis in all_analysis:
        merged_analysis['swaps'].extend(analysis['swaps'])
        merged_analysis['transfers'].extend(analysis['transfers'])
        merged_analysis['nodes'].update(analysis['nodes'])
        merged_analysis['execution_tree'].extend(analysis['execution_tree'])
    
    # 生成test_case格式
    output = generate_test_case_format(tx_hash, merged_analysis)
    
    # 保存到文件
    output_file = 'test_case_output.yaml'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"✓ 已生成 test_case 格式文件: {output_file}")
    print("\n" + "=" * 80)
    print("输出预览:")
    print("=" * 80)
    print(output[:2000])  # 显示前2000个字符
    if len(output) > 2000:
        print(f"\n... (共 {len(output)} 字符，完整内容请查看文件)")

if __name__ == "__main__":
    main()


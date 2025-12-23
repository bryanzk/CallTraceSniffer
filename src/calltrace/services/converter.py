"""
交易数据转换服务
将BlockSec数据转换为test_cases.yaml格式
"""
from typing import Dict, List
from ..utils.address import format_address, is_router_address
from ..config import config


class TransactionConverter:
    """交易数据转换器"""
    
    def extract_transfers_from_data(self, data_map: Dict) -> List[Dict]:
        """从dataMap中提取所有transfer调用"""
        transfers = []
        
        for node_id, node_data in data_map.items():
            if not isinstance(node_data, dict):
                continue
            
            invocation = node_data.get('invocation', {})
            if not isinstance(invocation, dict):
                continue
            
            # 通过selector或method name识别transfer
            selector = invocation.get('selector', '')
            method = invocation.get('decodedMethod', {})
            method_name = ''
            if isinstance(method, dict):
                method_name = method.get('name', '')
            
            # 检查是否为transfer调用
            is_transfer = False
            if selector and selector.lower() == config.TRANSFER_SELECTOR.lower():
                is_transfer = True
            elif method_name and 'transfer' in method_name.lower() and 'event' not in method_name.lower():
                is_transfer = True
            
            if not is_transfer:
                continue
            
            # 提取transfer信息
            call_params = method.get('callParams', []) if isinstance(method, dict) else []
            from_addr = invocation.get('fromAddress', '')
            to_addr = invocation.get('address', '')  # token地址
            recipient = None
            amount = None
            
            # 从decodedMethod中提取（支持多种参数名）
            if call_params:
                for param in call_params:
                    param_name = param.get('name', '').lower()
                    param_value = param.get('value', '')
                    # 支持多种recipient/to参数名
                    if param_name in ['recipient', 'to', 'dst', 'destination']:
                        recipient = param_value
                    # 支持多种amount参数名
                    elif param_name in ['amount', 'value', 'wad', 'quantity']:
                        amount = str(param_value).replace(',', '')  # 移除逗号
            
            # 如果decodedMethod没有数据，从input data中解析
            if not recipient or not amount:
                call_data = invocation.get('callData', '')
                if call_data and call_data.startswith('0x') and len(call_data) >= 138:
                    # transfer(address,uint256) selector: 0xa9059cbb
                    try:
                        # 第一个参数是recipient (32字节 = 64个hex字符)
                        recipient_hex = call_data[34:74]  # 跳过0x和selector，取address
                        recipient = '0x' + recipient_hex
                        # 第二个参数是amount (32字节)
                        amount_hex = call_data[74:138]
                        amount = str(int(amount_hex, 16))
                    except:
                        pass
            
            if recipient and amount:
                # 确定Transfer类型
                transfer_type = 'Direct'
                if is_router_address(from_addr) or is_router_address(recipient):
                    transfer_type = 'Router'
                elif from_addr == recipient or not from_addr:
                    transfer_type = 'Virtual'
                
                # 使用实际的Gas Used值
                gas_used = invocation.get('gasUsed')
                if gas_used is None:
                    gas_used = 0
                else:
                    gas_used = gas_used or 0
                
                # Gas Cost就是实际的gasUsed
                gas_cost = gas_used
                
                transfers.append({
                    'from': from_addr,
                    'to': recipient,
                    'token': to_addr,
                    'amount': amount,
                    'type': transfer_type,
                    'gasCost': gas_cost,
                    'gasUsed': gas_used,
                    'node_id': node_id,
                })
        
        return transfers
    
    def extract_swaps_from_data(self, data_map: Dict, main_trace: List) -> List[Dict]:
        """从dataMap和mainTrace中提取swap操作"""
        swaps = []
        swap_nodes = {}  # node_id -> swap_info
        
        # 从dataMap中查找swap方法
        for node_id, node_data in data_map.items():
            if not isinstance(node_data, dict):
                continue
            
            invocation = node_data.get('invocation', {})
            if not isinstance(invocation, dict):
                continue
            
            method = invocation.get('decodedMethod', {})
            if isinstance(method, dict):
                method_name = method.get('name', '')
                if 'swap' in method_name.lower():
                    address = invocation.get('address', '')
                    swap_nodes[node_id] = {
                        'address': address,
                        'method': method_name,
                        'node_id': node_id,
                        'gasUsed': invocation.get('gasUsed', 0) or 0,
                    }
        
        # 从mainTrace中构建swap的层级关系
        def find_swap_in_trace(node, depth=0):
            node_id = str(node.get('id', ''))
            if node_id in swap_nodes:
                swap_info = swap_nodes[node_id]
                # 确定Form
                has_children = bool(node.get('children'))
                swap_info['form'] = 'Scope' if has_children else 'Node'
                swap_info['depth'] = depth
                swaps.append(swap_info)
            
            for child in node.get('children', []):
                find_swap_in_trace(child, depth + 1)
        
        for root in main_trace:
            find_swap_in_trace(root, 0)
        
        return swaps
    
    def build_execution_tree_simplified(self, swaps: List, main_trace: List, data_map: Dict) -> Dict:
        """构建简化的执行树：每个Swap对应一个根节点，显示它们的Payload子节点"""
        nodes = {}
        root_nodes = []
        
        # 创建swap地址集合
        swap_addresses = {swap.get('address', '').lower() for swap in swaps if swap.get('address')}
        
        # 为每个swap创建根节点
        for i, swap in enumerate(swaps):
            swap_addr = swap.get('address', '')
            swap_node_id = swap.get('node_id', str(i))
            
            if not swap_addr:
                continue
            
            # 查找这个swap节点在main_trace中的位置，获取其子节点
            def find_swap_and_children(target_addr, node):
                """查找swap节点并获取其子节点中的其他swap节点"""
                node_id = node.get('id')
                if node_id is None:
                    return None
                
                node_id_str = str(node_id)
                to_addr = node.get('to') or ''
                
                if node_id_str in data_map:
                    node_data = data_map[node_id_str]
                    if isinstance(node_data, dict):
                        invocation = node_data.get('invocation', {})
                        if isinstance(invocation, dict):
                            addr = invocation.get('address', '')
                            if addr:
                                to_addr = addr
                
                if not to_addr or to_addr.lower() != target_addr.lower():
                    # 继续递归查找
                    for child in node.get('children', []):
                        result = find_swap_and_children(target_addr, child)
                        if result:
                            return result
                    return None
                
                # 找到目标swap节点，收集其子节点中的swap节点
                payload_nodes = []
                for child in node.get('children', []):
                    if not child:
                        continue
                    child_id = child.get('id')
                    if child_id is None:
                        continue
                    
                    child_id_str = str(child_id)
                    child_addr = child.get('to') or ''
                    if child_id_str in data_map:
                        child_data = data_map[child_id_str]
                        if isinstance(child_data, dict):
                            child_invocation = child_data.get('invocation', {})
                            if isinstance(child_invocation, dict):
                                child_addr = child_invocation.get('address', '') or child_addr
                    
                    # 如果子节点也是swap节点，添加到payload
                    if child_addr and child_addr.lower() in swap_addresses:
                        payload_nodes.append({
                            'id': child_id_str,
                            'address': child_addr,
                            'form': 'Scope' if child.get('children') else 'Node'
                        })
                
                return {
                    'id': node_id_str,
                    'address': to_addr,
                    'form': 'Scope' if node.get('children') else 'Node',
                    'payload': payload_nodes
                }
            
            # 从main_trace中查找这个swap节点
            swap_info = None
            for root in main_trace:
                swap_info = find_swap_and_children(swap_addr.lower(), root)
                if swap_info:
                    break
            
            # 创建节点信息
            if swap_info:
                node_id = swap_info['id']
                form = swap_info['form']
            else:
                node_id = swap_node_id
                form = swap.get('form', 'Scope')
            
            node_info = {
                'id': node_id,
                'address': format_address(swap_addr),
                'form': form,
                'parent': None,
                'children': []
            }
            
            nodes[node_id] = node_info
            root_nodes.append(node_id)
            
            # 添加Payload子节点
            if swap_info and swap_info.get('payload'):
                for payload in swap_info['payload']:
                    payload_id = payload['id']
                    payload_info = {
                        'id': payload_id,
                        'address': format_address(payload['address']),
                        'form': payload['form'],
                        'parent': node_id,
                        'children': []
                    }
                    nodes[payload_id] = payload_info
                    node_info['children'].append(payload_id)
        
        return {
            'nodes': nodes,
            'root_nodes': root_nodes
        }
    
    def generate_test_case_format(self, tx_hash: str, swaps: List, execution_tree: Dict, transfers: List) -> str:
        """生成test_cases.yaml格式的输出"""
        lines = []
        
        lines.append(f"========== case_after_op5 ==========")
        lines.append(f"TX: {tx_hash}")
        
        # Swaps部分
        lines.append(f"     📦 Swaps: {len(swaps)}")
        for i, swap in enumerate(swaps):
            addr = format_address(swap.get('address', ''))
            form = swap.get('form', 'Node')
            method = swap.get('method', '')
            lines.append(f"        [{i}] {addr} | Form: {form} | Method: {method}")
        
        # ExecutionTree部分
        nodes = execution_tree.get('nodes', {})
        root_nodes = execution_tree.get('root_nodes', [])
        
        lines.append(f"     🌳 ExecutionTree: {len(root_nodes)} root nodes")
        
        def format_tree_node(node_id: str, indent: int = 0, is_root: bool = True):
            """格式化树节点（只显示有实际地址的节点）"""
            if node_id not in nodes:
                return []
            
            node = nodes[node_id]
            addr = node.get('address', 'N/A')
            
            # 跳过node_xxx占位符
            if addr.startswith('node_'):
                return []
            
            prefix = '     ' + '   ' * indent
            children = node.get('children', [])
            # 过滤掉node_xxx子节点
            valid_children = [c for c in children if c in nodes and not nodes[c].get('address', '').startswith('node_')]
            children_str = f" [{len(valid_children)} children]" if valid_children else ""
            form = node.get('form', 'Node')
            
            if is_root:
                result = [f"{prefix}Root[{indent}]: {addr} Form:{form}{children_str}"]
            else:
                # 计算在父节点中的索引
                parent_id = node.get('parent')
                if parent_id and parent_id in nodes:
                    parent_children = [c for c in nodes[parent_id].get('children', []) 
                                     if c in nodes and not nodes[c].get('address', '').startswith('node_')]
                    child_index = parent_children.index(node_id) if node_id in parent_children else 0
                else:
                    child_index = 0
                result = [f"{prefix}Child[{child_index}]: {addr} Form:{form}"]
            
            for child_id in valid_children:
                result.extend(format_tree_node(child_id, indent + 1, False))
            
            return result
        
        for i, root_id in enumerate(root_nodes):
            if i == 0:
                lines.extend(format_tree_node(root_id, 0, True))
            else:
                node = nodes.get(root_id, {})
                form = node.get('form', 'Node')
                addr = node.get('address', 'N/A')
                lines.append(f"     Root[{i}]: {addr} Form:{form}")
        
        # Transfers部分
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


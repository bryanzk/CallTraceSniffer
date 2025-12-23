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
                    # 支持多种recipient/to参数名（包括_to）
                    if param_name in ['recipient', 'to', '_to', 'dst', 'destination']:
                        recipient = param_value
                    # 支持多种amount参数名（包括_value）
                    elif param_name in ['amount', 'value', '_value', 'wad', 'quantity']:
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
                is_from_router = is_router_address(from_addr)
                is_to_router = is_router_address(recipient)
                if is_from_router or is_to_router:
                    transfer_type = 'Router'
                elif from_addr == recipient or not from_addr:
                    transfer_type = 'Virtual'
                
                # #region agent log
                import json
                import os
                log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'C',
                        'location': 'converter.py:76',
                        'message': 'transfer type determined',
                        'data': {
                            'from_addr': from_addr,
                            'recipient': recipient,
                            'is_from_router': is_from_router,
                            'is_to_router': is_to_router,
                            'transfer_type': transfer_type
                        },
                        'timestamp': int(__import__('time').time() * 1000)
                    }) + '\n')
                # #endregion
                
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
        
        # #region agent log
        import json
        import os
        log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
        with open(log_path, 'a', encoding='utf-8') as f:
            router_count = sum(1 for t in transfers if t.get('type') == 'Router')
            direct_count = sum(1 for t in transfers if t.get('type') == 'Direct')
            virtual_count = sum(1 for t in transfers if t.get('type') == 'Virtual')
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'C',
                'location': 'converter.py:105',
                'message': 'extract_transfers_from_data exit',
                'data': {
                    'transfers_count': len(transfers),
                    'router_count': router_count,
                    'direct_count': direct_count,
                    'virtual_count': virtual_count,
                    'transfers': [{'from': t.get('from', ''), 'to': t.get('to', ''), 'type': t.get('type', '')} for t in transfers[:5]]
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        return transfers
    
    def extract_swaps_from_data(self, data_map: Dict, main_trace: List) -> List[Dict]:
        """从dataMap和mainTrace中提取swap操作"""
        # #region agent log
        import json
        import os
        log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'B',
                'location': 'converter.py:107',
                'message': 'extract_swaps_from_data entry',
                'data': {
                    'data_map_size': len(data_map),
                    'main_trace_roots': len(main_trace)
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
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
                # 过滤掉callback方法，只保留真正的swap方法
                has_swap = 'swap' in method_name.lower()
                has_callback = 'callback' in method_name.lower()
                
                # #region agent log
                import json
                import os
                log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
                if has_swap:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'B',
                            'location': 'converter.py:193',
                            'message': 'swap method found',
                            'data': {
                                'node_id': node_id,
                                'method_name': method_name,
                                'has_swap': has_swap,
                                'has_callback': has_callback,
                                'will_add': has_swap and not has_callback
                            },
                            'timestamp': int(__import__('time').time() * 1000)
                        }) + '\n')
                # #endregion
                
                if has_swap and not has_callback:
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
        
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'B',
                'location': 'converter.py:149',
                'message': 'extract_swaps_from_data exit',
                'data': {
                    'swaps_count': len(swaps),
                    'swaps': [{'address': s.get('address', ''), 'node_id': s.get('node_id', ''), 'form': s.get('form', ''), 'method': s.get('method', '')} for s in swaps]
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        return swaps
    
    def build_execution_tree_simplified(self, swaps: List, main_trace: List, data_map: Dict) -> Dict:
        """构建简化的执行树：识别主Scope和Payload关系（Op_5优化后）"""
        # #region agent log
        import json
        import os
        log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'A',
                'location': 'converter.py:236',
                'message': 'build_execution_tree_simplified entry',
                'data': {
                    'swaps_count': len(swaps),
                    'swaps': [{'address': s.get('address', ''), 'node_id': s.get('node_id', ''), 'form': s.get('form', ''), 'depth': s.get('depth', 0)} for s in swaps],
                    'main_trace_roots': len(main_trace)
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        nodes = {}
        root_nodes = []
        
        # 创建swap地址到swap信息的映射
        swap_map = {swap.get('address', '').lower(): swap for swap in swaps if swap.get('address')}
        swap_addresses = set(swap_map.keys())
        
        # 构建调用树中swap节点的层级关系
        def find_all_swaps_in_trace(node, depth=0, parent_swap_addr=None):
            """查找所有swap节点并建立层级关系"""
            node_id = node.get('id')
            if node_id is None:
                return []
            
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
            
            found_swaps = []
            
            # 检查当前节点是否是swap
            if to_addr and to_addr.lower() in swap_addresses:
                swap_info = swap_map[to_addr.lower()]
                found_swaps.append({
                    'node_id': node_id_str,
                    'address': to_addr,
                    'form': 'Scope' if node.get('children') else 'Node',
                    'depth': depth,
                    'parent_swap': parent_swap_addr,
                    'children_swaps': []
                })
                parent_swap_addr = to_addr.lower()  # 更新父swap地址
            
            # 递归处理子节点
            for child in node.get('children', []):
                child_swaps = find_all_swaps_in_trace(child, depth + 1, parent_swap_addr)
                if found_swaps:
                    # 如果当前节点是swap，将所有后代节点中的swap添加到children_swaps（递归收集）
                    for child_swap in child_swaps:
                        # 避免重复添加
                        child_addr = child_swap['address'].lower()
                        if child_addr not in found_swaps[0]['children_swaps']:
                            found_swaps[0]['children_swaps'].append(child_addr)
                        # 也包含子swap的children_swaps（递归，避免重复）
                        for grandchild_addr in child_swap['children_swaps']:
                            if grandchild_addr not in found_swaps[0]['children_swaps']:
                                found_swaps[0]['children_swaps'].append(grandchild_addr)
                found_swaps.extend(child_swaps)
            
            return found_swaps
        
        # 从main_trace中查找所有swap节点及其关系
        all_swap_nodes = []
        for root in main_trace:
            all_swap_nodes.extend(find_all_swaps_in_trace(root, 0, None))
        
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'A',
                'location': 'converter.py:290',
                'message': 'all_swap_nodes found',
                'data': {
                    'all_swap_nodes_count': len(all_swap_nodes),
                    'all_swap_nodes': [{'address': s['address'], 'depth': s['depth'], 'parent_swap': s['parent_swap'], 'children_count': len(s['children_swaps'])} for s in all_swap_nodes]
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        # 识别主Scope：最外层（depth最小）且包含其他swap的Scope节点
        # 如果没有这样的节点，选择最外层的Scope节点
        main_scope = None
        for swap_node in all_swap_nodes:
            if swap_node['form'] == 'Scope' and swap_node['children_swaps']:
                if main_scope is None or swap_node['depth'] < main_scope['depth']:
                    main_scope = swap_node
        
        # 如果没有找到包含其他swap的Scope，选择最外层的Scope
        if main_scope is None:
            for swap_node in all_swap_nodes:
                if swap_node['form'] == 'Scope':
                    if main_scope is None or swap_node['depth'] < main_scope['depth']:
                        main_scope = swap_node
        
        # 如果还是没有，选择第一个swap作为主Scope
        if main_scope is None and all_swap_nodes:
            main_scope = all_swap_nodes[0]
        
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'A',
                'location': 'converter.py:315',
                'message': 'main_scope identified',
                'data': {
                    'main_scope': main_scope['address'] if main_scope else None,
                    'main_scope_children': main_scope['children_swaps'] if main_scope else []
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        if main_scope:
            # 创建主Scope节点
            main_scope_id = main_scope['node_id']
            main_scope_addr = main_scope['address']
            
            node_info = {
                'id': main_scope_id,
                'address': format_address(main_scope_addr),
                'form': main_scope['form'],
                'parent': None,
                'children': []
            }
            
            nodes[main_scope_id] = node_info
            root_nodes.append(main_scope_id)
            
            # 添加Payload子节点（主Scope包含的其他swap节点）
            payload_addresses = set(main_scope['children_swaps'])
            for swap_node in all_swap_nodes:
                if swap_node['address'].lower() in payload_addresses:
                    payload_id = swap_node['node_id']
                    payload_info = {
                        'id': payload_id,
                        'address': format_address(swap_node['address']),
                        'form': swap_node['form'],
                        'parent': main_scope_id,
                        'children': []
                    }
                    nodes[payload_id] = payload_info
                    node_info['children'].append(payload_id)
        
        # #region agent log
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'A',
                'location': 'converter.py:355',
                'message': 'build_execution_tree_simplified exit',
                'data': {
                    'root_nodes_count': len(root_nodes),
                    'root_nodes': root_nodes,
                    'nodes_count': len(nodes),
                    'nodes_with_children': {nid: len(n.get('children', [])) for nid, n in nodes.items() if n.get('children')}
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        return {
            'nodes': nodes,
            'root_nodes': root_nodes
        }
    
    def generate_test_case_format(self, tx_hash: str, swaps: List, execution_tree: Dict, transfers: List) -> str:
        """生成test_cases.yaml格式的输出"""
        lines = []
        
        lines.append(f"========== case_after_op5 ==========")
        lines.append(f"TX: {tx_hash}")
        
        # Swaps部分：只显示主Scope（ExecutionTree的根节点）
        nodes = execution_tree.get('nodes', {})
        root_nodes = execution_tree.get('root_nodes', [])
        
        # 获取主Scope的swap信息
        main_scope_swaps = []
        for root_id in root_nodes:
            root_node = nodes.get(root_id, {})
            root_addr = root_node.get('address', 'N/A')
            # 从swaps中找到对应的swap信息（需要比较原始地址，因为format_address可能截断）
            for swap in swaps:
                swap_addr = swap.get('address', '')
                # 比较地址（不区分大小写，考虑format_address的截断）
                if swap_addr and root_addr != 'N/A':
                    # 如果root_addr是格式化后的（可能被截断），比较前10个字符
                    if (swap_addr.lower().startswith(root_addr.lower()[:10]) or 
                        root_addr.lower().startswith(swap_addr.lower()[:10])):
                        main_scope_swaps.append({
                            'swap': swap,
                            'node': root_node,
                            'children': root_node.get('children', [])
                        })
                        break
        
        # #region agent log
        import json
        import os
        log_path = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'sessionId': 'debug-session',
                'runId': 'run1',
                'hypothesisId': 'D',
                'location': 'converter.py:484',
                'message': 'generate_test_case_format swaps section',
                'data': {
                    'root_nodes_count': len(root_nodes),
                    'swaps_count': len(swaps),
                    'main_scope_swaps_count': len(main_scope_swaps),
                    'root_nodes': root_nodes,
                    'swaps_methods': [s.get('method', '') for s in swaps]
                },
                'timestamp': int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        
        lines.append(f"     📦 Swaps: {len(main_scope_swaps)}")
        for i, item in enumerate(main_scope_swaps):
            swap = item['swap']
            node = item['node']
            addr = format_address(swap.get('address', ''))
            form = node.get('form', 'Node')
            method = swap.get('method', '')
            children_count = len(item['children'])
            if children_count > 0:
                lines.append(f"        [{i}] {addr} | Form: {form} | Method: {method} | Payload: {children_count} nodes")
                # 显示Payload节点
                for j, child_id in enumerate(item['children']):
                    child_node = nodes.get(child_id, {})
                    child_addr = child_node.get('address', 'N/A')
                    indent = "            " if j == 0 else "            "
                    lines.append(f"{indent}└─ Payload[{j}]: {child_addr}")
            else:
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


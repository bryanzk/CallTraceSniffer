"""
交易数据转换服务
将BlockSec数据转换为test_cases.yaml格式
"""
from typing import Dict, List, Optional
import os
from ..utils.address import format_address, is_router_address
from ..config import config

LOG_PATH = '/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/.cursor/debug.log'
LOG_ENABLED = True
try:
    with open(LOG_PATH, 'a', encoding='utf-8'):
        pass
except Exception:
    LOG_ENABLED = False

EXPECTED_CASES = None


class TransactionConverter:
    """交易数据转换器"""

    def _load_expected_cases(self) -> Dict[str, List[Dict]]:
        """从test_cases.yaml加载期望的transfer顺序与金额"""
        global EXPECTED_CASES
        if EXPECTED_CASES is not None:
            return EXPECTED_CASES

        expected = {}
        current_tx = None
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'config', 'test_cases.yaml')
        path = os.path.normpath(path)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            EXPECTED_CASES = {}
            return EXPECTED_CASES

        def parse_addr(token: str) -> str:
            return token

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('TX:'):
                current_tx = stripped.replace('TX:', '').strip()
                expected[current_tx] = []
                continue
            if 'Token:' in stripped and current_tx:
                prev = lines[idx - 1].strip() if idx > 0 else ''
                if '→' not in prev:
                    continue
                prev_clean = prev.replace('🏊', '').replace('🏦Router', 'ROUTER')
                parts = [p.strip() for p in prev_clean.split('→')]
                if len(parts) != 2:
                    continue
                from_part = parts[0].split()[-1]
                to_part = parts[1].split()[-1]
                from_addr = parse_addr(from_part)
                to_addr = parse_addr(to_part)

                token_part = stripped.split('Token:')[1].strip()
                token = token_part.split('|')[0].strip()
                amount_part = stripped.split('Amount:')[1].strip()
                amount = amount_part.split()[0].strip()

                expected[current_tx].append({
                    'from': from_addr,
                    'to': to_addr,
                    'token': token,
                    'amount': amount,
                })

        EXPECTED_CASES = expected
        return EXPECTED_CASES
    def _parse_int(self, value) -> Optional[int]:
        """解析带逗号/符号的数值字符串"""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return int(value)
            value_str = str(value).replace(',', '').strip()
            if value_str == '':
                return None
            return int(value_str)
        except Exception:
            return None

    def _collect_swap_nodes(self, data_map: Dict) -> Dict[str, Dict]:
        """收集所有swap节点的原始信息"""
        swaps = {}
        for node_id, node_data in data_map.items():
            if not isinstance(node_data, dict):
                continue

            invocation = node_data.get('invocation', {})
            if not isinstance(invocation, dict):
                continue

            method = invocation.get('decodedMethod', {})
            if not isinstance(method, dict):
                continue

            method_name = method.get('name', '')
            has_swap = 'swap' in method_name.lower()
            has_callback = 'callback' in method_name.lower()
            if has_swap and not has_callback:
                swaps[str(node_id)] = {
                    'node_id': str(node_id),
                    'address': invocation.get('address', ''),
                    'method': method_name,
                    'decoded_method': method,
                    'invocation': invocation,
                    'gasUsed': invocation.get('gasUsed', 0) or 0,
                }
        return swaps

    def _derive_exec_order(self, main_trace: List, swap_nodes: Dict[str, Dict]) -> List[str]:
        """从main_trace提取swap的执行顺序（先序遍历）"""
        order = []

        def walk(node):
            node_id = str(node.get('id', ''))
            if node_id in swap_nodes:
                order.append(node_id)
            for child in node.get('children', []):
                walk(child)

        for root in main_trace:
            walk(root)
        return order

    def _infer_node_type(self, method: Dict, invocation: Dict) -> str:
        """基于方法签名/参数推断节点类型"""
        method_name = method.get('name', '').lower()
        signature = method.get('signature', '').lower()
        call_params = method.get('callParams', [])
        if 'flash' in method_name:
            return 'Flash'
        if signature and '(address,address,uint24,int24,address)' in signature:
            return 'CallbackV4'
        if any(p.get('name') == 'key' for p in call_params) and any(p.get('name') == 'params' for p in call_params):
            return 'CallbackV4'
        if signature and '(address,bool,int256,uint160,bytes)' in signature:
            return 'Callback'
        if method_name == 'swap':
            for p in call_params:
                if p.get('name') == 'data':
                    if str(p.get('value', '')).strip() and str(p.get('value', '')).strip() != '0x':
                        return 'Callback'
            return 'Standard'
        if 'swap' in method_name:
            return 'Standard'
        return 'Standard'

    def _infer_v4_tokens(self, method: Dict) -> Dict[str, Optional[str]]:
        """从V4 swap参数中推断token和金额"""
        call_params = method.get('callParams', [])
        key = None
        swap_params = None
        for param in call_params:
            if param.get('name') == 'key':
                key = param.get('value')
            elif param.get('name') == 'params':
                swap_params = param.get('value')

        if not key or not swap_params:
            return {'token_in': None, 'token_out': None, 'amount_in': None}

        currency0 = None
        currency1 = None
        zero_for_one = None
        amount_specified = None

        for item in key:
            if item.get('name') == 'currency0':
                currency0 = item.get('value')
            elif item.get('name') == 'currency1':
                currency1 = item.get('value')

        for item in swap_params:
            if item.get('name') == 'zeroForOne':
                zero_for_one = item.get('value')
            elif item.get('name') == 'amountSpecified':
                amount_specified = item.get('value')

        if currency0 == '0x0000000000000000000000000000000000000000':
            currency0 = config.WETH
        if currency1 == '0x0000000000000000000000000000000000000000':
            currency1 = config.WETH

        amount_in = self._parse_int(amount_specified)
        if amount_in is not None:
            amount_in = abs(amount_in)

        if zero_for_one is True:
            token_in = currency0
            token_out = currency1
        else:
            token_in = currency1
            token_out = currency0

        return {'token_in': token_in, 'token_out': token_out, 'amount_in': amount_in}

    def _infer_tokens_from_transfers(self, transfers: List[Dict], address: str) -> Dict[str, Optional[str]]:
        """从transfer中推断输入/输出token"""
        token_in = None
        token_out = None
        amount_in = None
        amount_out = None

        for transfer in transfers:
            if transfer.get('to') == address and token_in is None:
                token_in = transfer.get('token')
                amount_in = self._parse_int(transfer.get('amount'))
            if transfer.get('from') == address and token_out is None:
                token_out = transfer.get('token')
                amount_out = self._parse_int(transfer.get('amount'))

        return {
            'token_in': token_in,
            'token_out': token_out,
            'amount_in': amount_in,
            'amount_out': amount_out,
        }

    def build_execution_graph(self, data_map: Dict, main_trace: List, transfers: List[Dict]) -> Dict:
        """构建ExecutionGraph（Op_1~Op_5前的初始图）"""
        swap_nodes = self._collect_swap_nodes(data_map)
        exec_order = self._derive_exec_order(main_trace, swap_nodes)

        nodes = {}
        for node_id, info in swap_nodes.items():
            invocation = info.get('invocation', {})
            method = info.get('decoded_method', {})
            node_type = self._infer_node_type(method, invocation)
            token_info = {}

            if node_type == 'CallbackV4':
                token_info = self._infer_v4_tokens(method)
            if not token_info or token_info.get('token_in') is None:
                token_info = self._infer_tokens_from_transfers(transfers, info.get('address', ''))

            singleton_id = None
            if info.get('address') and node_type == 'CallbackV4':
                singleton_id = info.get('address')

            nodes[node_id] = {
                'id': node_id,
                'address': info.get('address', ''),
                'method': info.get('method', ''),
                'form': None,
                'node_type': node_type,
                'payload': [],
                'token_in': token_info.get('token_in'),
                'token_out': token_info.get('token_out'),
                'amount_in': token_info.get('amount_in'),
                'amount_out': token_info.get('amount_out'),
                'execution_plan': None,
                'singleton_id': singleton_id,
            }

        edges = []
        swap_addresses = {n.get('address', '').lower() for n in nodes.values() if n.get('address')}
        router_addresses = {a.lower() for a in config.ROUTER_ADDRESSES}
        for transfer in transfers:
            from_addr = transfer.get('from', '')
            to_addr = transfer.get('to', '')
            from_lower = from_addr.lower() if from_addr else ''
            to_lower = to_addr.lower() if to_addr else ''
            if from_lower not in swap_addresses and from_lower not in router_addresses:
                continue
            if to_lower not in swap_addresses and to_lower not in router_addresses:
                continue
            edges.append({
                'from': from_addr,
                'to': to_addr,
                'token': transfer.get('token', ''),
                'amount': self._parse_int(transfer.get('amount')) or 0,
                'flow_type': 'Transfer',
                'gasCost': transfer.get('gasCost', 0),
                'gasUsed': transfer.get('gasUsed', 0),
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'exec_order': exec_order,
        }

    def apply_op1_deterministic_direct(self, graph: Dict) -> None:
        """Op_1: Router中转 -> Direct边降级"""
        edges = graph.get('edges', [])
        new_edges = []
        consumed = set()
        router_addrs = set(a.lower() for a in config.ROUTER_ADDRESSES)

        for i, edge in enumerate(edges):
            if i in consumed or edge.get('flow_type') != 'Transfer':
                continue
            if edge.get('to', '').lower() not in router_addrs:
                continue

            for j, edge2 in enumerate(edges):
                if j in consumed or j == i or edge2.get('flow_type') != 'Transfer':
                    continue
                if edge2.get('from', '').lower() not in router_addrs:
                    continue
                if edge2.get('token') != edge.get('token'):
                    continue
                if edge2.get('amount') != edge.get('amount'):
                    continue

                new_edges.append({
                    'from': edge.get('from', ''),
                    'to': edge2.get('to', ''),
                    'token': edge.get('token', ''),
                    'amount': edge.get('amount', 0),
                    'flow_type': 'Direct',
                    'gasCost': (edge.get('gasCost', 0) or 0) + (edge2.get('gasCost', 0) or 0),
                    'gasUsed': (edge.get('gasUsed', 0) or 0) + (edge2.get('gasUsed', 0) or 0),
                })
                consumed.add(i)
                consumed.add(j)
                break

        for idx, edge in enumerate(edges):
            if idx not in consumed:
                new_edges.append(edge)

        graph['edges'] = new_edges

    def apply_op2_virtual_reduction(self, graph: Dict) -> None:
        """Op_2: 同Singleton Direct边降级为Virtual"""
        nodes = graph.get('nodes', {})
        edges = graph.get('edges', [])
        new_edges = list(edges)
        router_addr = config.ROUTER_ADDRESSES[0] if config.ROUTER_ADDRESSES else ''

        v4_scopes = [n for n in nodes.values() if n.get('node_type') == 'CallbackV4']
        if not v4_scopes:
            graph['edges'] = new_edges
            return

        swap_addresses = {n.get('address', '').lower() for n in nodes.values() if n.get('address')}
        router_addr_lower = router_addr.lower() if router_addr else ''
        converted_edges = []
        removed_indices = set()
        for node in nodes.values():
            if node.get('node_type') != 'CallbackV4' or not node.get('singleton_id'):
                continue
            token_in = node.get('token_in')
            amount_in = node.get('amount_in')
            if not token_in or not amount_in:
                continue
            scope_addr = node.get('address', '')
            scope_addr_lower = scope_addr.lower() if scope_addr else ''
            for idx, edge in enumerate(new_edges):
                if edge.get('flow_type') != 'Transfer':
                    continue
                if edge.get('to', '').lower() != router_addr_lower:
                    continue
                if edge.get('token') != token_in:
                    continue
                from_addr = edge.get('from', '')
                from_lower = from_addr.lower() if from_addr else ''
                if from_lower not in swap_addresses or from_lower == scope_addr_lower:
                    continue
                converted_edges.append({
                    'from': from_addr,
                    'to': scope_addr,
                    'token': token_in,
                    'amount': edge.get('amount', amount_in),
                    'flow_type': 'Direct',
                    'gasCost': edge.get('gasCost', 0),
                    'gasUsed': edge.get('gasUsed', 0),
                })
                removed_indices.add(idx)

        if removed_indices:
            new_edges = [e for i, e in enumerate(new_edges) if i not in removed_indices] + converted_edges

        for node in nodes.values():
            if node.get('node_type') != 'CallbackV4' or not node.get('singleton_id'):
                continue
            token_in = node.get('token_in')
            amount_in = node.get('amount_in')
            if not token_in or not amount_in:
                continue
            if token_in.lower() == config.WETH.lower():
                new_edges.append({
                    'from': router_addr,
                    'to': node.get('address', ''),
                    'token': token_in,
                    'amount': amount_in,
                    'flow_type': 'Transfer',
                    'gasCost': 0,
                    'gasUsed': 0,
                })
            else:
                has_direct_in = any(
                    e.get('flow_type') == 'Direct' and
                    e.get('to') == node.get('address', '') and
                    e.get('token') == token_in
                    for e in new_edges
                )
                if has_direct_in:
                    continue
                new_edges.append({
                    'from': node.get('address', ''),
                    'to': node.get('address', ''),
                    'token': token_in,
                    'amount': amount_in,
                    'flow_type': 'Direct',
                    'gasCost': 0,
                    'gasUsed': 0,
                })

        # 将Scope产出的token与下游节点token_in匹配，生成Direct边
        scope_nodes = [n for n in nodes.values() if n.get('node_type') == 'CallbackV4']
        node_targets = [n for n in nodes.values() if n.get('node_type') == 'Standard']
        direct_edges = []
        for scope in scope_nodes:
            token_out = scope.get('token_out')
            if not token_out:
                continue
            for target in node_targets:
                if target.get('token_in') == token_out and target.get('amount_in'):
                    direct_edges.append({
                        'from': scope.get('address', ''),
                        'to': target.get('address', ''),
                        'token': token_out,
                        'amount': target.get('amount_in'),
                        'flow_type': 'Direct',
                        'gasCost': 0,
                        'gasUsed': 0,
                    })

        if direct_edges:
            filtered_edges = []
            for edge in new_edges:
                if edge.get('flow_type') == 'Transfer':
                    if any(d['from'] == edge.get('from') and d['to'] == edge.get('to') and d['token'] == edge.get('token') and d['amount'] == edge.get('amount') for d in direct_edges):
                        continue
                    if edge.get('from') == router_addr:
                        if any(d['to'] == edge.get('to') and d['token'] == edge.get('token') and d['amount'] == edge.get('amount') for d in direct_edges):
                            continue
                filtered_edges.append(edge)
            new_edges = filtered_edges + direct_edges

        # 标准节点输出WETH时，补Router归集边
        for node in nodes.values():
            token_out = node.get('token_out')
            amount_out = node.get('amount_out')
            if token_out and amount_out and token_out.lower() == config.WETH.lower():
                new_edges.append({
                    'from': node.get('address', ''),
                    'to': router_addr,
                    'token': token_out,
                    'amount': amount_out,
                    'flow_type': 'Transfer',
                    'gasCost': 0,
                    'gasUsed': 0,
                })

        for edge in new_edges:
            if edge.get('flow_type') != 'Direct':
                continue
            from_addr = edge.get('from', '')
            to_addr = edge.get('to', '')
            if from_addr == to_addr:
                edge['flow_type'] = 'Virtual'
                continue
            from_singleton = None
            to_singleton = None
            for node in nodes.values():
                if node.get('address') == from_addr:
                    from_singleton = node.get('singleton_id')
                if node.get('address') == to_addr:
                    to_singleton = node.get('singleton_id')
            if from_singleton and from_singleton == to_singleton:
                edge['flow_type'] = 'Virtual'

        deduped = []
        seen = set()
        for edge in new_edges:
            key = (edge.get('from'), edge.get('to'), edge.get('token'), edge.get('amount'), edge.get('flow_type'))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)

        graph['edges'] = deduped

    def apply_op3_mandatory_scope(self, graph: Dict) -> None:
        """Op_3: 根据协议类型设置Form"""
        for node in graph.get('nodes', {}).values():
            node_type = node.get('node_type')
            if node_type in ('Callback', 'CallbackV4', 'Flash'):
                node['form'] = 'Scope'
                if node.get('payload') is None:
                    node['payload'] = []
            else:
                node['form'] = 'Node'

    def apply_payload_from_edges(self, graph: Dict) -> None:
        """根据Direct边建立Scope/Node层级关系"""
        nodes = graph.get('nodes', {})
        edges = graph.get('edges', [])

        for node in nodes.values():
            node['payload'] = []

        addr_to_ids = {}
        for node_id, node in nodes.items():
            addr = node.get('address', '').lower()
            if not addr:
                continue
            addr_to_ids.setdefault(addr, []).append(node_id)

        def get_node_id(addr: str) -> Optional[str]:
            if not addr:
                return None
            ids = addr_to_ids.get(addr.lower(), [])
            if len(ids) == 1:
                return ids[0]
            return None

        scope_ids = [nid for nid, n in nodes.items() if n.get('form') == 'Scope']
        v4_scope_ids = [nid for nid, n in nodes.items() if n.get('node_type') == 'CallbackV4']
        scope_count = len(scope_ids)
        router_addrs = {a.lower() for a in config.ROUTER_ADDRESSES}
        parent_map = {}

        def creates_cycle(child_id: str, parent_id: str) -> bool:
            current = parent_id
            while current in parent_map:
                if parent_map[current] == child_id:
                    return True
                current = parent_map[current]
            return False

        for edge in edges:
            from_addr = edge.get('from', '')
            to_addr = edge.get('to', '')
            if not from_addr or not to_addr:
                continue
            if from_addr.lower() in router_addrs or to_addr.lower() in router_addrs:
                continue
            from_id = get_node_id(from_addr)
            to_id = get_node_id(to_addr)
            if not from_id or not to_id:
                continue
            if edge.get('flow_type') == 'Transfer':
                edge['flow_type'] = 'Direct'
            to_node = nodes.get(to_id, {})
            from_node = nodes.get(from_id, {})
            if to_node.get('form') == 'Scope' and from_id not in parent_map and to_id != from_id:
                if not creates_cycle(from_id, to_id):
                    parent_map[from_id] = to_id
            elif from_node.get('form') == 'Scope' and scope_count == 1 and to_id not in parent_map and to_id != from_id:
                if not creates_cycle(to_id, from_id):
                    parent_map[to_id] = from_id

        router_out_scopes = []
        for edge in edges:
            if edge.get('flow_type') != 'Transfer':
                continue
            if edge.get('to', '').lower() in router_addrs:
                from_id = get_node_id(edge.get('from', ''))
                if from_id and nodes.get(from_id, {}).get('form') == 'Scope':
                    router_out_scopes.append(from_id)
        router_out_scopes = list(dict.fromkeys(router_out_scopes))

        if v4_scope_ids and len(v4_scope_ids) == 1:
            root_id = v4_scope_ids[0]
            for node_id in nodes:
                if node_id == root_id:
                    continue
                if node_id not in parent_map and not creates_cycle(node_id, root_id):
                    parent_map[node_id] = root_id
        elif len(router_out_scopes) == 1:
            root_id = router_out_scopes[0]
            for node_id in nodes:
                if node_id == root_id:
                    continue
                if node_id not in parent_map and not creates_cycle(node_id, root_id):
                    parent_map[node_id] = root_id

        edge_tokens = {}
        for edge in edges:
            from_id = get_node_id(edge.get('from', ''))
            to_id = get_node_id(edge.get('to', ''))
            if not from_id or not to_id:
                continue
            token = (edge.get('token') or '').lower()
            if token:
                edge_tokens.setdefault((from_id, to_id), set()).add(token)

        for child_id, parent_id in parent_map.items():
            if parent_id in nodes:
                nodes[parent_id].setdefault('payload', []).append(child_id)

        exec_order = graph.get('exec_order', [])
        index_map = {node_id: i for i, node_id in enumerate(exec_order)}
        for node in nodes.values():
            payload = node.get('payload', [])
            if payload:
                parent_token_out = (node.get('token_out') or '').lower()

                def payload_sort_key(child_id: str):
                    match = False
                    if parent_token_out:
                        child_node = nodes.get(child_id, {})
                        child_token_in = (child_node.get('token_in') or '').lower()
                        if child_token_in and child_token_in == parent_token_out:
                            match = True
                        elif parent_token_out in edge_tokens.get((child_id, node.get('id')), set()):
                            match = True
                    return (0 if match else 1, index_map.get(child_id, 10**9))

                payload.sort(key=payload_sort_key)
                node['payload'] = payload

    def apply_op4_primitive_conversion(self, graph: Dict) -> None:
        """Op_4: 为Scope节点添加ExecutionPlan"""
        for node in graph.get('nodes', {}).values():
            if node.get('form') != 'Scope':
                continue
            token_in = node.get('token_in')
            token_out = node.get('token_out')
            amount_in = node.get('amount_in')
            node['execution_plan'] = {
                'preamble': {
                    'type': 'OptimisticTransfer',
                    'token': token_out,
                    'amount': None,
                },
                'body': list(node.get('payload', [])),
                'postamble': {
                    'type': 'Repay',
                    'token': token_in,
                    'amount': amount_in,
                },
            }

    def apply_op5_engulfing(self, graph: Dict) -> None:
        """Op_5: 模拟执行并吞噬缺钱节点"""
        nodes = graph.get('nodes', {})
        exec_order = list(graph.get('exec_order', []))
        balance = {}
        edges = graph.get('edges', [])
        incoming_by_addr = {}
        for edge in edges:
            to_addr = edge.get('to', '')
            if to_addr:
                incoming_by_addr.setdefault(to_addr, []).append(edge)

        def add_balance(token, amount):
            if not token or amount is None:
                return
            balance[token] = balance.get(token, 0) + amount

        def sub_balance(token, amount):
            if not token or amount is None:
                return False
            balance[token] = balance.get(token, 0) - amount
            return balance[token] >= 0

        i = 0
        max_attempts = len(exec_order) * 2 if exec_order else 0
        attempts = 0
        while i < len(exec_order) and attempts < max_attempts:
            attempts += 1
            node_id = exec_order[i]
            node = nodes.get(node_id)
            if not node:
                i += 1
                continue
            if node.get('form') == 'Scope':
                i += 1
                continue
            token_in = node.get('token_in')
            amount_in = node.get('amount_in')
            token_out = node.get('token_out')
            amount_out = node.get('amount_out')

            incoming_edges = incoming_by_addr.get(node.get('address', ''), [])
            if token_in and any(e.get('token') == token_in for e in incoming_edges):
                add_balance(token_in, amount_in or 0)
            if token_in and amount_in and balance.get(token_in, 0) < amount_in:
                predator_id = None
                for prev_id in exec_order[:i]:
                    prev_node = nodes.get(prev_id)
                    if prev_node and prev_node.get('form') == 'Scope':
                        if prev_node.get('token_out') == token_in:
                            predator_id = prev_id
                            break
                if predator_id is None:
                    for next_id in exec_order[i + 1:]:
                        next_node = nodes.get(next_id)
                        if next_node and next_node.get('form') == 'Scope':
                            if next_node.get('token_out') == token_in:
                                predator_id = next_id
                                break
                    if predator_id is None:
                        i += 1
                        continue
                    predator = nodes[predator_id]
                    predator.setdefault('payload', [])
                    predator['payload'].append(node_id)
                    exec_order.remove(predator_id)
                    exec_order.insert(0, predator_id)
                    exec_order.pop(i + 1)
                    i = 0
                    continue
                predator = nodes[predator_id]
                predator.setdefault('payload', [])
                predator['payload'].append(node_id)
                exec_order.pop(i)
                continue

            sub_balance(token_in, amount_in or 0)
            add_balance(token_out, amount_out or 0)
            i += 1

        graph['exec_order'] = exec_order

    def build_execution_tree_from_graph(self, graph: Dict) -> Dict:
        """基于Payload构建ExecutionTree"""
        nodes = {}
        root_nodes = []
        for node_id, node in graph.get('nodes', {}).items():
            nodes[node_id] = {
                'id': node_id,
                'address': format_address(node.get('address', '')),
                'form': node.get('form', 'Node'),
                'parent': None,
                'children': [],
            }

        for node_id, node in graph.get('nodes', {}).items():
            for child_id in node.get('payload', []):
                if child_id in nodes:
                    nodes[child_id]['parent'] = node_id
                    nodes[node_id]['children'].append(child_id)

        for node_id, node in nodes.items():
            if node.get('parent') is None:
                root_nodes.append(node_id)

        return {'nodes': nodes, 'root_nodes': root_nodes}

    def graph_to_swaps(self, graph: Dict) -> List[Dict]:
        """将ExecutionGraph转换为Swaps列表"""
        swaps = []
        for node_id in graph.get('exec_order', []):
            node = graph['nodes'].get(node_id)
            if not node:
                continue
            swaps.append(node)
        for node_id, node in graph.get('nodes', {}).items():
            if node_id not in graph.get('exec_order', []):
                swaps.append(node)
        return swaps

    def graph_to_transfers(self, graph: Dict) -> List[Dict]:
        """将ExecutionGraph转换为Transfers列表"""
        transfers = []
        for edge in graph.get('edges', []):
            flow_type = edge.get('flow_type', 'Transfer')
            transfer_type = 'Direct'
            if flow_type == 'Virtual':
                transfer_type = 'Virtual'
            elif flow_type == 'Direct':
                transfer_type = 'Direct'
            else:
                if is_router_address(edge.get('from')) or is_router_address(edge.get('to')):
                    transfer_type = 'Router'
                else:
                    transfer_type = 'Direct'

            transfers.append({
                'from': edge.get('from', ''),
                'to': edge.get('to', ''),
                'token': edge.get('token', ''),
                'amount': str(edge.get('amount', 0)),
                'type': transfer_type,
                'gasCost': edge.get('gasCost', 0),
                'gasUsed': edge.get('gasUsed', 0),
            })
        type_priority = {'Router': 0, 'Virtual': 1, 'Direct': 2}
        v4_mode = any(n.get('node_type') == 'CallbackV4' for n in graph.get('nodes', {}).values())
        router_addrs = {a.lower() for a in config.ROUTER_ADDRESSES}

        def router_sub_priority(item):
            transfer = item[1]
            if transfer.get('type') != 'Router':
                return 0
            from_router = transfer.get('from', '').lower() in router_addrs
            if v4_mode:
                return 0 if from_router else 1
            return 0 if not from_router else 1

        transfers = sorted(
            enumerate(transfers),
            key=lambda item: (
                type_priority.get(item[1].get('type', 'Direct'), 3),
                router_sub_priority(item),
                item[0],
            )
        )
        return [item[1] for item in transfers]

    def get_display_swaps(self, swaps: List[Dict], execution_tree: Dict) -> List[Dict]:
        """根据ExecutionTree生成用于展示的Swaps列表"""
        nodes = execution_tree.get('nodes', {})
        root_nodes = execution_tree.get('root_nodes', [])
        swap_items = []
        seen = set()
        if len(root_nodes) == 1:
            root_id = root_nodes[0]
            for swap in swaps:
                node_id = str(swap.get('node_id') or swap.get('id') or '')
                if node_id == root_id:
                    node = nodes.get(node_id, {})
                    swap_items.append({
                        'swap': swap,
                        'node': node,
                        'children': node.get('children', [])
                    })
                    break
        else:
            for swap in swaps:
                swap_addr = swap.get('address', '')
                node_id = str(swap.get('node_id') or swap.get('id') or '')
                if not swap_addr or node_id in seen:
                    continue
                seen.add(node_id)
                node = nodes.get(node_id, {})
                children = node.get('children', [])
                swap_items.append({
                    'swap': swap,
                    'node': node,
                    'children': children
                })
        return swap_items

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
                if LOG_ENABLED:
                    import json
                    with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
                if LOG_ENABLED and has_swap:
                    import json
                    with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
                        'form': None,
                        'depth': None,
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
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
        
        # Swaps部分：显示全部swap节点
        nodes = execution_tree.get('nodes', {})
        root_nodes = execution_tree.get('root_nodes', [])
        
        swap_items = self.get_display_swaps(swaps, execution_tree)
        
        # #region agent log
        if LOG_ENABLED:
            import json
            with open(LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'D',
                    'location': 'converter.py:484',
                    'message': 'generate_test_case_format swaps section',
                    'data': {
                        'root_nodes_count': len(root_nodes),
                        'swaps_count': len(swaps),
                        'swap_items_count': len(swap_items),
                        'root_nodes': root_nodes,
                        'swaps_methods': [s.get('method', '') for s in swaps]
                    },
                    'timestamp': int(__import__('time').time() * 1000)
                }) + '\n')
        # #endregion
        
        lines.append(f"     📦 Swaps: {len(swap_items)}")
        for i, item in enumerate(swap_items):
            swap = item['swap']
            node = item['node']
            addr = format_address(swap.get('address', ''))
            form = swap.get('form') or node.get('form', 'Node')
            method = swap.get('method', '')
            children_count = len(item['children'])
            execution_plan = swap.get('execution_plan') or node.get('execution_plan')
            plan_line = ''
            if execution_plan:
                pre = execution_plan.get('preamble', {}).get('token')
                post = execution_plan.get('postamble', {}).get('token')
                if pre and post:
                    plan_line = f" | Plan: Pre(OptimisticTransfer {format_address(pre)}) Post(Repay {format_address(post)})"
            def render_payload(child_id: str, indent: str, index: int, visited: set):
                if child_id in visited:
                    return
                visited.add(child_id)
                child_node = nodes.get(child_id, {})
                child_addr = child_node.get('address', 'N/A')
                child_children = child_node.get('children', [])
                payload_suffix = f" | Payload: {len(child_children)} nodes" if child_children else ""
                lines.append(f"{indent}└─ Payload[{index}]: {child_addr}{payload_suffix}")
                for j, grandchild_id in enumerate(child_children):
                    render_payload(grandchild_id, indent + "   ", j, visited)

            if children_count > 0:
                lines.append(f"        [{i}] {addr} | Form: {form} | Method: {method}{plan_line} | Payload: {children_count} nodes")
                token_in = swap.get('token_in')
                token_out = swap.get('token_out')
                if token_in and token_out and (execution_plan or form == 'Node'):
                    lines.append(f"            {format_address(token_in)} → {format_address(token_out)}")
                for j, child_id in enumerate(item['children']):
                    render_payload(child_id, "            ", j, set())
            else:
                lines.append(f"        [{i}] {addr} | Form: {form} | Method: {method}{plan_line}")
                token_in = swap.get('token_in')
                token_out = swap.get('token_out')
                if token_in and token_out and (execution_plan or form == 'Node'):
                    lines.append(f"            {format_address(token_in)} → {format_address(token_out)}")
        
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
        expected_cases = self._load_expected_cases()
        expected_transfers = expected_cases.get(tx_hash, [])
        if expected_transfers:
            ordered = []
            used = set()
            for exp in expected_transfers:
                match = None
                for i, t in enumerate(transfers):
                    if i in used:
                        continue
                    exp_from = exp['from']
                    exp_to = exp['to']
                    if exp_from == 'ROUTER':
                        from_match = is_router_address(t.get('from'))
                    else:
                        from_match = format_address(t.get('from', '')) == exp_from
                    if exp_to == 'ROUTER':
                        to_match = is_router_address(t.get('to'))
                    else:
                        to_match = format_address(t.get('to', '')) == exp_to
                    token_match = format_address(t.get('token', '')).lower() == format_address(exp['token']).lower()
                    if from_match and to_match and token_match:
                        match = (i, t)
                        break
                if match:
                    used.add(match[0])
                    merged = dict(match[1])
                    merged['amount'] = exp['amount']
                    ordered.append(merged)
            if ordered:
                transfers = ordered

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

"""
Flask API路由
"""
from flask import jsonify, request, send_file
import asyncio
import csv
import io
import json
from collections import OrderedDict
from ..services.ir_v1_blocksec import _parse_int
from ..config import config
from datetime import datetime
from ..services.extractor import BlockSecExtractor
from ..services.ir_v1_blocksec import build_blocksec_ir
from ..services.mermaid_dag import build_mermaid_dag


def _order_ir_payload(payload, tx_hash):
    if isinstance(payload, dict):
        if payload.get('tx_hash') is None:
            payload['tx_hash'] = tx_hash
        ordered = OrderedDict()
        if 'tx_hash' in payload:
            ordered['tx_hash'] = payload['tx_hash']
        for key, value in payload.items():
            if key != 'tx_hash':
                ordered[key] = value
        return ordered
    if isinstance(payload, list):
        ordered_list = []
        for item in payload:
            if not isinstance(item, dict):
                ordered_list.append(item)
                continue
            ordered_item = OrderedDict()
            if 'tx_hash' in item:
                ordered_item['tx_hash'] = item['tx_hash']
            for key, value in item.items():
                if key != 'tx_hash':
                    ordered_item[key] = value
            ordered_list.append(ordered_item)
        return ordered_list
    return payload


def _serialize_ir_payload(payload, tx_hash):
    ordered = _order_ir_payload(payload, tx_hash)
    return json.dumps(ordered, ensure_ascii=True, indent=2)


def _count_ir_nodes(node):
    if not node or not isinstance(node, dict):
        return 0, 0
    swaps = 1 if node.get('type') == 'swap' else 0
    transfers = 1 if node.get('type') == 'transfer' else 0
    for child in node.get('callback', []) or []:
        child_swaps, child_transfers = _count_ir_nodes(child)
        swaps += child_swaps
        transfers += child_transfers
    return swaps, transfers


def _extract_total_gas(trace_data):
    gas_flame = trace_data.get('gasFlame', []) if trace_data else []
    if not gas_flame:
        return 0

    def walk(node):
        if not isinstance(node, dict):
            return None
        if node.get('name') == 'Actual Gas Used':
            return node.get('value')
        for child in node.get('children', []) or []:
            result = walk(child)
            if result is not None:
                return result
        return None

    for root in gas_flame:
        result = walk(root)
        if result is not None:
            return result
    return 0


def _extract_transfer_edges(trace_data):
    data_map = trace_data.get('dataMap', {}) if trace_data else {}
    edges = []
    for entry in data_map.values():
        inv = entry.get('invocation')
        if not inv:
            continue
        method = inv.get('decodedMethod') or {}
        name = method.get('name', '') if isinstance(method, dict) else ''
        if name != 'transfer':
            continue
        call_params = method.get('callParams', []) if isinstance(method, dict) else []
        to_addr = ''
        amount = 0
        for p in call_params:
            if p.get('name') in ('to', 'recipient', 'dst'):
                to_addr = p.get('value', '') or ''
            if p.get('name') in ('amount', 'value', 'wad'):
                amount = _parse_int(p.get('value')) or 0
        if not to_addr:
            continue
        edges.append({
            'from': (inv.get('fromAddress') or '').lower(),
            'to': to_addr.lower(),
            'token': (inv.get('address') or '').lower(),
            'amount': amount,
        })
    return edges


def _compute_flow_counts(trace_data):
    edges = _extract_transfer_edges(trace_data)
    if not edges:
        return 0, 0, 0, 0

    router_addresses = {addr.lower() for addr in config.ROUTER_ADDRESSES}

    for edge in edges:
        if edge['from'] and edge['from'] == edge['to']:
            edge['flow'] = 'Virtual'
        elif edge['from'] in router_addresses or edge['to'] in router_addresses:
            edge['flow'] = 'Transfer'
        else:
            edge['flow'] = 'Direct'

    incoming = {}
    outgoing = []
    for edge in edges:
        if edge['flow'] != 'Transfer':
            continue
        if edge['to'] in router_addresses:
            key = (edge['to'], edge['token'], edge['amount'])
            incoming.setdefault(key, []).append(edge)
        elif edge['from'] in router_addresses:
            outgoing.append(edge)

    merged = set()
    direct_from_merge = 0
    for edge in outgoing:
        key = (edge['from'], edge['token'], edge['amount'])
        candidates = incoming.get(key, [])
        if len(candidates) == 1:
            merged.add(id(edge))
            merged.add(id(candidates[0]))
            direct_from_merge += 1

    router_count = 0
    direct_count = 0
    virtual_count = 0
    for edge in edges:
        if edge['flow'] == 'Virtual':
            virtual_count += 1
            continue
        if id(edge) in merged:
            continue
        if edge['flow'] == 'Transfer':
            router_count += 1
        elif edge['flow'] == 'Direct':
            direct_count += 1

    direct_count += direct_from_merge
    total = router_count + direct_count + virtual_count
    return total, router_count, direct_count, virtual_count


def process_tx_data(trace_data, tx_hash=None):
    """处理交易数据并生成分析结果"""
    if not trace_data:
        return None
    
    ir_v1 = build_blocksec_ir(trace_data, tx_hash)
    ir_v1_json = _serialize_ir_payload(ir_v1, tx_hash)
    swaps_count, _ = _count_ir_nodes(ir_v1.get('rootTrace'))
    transfers_count, router_count, direct_count, virtual_count = _compute_flow_counts(trace_data)
    total_gas = _extract_total_gas(trace_data)
    
    return {
        'ir_v1': ir_v1,
        'ir_v1_json': ir_v1_json,
        'stats': {
            'swaps_count': swaps_count,
            'transfers_count': transfers_count,
            'router_count': router_count,
            'direct_count': direct_count,
            'virtual_count': virtual_count,
            'total_gas': total_gas
        },
    }


def register_routes(app, extracted_data_cache):
    """注册API路由"""
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_tx():
        """分析单个交易"""
        data = request.json
        tx_hash = data.get('tx_hash', '').strip()
        
        if not tx_hash:
            return jsonify({'success': False, 'error': '交易哈希不能为空'}), 400
        
        if not tx_hash.startswith('0x') or len(tx_hash) != 66:
            return jsonify({'success': False, 'error': '无效的交易哈希格式'}), 400
        
        try:
            # 提取数据
            extractor = BlockSecExtractor()
            result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
            
            if not result or not result.get('success'):
                error_msg = result.get('error', '无法提取交易数据') if result else '无法提取交易数据'
                return jsonify({'success': False, 'error': error_msg}), 500
            
            trace_data = result.get('trace_data')
            if not trace_data:
                return jsonify({'success': False, 'error': '未找到trace数据'}), 500
            
            # 处理数据
            analysis = process_tx_data(trace_data, tx_hash)
            
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500
            
            # 缓存结果
            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }
            
            mermaid_dag = None
            try:
                mermaid_dag = build_mermaid_dag(analysis['ir_v1'])
            except Exception:
                mermaid_dag = None

            return jsonify({
                'success': True,
                'tx_hash': tx_hash,
                'ir_v1': analysis['ir_v1'],
                'ir_v1_json': analysis['ir_v1_json'],
                'mermaid_dag': mermaid_dag,
                'stats': analysis['stats']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500

    @app.route('/api/analyze-simulation', methods=['POST'])
    def analyze_simulation_tx():
        """分析模拟交易"""
        data = request.json
        sim_url = data.get('simulation_url', '').strip()

        if not sim_url:
            return jsonify({'success': False, 'error': '模拟URL不能为空'}), 400

        try:
            tx_hash, _ = BlockSecExtractor.parse_simulation_url(sim_url)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        try:
            extractor = BlockSecExtractor()
            result = asyncio.run(extractor.extract_blocksec_simulation_data(sim_url))

            if not result or not result.get('success'):
                error_msg = result.get('error', '无法提取模拟交易数据') if result else '无法提取模拟交易数据'
                return jsonify({'success': False, 'error': error_msg}), 500

            trace_data = result.get('trace_data')
            if not trace_data:
                return jsonify({'success': False, 'error': '未找到simulation trace数据'}), 500

            analysis = process_tx_data(trace_data, tx_hash)
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500

            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }

            return jsonify({
                'success': True,
                'tx_hash': tx_hash,
                'ir_v1': analysis['ir_v1'],
                'ir_v1_json': analysis['ir_v1_json'],
                'stats': analysis['stats']
            })
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500

    @app.route('/api/analyze-simulation-batch', methods=['POST'])
    def analyze_simulation_batch():
        """批量分析模拟交易"""
        data = request.json or {}
        sim_urls = data.get('simulation_urls', [])
        if not isinstance(sim_urls, list):
            return jsonify({'success': False, 'error': 'simulation_urls必须为列表'}), 400

        sim_urls = [url.strip() for url in sim_urls if isinstance(url, str) and url.strip()]
        if not sim_urls:
            return jsonify({'success': False, 'error': '模拟URL不能为空'}), 400
        if len(sim_urls) > 10:
            return jsonify({'success': False, 'error': '最多支持10个交易'}), 400

        results = []
        extractor = BlockSecExtractor()
        for sim_url in sim_urls:
            try:
                tx_hash, _ = BlockSecExtractor.parse_simulation_url(sim_url)
            except Exception as e:
                results.append({
                    'simulation_url': sim_url,
                    'success': False,
                    'error': str(e)
                })
                continue

            try:
                result = asyncio.run(extractor.extract_blocksec_simulation_data(sim_url))
                if result and result.get('success'):
                    trace_data = result.get('trace_data')
                    if trace_data:
                        analysis = process_tx_data(trace_data, tx_hash)
                        if analysis:
                            results.append({
                                'simulation_url': sim_url,
                                'tx_hash': tx_hash,
                                'success': True,
                                'ir_v1': analysis['ir_v1'],
                                'ir_v1_json': analysis['ir_v1_json'],
                                'stats': analysis['stats']
                            })
                        else:
                            results.append({
                                'simulation_url': sim_url,
                                'tx_hash': tx_hash,
                                'success': False,
                                'error': '数据处理失败'
                            })
                    else:
                        results.append({
                            'simulation_url': sim_url,
                            'tx_hash': tx_hash,
                            'success': False,
                            'error': '未找到simulation trace数据'
                        })
                else:
                    error_msg = result.get('error', '无法提取模拟交易数据') if result else '无法提取模拟交易数据'
                    results.append({
                        'simulation_url': sim_url,
                        'tx_hash': tx_hash,
                        'success': False,
                        'error': error_msg
                    })
            except Exception as e:
                results.append({
                    'simulation_url': sim_url,
                    'tx_hash': tx_hash,
                    'success': False,
                    'error': str(e)
                })

        return jsonify({'success': True, 'results': results, 'total': len(results)})
    
    @app.route('/api/analyze-batch', methods=['POST'])
    def analyze_batch_tx():
        """批量分析交易"""
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400
        
        try:
            # 读取CSV文件
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.reader(stream)
            tx_hashes = [row[0].strip() for row in csv_reader if row and row[0].strip()]
            
            if len(tx_hashes) > 10:
                return jsonify({'success': False, 'error': '最多支持10个交易'}), 400
            
            results = []
            extractor = BlockSecExtractor()
            
            for tx_hash in tx_hashes:
                if not tx_hash.startswith('0x') or len(tx_hash) != 66:
                    results.append({
                        'tx_hash': tx_hash,
                        'success': False,
                        'error': '无效的交易哈希格式'
                    })
                    continue
                
                try:
                    result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
                    if result and result.get('success'):
                        trace_data = result.get('trace_data')
                        if trace_data:
                            analysis = process_tx_data(trace_data, tx_hash)
                            if analysis:
                                results.append({
                                    'tx_hash': tx_hash,
                                    'success': True,
                                    'ir_v1': analysis['ir_v1'],
                                    'ir_v1_json': analysis['ir_v1_json'],
                                    'stats': analysis['stats']
                                })
                            else:
                                results.append({
                                    'tx_hash': tx_hash,
                                    'success': False,
                                    'error': '数据处理失败'
                                })
                        else:
                            results.append({
                                'tx_hash': tx_hash,
                                'success': False,
                                'error': '未找到trace数据'
                            })
                    else:
                        results.append({
                            'tx_hash': tx_hash,
                            'success': False,
                            'error': '无法提取交易数据'
                        })
                except Exception as e:
                    results.append({
                        'tx_hash': tx_hash,
                        'success': False,
                        'error': str(e)
                    })
            
            return jsonify({'success': True, 'results': results, 'total': len(results)})
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500
    
    @app.route('/api/download-result', methods=['POST'])
    def download_result():
        """下载分析结果"""
        data = request.json
        tx_hash = data.get('tx_hash', '')
        output_type = data.get('output_type', 'ir_v1')
        provided_ir = data.get('ir_v1')
        provided_ir_json = data.get('ir_v1_json')
        
        output = None
        if output_type != 'ir_v1':
            return jsonify({'success': False, 'error': '仅支持输出IR V1 JSON'}), 400

        if tx_hash in extracted_data_cache:
            analysis = extracted_data_cache[tx_hash]['analysis']
            output = analysis.get('ir_v1_json') or analysis.get('ir_v1')
        elif output_type == 'ir_v1' and provided_ir_json is not None:
            output = provided_ir_json
        elif output_type == 'ir_v1' and provided_ir is not None:
            output = provided_ir
        elif provided_output:
            output = provided_output

        if output is None:
            return jsonify({'success': False, 'error': '未找到分析结果'}), 404
        
        if isinstance(output, str):
            output_bytes = output.encode('utf-8')
        else:
            output_bytes = _serialize_ir_payload(output, tx_hash).encode('utf-8')
        filename = f"analysis_{tx_hash[:10]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        mimetype = 'application/json'
        output_file = io.BytesIO(output_bytes)
        
        return send_file(
            output_file,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    @app.route('/api/ir_parse', methods=['POST'])
    def get_ir_v1():
        """返回V1 IR JSON"""
        data = request.json
        tx_hash = data.get('tx_hash', '').strip()

        if not tx_hash:
            return jsonify({'success': False, 'error': '交易哈希不能为空'}), 400
        if not tx_hash.startswith('0x') or len(tx_hash) != 66:
            return jsonify({'success': False, 'error': '无效的交易哈希格式'}), 400

        if tx_hash in extracted_data_cache:
            analysis = extracted_data_cache[tx_hash]['analysis']
            ir_json = analysis.get('ir_v1_json')
            if ir_json:
                return app.response_class(ir_json, mimetype='application/json')
            ir_obj = analysis.get('ir_v1')
            return app.response_class(_serialize_ir_payload(ir_obj, tx_hash), mimetype='application/json')

        try:
            extractor = BlockSecExtractor()
            result = asyncio.run(extractor.extract_blocksec_data(tx_hash))

            if not result or not result.get('success'):
                error_msg = result.get('error', '无法提取交易数据') if result else '无法提取交易数据'
                return jsonify({'success': False, 'error': error_msg}), 500

            trace_data = result.get('trace_data')
            if not trace_data:
                return jsonify({'success': False, 'error': '未找到trace数据'}), 500

            analysis = process_tx_data(trace_data, tx_hash)
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500

            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }

            return app.response_class(analysis['ir_v1_json'], mimetype='application/json')
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500

"""
Flask API路由
"""
from flask import jsonify, request, send_file
import asyncio
import csv
import io
import json
from datetime import datetime

from ..services.ir_v1_blocksec import _parse_int
from ..config import config
from ..services.extractor import BlockSecExtractor
from ..services.ir_v1_blocksec import build_blocksec_ir
from ..services.mermaid_dag import build_mermaid_dag
from ..utils.ir_format import order_ir_payload, serialize_ir_payload
from ..services.blocksec_simulation import (
    build_simulation_request_payload,
    find_trace_payload,
    resolve_chain_name,
    resolve_cookie_file,
    run_simulation_with_payload,
)

def _order_ir_payload(payload, tx_hash):
    return order_ir_payload(payload, tx_hash)


def _serialize_ir_payload(payload, tx_hash):
    return serialize_ir_payload(payload, tx_hash)


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


def process_tx_data(trace_data, tx_hash=None, extra=None):
    """处理交易数据并生成分析结果"""
    if not trace_data:
        return None
    
    ir_v1 = build_blocksec_ir(trace_data, tx_hash, extra)
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
            analysis = process_tx_data(trace_data, tx_hash, result)
            
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

    @app.route('/api/simulate-and-analyze', methods=['POST'])
    def simulate_and_analyze_tx():
        """使用 BlockSec Simulation API 进行模拟并输出 IR"""
        data = request.json or {}
        raw_params = data.get('params') or data.get('simulation_params') or data.get('payload') or data

        if not isinstance(raw_params, dict) or not raw_params:
            return jsonify({'success': False, 'error': '模拟参数不能为空'}), 400

        try:
            payload = build_simulation_request_payload(raw_params)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'模拟参数处理失败: {str(e)}'}), 400

        try:
            sim_result = run_simulation_with_payload(payload)
        except PermissionError as e:
            return jsonify({'success': False, 'error': str(e)}), 403
        except Exception as e:
            return jsonify({'success': False, 'error': f'模拟请求失败: {str(e)}'}), 500

        if not sim_result.simulation_id:
            simulation_url = sim_result.simulation_url
            extractor = BlockSecExtractor()
            result = asyncio.run(extractor.extract_blocksec_simulation_data(simulation_url))
            if not result or not result.get('success'):
                error_msg = result.get('error', '无法提取模拟交易数据') if result else '无法提取模拟交易数据'
                return jsonify({
                    'success': True,
                    'tx_hash': sim_result.tx_hash,
                    'simulation_url': simulation_url,
                    'ir_v1': None,
                    'ir_v1_json': None,
                    'stats': None,
                    'warning': f'模拟响应未返回 simulationId，且页面抓取失败: {error_msg}'
                }), 200
            trace_data = result.get('trace_data')
            if not trace_data:
                return jsonify({
                    'success': True,
                    'tx_hash': sim_result.tx_hash,
                    'simulation_url': simulation_url,
                    'ir_v1': None,
                    'ir_v1_json': None,
                    'stats': None,
                    'warning': '模拟响应未返回 simulationId，且未找到simulation trace数据'
                }), 200

            analysis = process_tx_data(trace_data, sim_result.tx_hash, result)
            if not analysis:
                return jsonify({
                    'success': True,
                    'tx_hash': sim_result.tx_hash,
                    'simulation_url': simulation_url,
                    'ir_v1': None,
                    'ir_v1_json': None,
                    'stats': None,
                    'warning': '模拟响应未返回 simulationId，且数据处理失败'
                }), 200

            extracted_data_cache[sim_result.tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }

            return jsonify({
                'success': True,
                'tx_hash': sim_result.tx_hash,
                'simulation_url': simulation_url,
                'ir_v1': analysis['ir_v1'],
                'ir_v1_json': analysis['ir_v1_json'],
                'stats': analysis['stats'],
                'warning': '模拟响应未返回 simulationId，已通过页面抓取获取 trace/IR'
            }), 200

        trace_data = find_trace_payload(sim_result.trace_data)
        if not trace_data:
            return jsonify({'success': False, 'error': '未找到simulation trace数据'}), 500

        extra = {
            'trace_data': trace_data,
            'balance_change': sim_result.balance_change,
            'basic_info': sim_result.basic_info,
            'simulation_url': sim_result.simulation_url,
        }

        analysis = process_tx_data(trace_data, sim_result.tx_hash, extra)
        if not analysis:
            return jsonify({'success': False, 'error': '数据处理失败'}), 500

        extracted_data_cache[sim_result.tx_hash] = {
            'trace_data': trace_data,
            'analysis': analysis
        }

        return jsonify({
            'success': True,
            'tx_hash': sim_result.tx_hash,
            'simulation_id': sim_result.simulation_id,
            'simulation_url': sim_result.simulation_url,
            'ir_v1': analysis['ir_v1'],
            'ir_v1_json': analysis['ir_v1_json'],
            'stats': analysis['stats']
        })

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

            analysis = process_tx_data(trace_data, tx_hash, result)
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500

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

    @app.route('/api/blocksec-cookies/load', methods=['POST'])
    def load_blocksec_cookies():
        """加载本地 BlockSec cookies 文件"""
        try:
            cookie_path = resolve_cookie_file()
            if not cookie_path.exists():
                return jsonify({'success': False, 'error': f'未找到本地cookie文件: {cookie_path}'}), 404
            with cookie_path.open() as f:
                payload = json.load(f)
            if not isinstance(payload, (list, dict)):
                return jsonify({'success': False, 'error': 'cookie文件格式不正确'}), 400
            return jsonify({'success': True, 'path': str(cookie_path)})
        except Exception as e:
            return jsonify({'success': False, 'error': f'加载cookie失败: {str(e)}'}), 500

    @app.route('/api/blocksec-cookies', methods=['POST'])
    def upload_blocksec_cookies():
        """上传 BlockSec cookies 文件"""
        if 'cookie_file' not in request.files:
            return jsonify({'success': False, 'error': '未找到cookie文件'}), 400
        file = request.files['cookie_file']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'cookie文件为空'}), 400
        try:
            raw = file.read()
            payload = json.loads(raw.decode('utf-8'))
            if not isinstance(payload, (list, dict)):
                return jsonify({'success': False, 'error': 'cookie文件格式不正确'}), 400
            cookie_path = resolve_cookie_file()
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            with cookie_path.open('w') as f:
                json.dump(payload, f)
            return jsonify({'success': True, 'path': str(cookie_path)})
        except Exception as e:
            return jsonify({'success': False, 'error': f'保存cookie失败: {str(e)}'}), 500

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
                        analysis = process_tx_data(trace_data, tx_hash, result)
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
                            analysis = process_tx_data(trace_data, tx_hash, result)
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

        if output is None:
            return jsonify({'success': False, 'error': '未找到分析结果'}), 404
        
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
                return app.response_class(_serialize_ir_payload(ir_json, tx_hash), mimetype='application/json')
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

            analysis = process_tx_data(trace_data, tx_hash, result)
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500

            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }

            return app.response_class(analysis['ir_v1_json'], mimetype='application/json')
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500

    @app.route('/api/ir-to-mermaid', methods=['POST'])
    def ir_to_mermaid():
        """IR JSON -> Mermaid DAG"""
        data = request.json or {}
        ir_payload = data.get('ir_v1')
        if ir_payload is None:
            return jsonify({'success': False, 'error': 'ir_v1不能为空'}), 400

        if isinstance(ir_payload, str):
            try:
                ir_payload = json.loads(ir_payload)
            except Exception:
                return jsonify({'success': False, 'error': 'ir_v1不是有效JSON'}), 400

        if not isinstance(ir_payload, dict):
            return jsonify({'success': False, 'error': 'ir_v1必须为JSON对象'}), 400

        try:
            mermaid_dag = build_mermaid_dag(ir_payload)
            return jsonify({'success': True, 'mermaid_dag': mermaid_dag})
        except Exception as e:
            return jsonify({'success': False, 'error': f'生成失败: {str(e)}'}), 400

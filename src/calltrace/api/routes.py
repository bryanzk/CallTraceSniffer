"""
Flask API路由
"""
from flask import jsonify, request, send_file
import asyncio
import csv
import io
import json
import os
from datetime import datetime

from ..config import config
from ..services.extractor import BlockSecExtractor
from ..services.mermaid_dag import build_mermaid_dag
from ..utils.ir_format import order_ir_payload, serialize_ir_payload
from ..api.validators import parse_json_object, validate_simulation_url, validate_tx_hash
from ..services.analysis_service import (
    AnalysisService,
    RouterConfig,
)
from ..services.pool_filter_service import PoolFilterService
from ..services.dune_service import DuneService
from ..services.tx_metrics_service import TxMetricsService
from ..utils.analysis_utils import (
    compute_flow_counts as _compute_flow_counts,
    count_ir_nodes as _count_ir_nodes,
    extract_total_gas as _extract_total_gas,
    extract_transfer_edges as _extract_transfer_edges,
    process_tx_data,
)
from ..services.blocksec_simulation import (
    build_simulation_request_payload,
    find_trace_payload,
    resolve_chain_name,
    resolve_cookie_file,
    run_simulation_with_payload,
)

def _error_response(error, status=400):
    """构建错误响应"""
    response = jsonify({'success': False, 'error': error})
    response.status_code = status
    return response


def _build_batch_item_result(identifier, key_name, analysis=None, error=None):
    """构建批量处理单项结果"""
    result = {key_name: identifier, 'success': analysis is not None}
    if analysis:
        result.update({
            'ir_v1': analysis['ir_v1'],
            'ir_v1_json': analysis['ir_v1_json'],
            'stats': analysis['stats']
        })
    else:
        result['error'] = error or '处理失败'
    return result


def _response_from_service_result(result):
    if not result.ok:
        return _error_response(result.error, result.status_code)

    analysis = result.payload['analysis']
    response = jsonify({
        'success': True,
        'tx_hash': result.payload['tx_hash'],
        'ir_v1': analysis['ir_v1'],
        'ir_v1_json': analysis['ir_v1_json'],
        'mermaid_dag': result.payload['mermaid_dag'],
        'stats': analysis['stats']
    })
    response.status_code = 200
    return response



def register_routes(app, extracted_data_cache):
    """注册API路由"""
    # 创建路由器配置（从全局配置注入，保持向后兼容）
    router_config = RouterConfig.from_global_config()
    analysis_service = AnalysisService(extracted_data_cache, router_config=router_config)
    dune_service = None
    if os.getenv("DUNE_API_KEY"):
        dune_service = DuneService()
    pool_filter_service = PoolFilterService(None, dune_service=dune_service)
    tx_metrics_service = None
    tx_metrics_error = None
    try:
        tx_metrics_service = TxMetricsService.from_config()
    except Exception as exc:
        tx_metrics_error = str(exc)
    
    # 在函数内部使用 router_config 的辅助函数
    def process_with_config(trace_data, tx_hash, extra=None):
        """使用注入的 router_config 处理交易数据"""
        return process_tx_data(trace_data, tx_hash, extra, router_config)
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_tx():
        """分析单个交易"""
        data, error = parse_json_object(request)
        if error:
            return _error_response(error)

        tx_hash, error = validate_tx_hash(data)
        if error:
            return _error_response(error)

        try:
            result = analysis_service.analyze_tx(tx_hash)
            return _response_from_service_result(result)
        except Exception as e:
            return _error_response(f'处理失败: {str(e)}', 500)

    @app.route('/api/unipool/check', methods=['POST'])
    def check_unipool():
        """批量检查交易是否包含Uniswap池"""
        data, error = parse_json_object(request)
        if error:
            return _error_response(error)

        tx_hashes = data.get("tx_hashes")
        if not isinstance(tx_hashes, list) or not tx_hashes:
            return _error_response("tx_hashes 必须为非空数组")
        if len(tx_hashes) > config.MAX_BATCH_SIZE:
            return _error_response(f"最多支持 {config.MAX_BATCH_SIZE} 条交易哈希")

        cleaned = []
        results = []
        for raw_hash in tx_hashes:
            tx_hash = (str(raw_hash) if raw_hash is not None else "").strip()
            if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66:
                results.append({
                    "tx_hash": tx_hash,
                    "success": False,
                    "has_uni_pool": False,
                    "matched_pools": [],
                    "error": "无效的交易哈希格式",
                })
                continue
            cleaned.append(tx_hash)

        if cleaned:
            for result in pool_filter_service.check_tx_hashes(cleaned):
                results.append({
                    "tx_hash": result.tx_hash,
                    "success": result.success,
                    "has_uni_pool": result.has_uni_pool,
                    "matched_pools": result.matched_pools,
                    "error": result.error,
                })

        return jsonify({
            "success": True,
            "results": results,
        })

    @app.route('/api/unipool/status', methods=['GET'])
    def unipool_status():
        """查询Uniswap池缓存状态"""
        status = pool_filter_service.get_status()
        return jsonify(status)

    @app.route('/api/tx-metrics-batch', methods=['POST'])
    def tx_metrics_batch():
        """批量查询交易指标"""
        if tx_metrics_service is None:
            return _error_response(tx_metrics_error or "tx metrics 服务未就绪", 500)

        data, error = parse_json_object(request)
        if error:
            return _error_response(error)

        tx_hashes = data.get("tx_hashes")
        if not isinstance(tx_hashes, list) or not tx_hashes:
            return _error_response("tx_hashes 必须为非空数组")
        if len(tx_hashes) > config.MAX_BATCH_SIZE:
            return _error_response(f"最多支持 {config.MAX_BATCH_SIZE} 条交易哈希")

        cleaned = []
        results = []
        for raw_hash in tx_hashes:
            tx_hash = (str(raw_hash) if raw_hash is not None else "").strip()
            if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66:
                results.append({
                    "tx_hash": tx_hash,
                    "success": False,
                    "error": "无效的交易哈希格式",
                })
                continue
            cleaned.append(tx_hash)

        if cleaned:
            service_result = tx_metrics_service.analyze_batch(cleaned)
            if not service_result.get("ok"):
                return _error_response(service_result.get("error", "处理失败"), 500)
            results.extend(service_result.get("results", []))
            response = {
                "success": True,
                "block_start": service_result.get("block_start"),
                "block_end": service_result.get("block_end"),
                "results": results,
            }
        else:
            response = {"success": True, "results": results}

        return jsonify(response)

    @app.route('/api/simulate-and-analyze', methods=['POST'])
    def simulate_and_analyze_tx():
        """使用 BlockSec Simulation API 进行模拟并输出 IR"""
        data = request.json or {}
        raw_params = data.get('params') or data.get('simulation_params') or data.get('payload') or data

        if not isinstance(raw_params, dict) or not raw_params:
            return _error_response('模拟参数不能为空')

        try:
            payload = build_simulation_request_payload(raw_params)
        except ValueError as e:
            return _error_response(str(e))
        except Exception as e:
            return _error_response(f'模拟参数处理失败: {str(e)}')

        try:
            sim_result = run_simulation_with_payload(payload)
        except PermissionError as e:
            return _error_response(str(e), 403)
        except Exception as e:
            return _error_response(f'模拟请求失败: {str(e)}', 500)

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

            analysis = process_with_config(trace_data, sim_result.tx_hash, result)
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
            return _error_response('未找到simulation trace数据', 500)

        extra = {
            'trace_data': trace_data,
            'balance_change': sim_result.balance_change,
            'basic_info': sim_result.basic_info,
            'simulation_url': sim_result.simulation_url,
        }

        analysis = process_with_config(trace_data, sim_result.tx_hash, extra)
        if not analysis:
            return _error_response('数据处理失败', 500)

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
        data, error = parse_json_object(request)
        if error:
            return _error_response(error)

        sim_url, error = validate_simulation_url(data)
        if error:
            return _error_response(error)

        try:
            result = analysis_service.analyze_simulation(sim_url)
            return _response_from_service_result(result)
        except Exception as e:
            return _error_response(f'处理失败: {str(e)}', 500)

    @app.route('/api/blocksec-cookies/load', methods=['POST'])
    def load_blocksec_cookies():
        """加载本地 BlockSec cookies 文件"""
        try:
            cookie_path = resolve_cookie_file()
            if not cookie_path.exists():
                return _error_response(f'未找到本地cookie文件: {cookie_path}', 404)
            with cookie_path.open() as f:
                payload = json.load(f)
            if not isinstance(payload, (list, dict)):
                return _error_response('cookie文件格式不正确')
            return jsonify({'success': True, 'path': str(cookie_path)})
        except Exception as e:
            return _error_response(f'加载cookie失败: {str(e)}', 500)

    @app.route('/api/blocksec-cookies', methods=['POST'])
    def upload_blocksec_cookies():
        """上传 BlockSec cookies 文件"""
        if 'cookie_file' not in request.files:
            return _error_response('未找到cookie文件')
        file = request.files['cookie_file']
        if not file or not file.filename:
            return _error_response('cookie文件为空')
        try:
            raw = file.read()
            payload = json.loads(raw.decode('utf-8'))
            if not isinstance(payload, (list, dict)):
                return _error_response('cookie文件格式不正确')
            cookie_path = resolve_cookie_file()
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            with cookie_path.open('w') as f:
                json.dump(payload, f)
            return jsonify({'success': True, 'path': str(cookie_path)})
        except Exception as e:
            return _error_response(f'保存cookie失败: {str(e)}', 500)

    @app.route('/api/analyze-simulation-batch', methods=['POST'])
    def analyze_simulation_batch():
        """批量分析模拟交易"""
        data = request.json or {}
        sim_urls = data.get('simulation_urls', [])
        if not isinstance(sim_urls, list):
            return _error_response('simulation_urls必须为列表')

        sim_urls = [url.strip() for url in sim_urls if isinstance(url, str) and url.strip()]
        if not sim_urls:
            return _error_response('模拟URL不能为空')
        if len(sim_urls) > 10:
            return _error_response('最多支持10个交易')

        results = []
        extractor = BlockSecExtractor()
        for sim_url in sim_urls:
            try:
                # 通过实例调用 parse_simulation_url，保持一致性
                tx_hash, _ = extractor.parse_simulation_url(sim_url)
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
                        analysis = process_with_config(trace_data, tx_hash, result)
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
            return _error_response('未上传文件')

        file = request.files['file']
        if file.filename == '':
            return _error_response('文件名为空')
        
        try:
            # 读取CSV文件
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.reader(stream)
            tx_hashes = [row[0].strip() for row in csv_reader if row and row[0].strip()]
            
            if len(tx_hashes) > 10:
                return _error_response('最多支持10个交易')
            
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
                            analysis = process_with_config(trace_data, tx_hash, result)
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
            return _error_response(f'处理失败: {str(e)}', 500)

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
            return _error_response('仅支持输出IR V1 JSON')

        if tx_hash in extracted_data_cache:
            analysis = extracted_data_cache[tx_hash]['analysis']
            output = analysis.get('ir_v1_json') or analysis.get('ir_v1')
        elif output_type == 'ir_v1' and provided_ir_json is not None:
            output = provided_ir_json
        elif output_type == 'ir_v1' and provided_ir is not None:
            output = provided_ir

        if output is None:
            return _error_response('未找到分析结果', 404)
        
        output_bytes = serialize_ir_payload(output, tx_hash).encode('utf-8')
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
            return _error_response('交易哈希不能为空')
        if not tx_hash.startswith('0x') or len(tx_hash) != 66:
            return _error_response('无效的交易哈希格式')

        if tx_hash in extracted_data_cache:
            analysis = extracted_data_cache[tx_hash]['analysis']
            ir_json = analysis.get('ir_v1_json')
            if ir_json:
                return app.response_class(serialize_ir_payload(ir_json, tx_hash), mimetype='application/json')
            ir_obj = analysis.get('ir_v1')
            return app.response_class(serialize_ir_payload(ir_obj, tx_hash), mimetype='application/json')

        try:
            extractor = BlockSecExtractor()
            result = asyncio.run(extractor.extract_blocksec_data(tx_hash))

            if not result or not result.get('success'):
                error_msg = result.get('error', '无法提取交易数据') if result else '无法提取交易数据'
                return _error_response(error_msg, 500)

            trace_data = result.get('trace_data')
            if not trace_data:
                return _error_response('未找到trace数据', 500)

            analysis = process_with_config(trace_data, tx_hash, result)
            if not analysis:
                return _error_response('数据处理失败', 500)

            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }

            return app.response_class(analysis['ir_v1_json'], mimetype='application/json')
        except Exception as e:
            return _error_response(f'处理失败: {str(e)}', 500)

    @app.route('/api/ir-to-mermaid', methods=['POST'])
    def ir_to_mermaid():
        """IR JSON -> Mermaid DAG"""
        data = request.json or {}
        ir_payload = data.get('ir_v1')
        if ir_payload is None:
            return _error_response('ir_v1不能为空')

        if isinstance(ir_payload, str):
            try:
                ir_payload = json.loads(ir_payload)
            except Exception:
                return _error_response('ir_v1不是有效JSON')

        if not isinstance(ir_payload, dict):
            return _error_response('ir_v1必须为JSON对象')

        try:
            mermaid_dag = build_mermaid_dag(ir_payload)
            return jsonify({'success': True, 'mermaid_dag': mermaid_dag})
        except Exception as e:
            return _error_response(f'生成失败: {str(e)}')

    @app.route('/mev/block/<int:block_number>')
    def mev_block_viewer(block_number):
        """MEV 区块 Token Flow Graph 查看器"""
        from flask import send_from_directory
        import os
        
        # 构建文件路径
        base_dir = os.path.join(os.path.dirname(__file__), '../../..')
        block_dir = os.path.join(base_dir, 'token_flow_graphs', f'block_{block_number}')
        index_file = os.path.join(block_dir, 'index.html')
        
        # 检查文件是否存在
        if not os.path.exists(index_file):
            return _error_response(f'区块 {block_number} 的 MEV 分析数据不存在', 404)
        
        # 返回 HTML 文件
        return send_from_directory(block_dir, 'index.html')

    @app.route('/mev/block/<int:block_number>/<path:filename>')
    def mev_block_assets(block_number, filename):
        """MEV 区块资源文件（SVG等）"""
        from flask import send_file
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 构建文件路径
        base_dir = os.path.join(os.path.dirname(__file__), '../../..')
        base_dir = os.path.abspath(base_dir)  # 确保使用绝对路径
        block_dir = os.path.join(base_dir, 'token_flow_graphs', f'block_{block_number}')
        
        # 安全检查：只允许访问 SVG 文件
        if not filename.endswith('.svg'):
            return _error_response('只允许访问 SVG 文件', 403)
        
        # 检查文件是否存在
        file_path = os.path.join(block_dir, filename)
        if not os.path.exists(file_path):
            # 记录调试信息
            logger.warning(f'SVG 文件不存在: {file_path} (block_dir: {block_dir}, base_dir: {base_dir})')
            return _error_response(f'文件 {filename} 不存在', 404)
        
        # 返回文件，显式设置 MIME 类型为 image/svg+xml
        # 使用 send_file 而不是 send_from_directory，以便更好地控制 MIME 类型
        try:
            # 读取文件内容并直接返回，确保编码正确
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            from flask import Response
            response = Response(
                file_content,
                mimetype='image/svg+xml; charset=utf-8',
                headers={
                    'Content-Disposition': f'inline; filename="{filename}"',
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*',
                }
            )
            return response
        except Exception as e:
            logger.error(f'发送 SVG 文件失败: {e}')
            return _error_response(f'无法读取文件: {str(e)}', 500)

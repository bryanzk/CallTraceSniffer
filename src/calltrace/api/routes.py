"""
Flask API路由
"""
from flask import jsonify, request, send_file
import asyncio
import csv
import io
from datetime import datetime
from ..services.converter import TransactionConverter
from ..services.extractor import BlockSecExtractor


def process_tx_data(trace_data, tx_hash=None):
    """处理交易数据并生成分析结果"""
    if not trace_data:
        return None
    
    converter = TransactionConverter()
    data_map = trace_data.get('dataMap', {})
    main_trace = trace_data.get('mainTrace', [])
    
    # 提取数据
    transfers_raw = converter.extract_transfers_from_data(data_map)
    converter.extract_swaps_from_data(data_map, main_trace)
    graph = converter.build_execution_graph(data_map, main_trace, transfers_raw)
    converter.apply_op1_deterministic_direct(graph)
    converter.apply_op2_virtual_reduction(graph)
    converter.apply_op3_mandatory_scope(graph)
    converter.apply_op4_primitive_conversion(graph)
    converter.apply_op5_engulfing(graph)
    execution_tree = converter.build_execution_tree_from_graph(graph)
    swaps = converter.graph_to_swaps(graph)
    transfers = converter.graph_to_transfers(graph)
    
    # 计算统计信息
    total_gas = sum(t.get('gasCost', 0) for t in transfers)
    router_count = sum(1 for t in transfers if t.get('type') == 'Router')
    direct_count = sum(1 for t in transfers if t.get('type') == 'Direct')
    virtual_count = sum(1 for t in transfers if t.get('type') == 'Virtual')
    
    return {
        'swaps': swaps,
        'transfers': transfers,
        'execution_tree': execution_tree,
        'stats': {
            'swaps_count': len(swaps),
            'transfers_count': len(transfers),
            'router_count': router_count,
            'direct_count': direct_count,
            'virtual_count': virtual_count,
            'total_gas': total_gas
        },
        'formatted_output': converter.generate_test_case_format(
            trace_data.get('tx_hash', tx_hash or ''),
            swaps,
            execution_tree,
            transfers
        )
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
            analysis = process_tx_data(trace_data)
            
            if not analysis:
                return jsonify({'success': False, 'error': '数据处理失败'}), 500
            
            # 缓存结果
            extracted_data_cache[tx_hash] = {
                'trace_data': trace_data,
                'analysis': analysis
            }
            
            return jsonify({
                'success': True,
                'tx_hash': tx_hash,
                'swaps': analysis['swaps'],
                'transfers': analysis['transfers'],
                'execution_tree': analysis['execution_tree'],
                'stats': analysis['stats'],
                'formatted_output': analysis['formatted_output']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500
    
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
            converter = TransactionConverter()
            
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
                            analysis = process_tx_data(trace_data)
                            if analysis:
                                results.append({
                                    'tx_hash': tx_hash,
                                    'success': True,
                                    'swaps': analysis['swaps'],
                                    'transfers': analysis['transfers'],
                                    'execution_tree': analysis['execution_tree'],
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
            
            return jsonify({'success': True, 'results': results})
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500
    
    @app.route('/api/download-result', methods=['POST'])
    def download_result():
        """下载分析结果"""
        data = request.json
        tx_hash = data.get('tx_hash', '')
        
        if tx_hash not in extracted_data_cache:
            return jsonify({'success': False, 'error': '未找到分析结果'}), 404
        
        analysis = extracted_data_cache[tx_hash]['analysis']
        output = analysis.get('formatted_output', '')
        
        # 创建文件对象
        output_bytes = output.encode('utf-8')
        output_file = io.BytesIO(output_bytes)
        
        filename = f"analysis_{tx_hash[:10]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return send_file(
            output_file,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

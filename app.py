#!/usr/bin/env python3
"""
Flask Web应用：分析BlockSec交易数据
"""
from flask import Flask, render_template, request, jsonify, send_file
import asyncio
from playwright.async_api import async_playwright
import json
import csv
import io
import sys
import os
from datetime import datetime
from convert_to_test_case_v2 import (
    extract_transfers_from_data,
    extract_swaps_from_data,
    build_execution_tree_simplified,
    generate_test_case_format,
    format_address
)

app = Flask(__name__)

# 存储提取的数据（临时）
extracted_data_cache = {}

async def extract_blocksec_data(tx_hash: str):
    """提取BlockSec数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
        
        # 监听API响应
        trace_data = None
        async def handle_response(response):
            nonlocal trace_data
            if '/api/v1/onchain/tx/trace' in response.url:
                try:
                    trace_data = await response.json()
                except Exception as e:
                    print(f"解析trace数据时出错: {e}")
        
        page.on('response', handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            await page.wait_for_timeout(15000)
            
            return {
                'success': True,
                'tx_hash': tx_hash,
                'trace_data': trace_data
            }
        except Exception as e:
            return {
                'success': False,
                'tx_hash': tx_hash,
                'error': str(e)
            }
        finally:
            await browser.close()

def process_tx_data(trace_data):
    """处理交易数据并生成分析结果"""
    if not trace_data:
        return None
    
    data_map = trace_data.get('dataMap', {})
    main_trace = trace_data.get('mainTrace', [])
    
    # 提取数据
    transfers = extract_transfers_from_data(data_map)
    swaps = extract_swaps_from_data(data_map, main_trace)
    execution_tree = build_execution_tree_simplified(swaps, main_trace, data_map)
    
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
        'formatted_output': generate_test_case_format(
            trace_data.get('tx_hash', ''),
            swaps,
            execution_tree,
            transfers
        )
    }

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

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
        result = asyncio.run(extract_blocksec_data(tx_hash))
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', '提取数据失败')
            }), 500
        
        if not result.get('trace_data'):
            return jsonify({
                'success': False,
                'error': '未能获取trace数据，请确认交易哈希正确'
            }), 500
        
        # 处理数据
        analysis = process_tx_data(result['trace_data'])
        
        if not analysis:
            return jsonify({
                'success': False,
                'error': '处理数据失败'
            }), 500
        
        # 格式化结果
        response_data = {
            'success': True,
            'tx_hash': tx_hash,
            'stats': analysis['stats'],
            'swaps': [
                {
                    'address': format_address(s.get('address', '')),
                    'method': s.get('method', ''),
                    'gasUsed': s.get('gasUsed', 0)
                }
                for s in analysis['swaps']
            ],
            'transfers': [
                {
                    'from': format_address(t.get('from', '')),
                    'to': format_address(t.get('to', '')),
                    'token': format_address(t.get('token', '')),
                    'amount': t.get('amount', '0'),
                    'type': t.get('type', 'Direct'),
                    'gasCost': t.get('gasCost', 0)
                }
                for t in analysis['transfers']
            ],
            'execution_tree': {
                'root_count': len(analysis['execution_tree']['root_nodes']),
                'root_nodes': [
                    format_address(analysis['execution_tree']['nodes'].get(node_id, {}).get('address', ''))
                    for node_id in analysis['execution_tree']['root_nodes']
                ]
            },
            'formatted_output': analysis['formatted_output']
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

@app.route('/api/analyze-batch', methods=['POST'])
def analyze_batch():
    """批量分析交易（从CSV）"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': '只支持CSV文件'}), 400
    
    try:
        # 读取CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        
        tx_hashes = []
        for row in csv_reader:
            if row and row[0].strip():
                tx_hash = row[0].strip()
                if tx_hash.startswith('0x') and len(tx_hash) == 66:
                    tx_hashes.append(tx_hash)
        
        if not tx_hashes:
            return jsonify({'success': False, 'error': 'CSV文件中没有有效的交易哈希'}), 400
        
        if len(tx_hashes) > 10:
            return jsonify({'success': False, 'error': '一次最多处理10个交易'}), 400
        
        # 批量处理
        results = []
        for tx_hash in tx_hashes:
            try:
                result = asyncio.run(extract_blocksec_data(tx_hash))
                if result['success'] and result.get('trace_data'):
                    analysis = process_tx_data(result['trace_data'])
                    if analysis:
                        results.append({
                            'tx_hash': tx_hash,
                            'success': True,
                            'stats': analysis['stats'],
                            'formatted_output': analysis['formatted_output']
                        })
                    else:
                        results.append({
                            'tx_hash': tx_hash,
                            'success': False,
                            'error': '处理数据失败'
                        })
                else:
                    results.append({
                        'tx_hash': tx_hash,
                        'success': False,
                        'error': result.get('error', '提取数据失败')
                    })
            except Exception as e:
                results.append({
                    'tx_hash': tx_hash,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'total': len(tx_hashes),
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'处理CSV文件失败: {str(e)}'
        }), 500

@app.route('/api/download-result', methods=['POST'])
def download_result():
    """下载分析结果"""
    data = request.json
    formatted_output = data.get('formatted_output', '')
    tx_hash = data.get('tx_hash', 'unknown')
    
    # 创建文件
    output = io.StringIO()
    output.write(formatted_output)
    output.seek(0)
    
    filename = f'tx_analysis_{tx_hash[:10]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)


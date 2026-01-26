#!/usr/bin/env python3
"""
生成 MEV 区块 Token Flow Graph HTML 页面
包含每笔交易的 PnL 和 EigenTx 链接
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

def get_block_mev_data(block_number):
    """获取区块 MEV 数据"""
    mcp_server = "/Users/kezheng/Codes/CursorDeveloper/MEVAL/eigenphi-backend-go/bin/mcp-server"
    
    request = {
        "method": "tools/call",
        "params": {
            "name": "get_eigenphi_block_mev",
            "arguments": {
                "block_number": block_number
            }
        }
    }
    
    try:
        result = subprocess.run(
            [mcp_server],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"错误: MCP 服务器返回错误: {result.stderr}")
            return None
        
        response = json.loads(result.stdout)
        
        if "error" in response:
            print(f"错误: {response['error']}")
            return None
        
        text = response['result']['content'][0]['text']
        return parse_block_mev_text(text)
    except Exception as e:
        print(f"获取区块 {block_number} MEV 数据失败: {e}")
        return None

def parse_block_mev_text(text):
    """解析区块 MEV 文本数据"""
    lines = text.strip().split('\n')
    
    result = {
        'block_number': None,
        'type_summaries': [],
        'transactions': []
    }
    
    current_tx = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 解析区块号
        if line.startswith('区块 ') and 'MEV 汇总:' in line:
            match = re.search(r'区块 (\d+)', line)
            if match:
                result['block_number'] = int(match.group(1))
        
        # 解析类型汇总
        elif line.startswith('- 类型汇总:'):
            continue
        elif line.startswith('  - '):
            # 类型汇总行: "  - Arbitrage: Profit X USD, Cost Y USD, Revenue Z USD"
            match = re.match(r'  - (\w+): Profit ([\d.+-]+) USD, Cost ([\d.+-]+) USD, Revenue ([\d.+-]+) USD', line)
            if match:
                result['type_summaries'].append({
                    'type': match.group(1),
                    'profit': match.group(2),
                    'cost': match.group(3),
                    'revenue': match.group(4)
                })
        
        # 解析交易列表
        elif line.startswith('- 交易列表:'):
            continue
        elif re.match(r'\s*- \[(\d+)\] (0x[a-fA-F0-9]+)', line):
            # 新交易: "  - [28] 0x..." 或 "- [28] 0x..."
            match = re.match(r'\s*- \[(\d+)\] (0x[a-fA-F0-9]+)', line)
            if match:
                if current_tx:
                    result['transactions'].append(current_tx)
                current_tx = {
                    'index': int(match.group(1)),
                    'tx_hash': match.group(2),
                    'types': [],
                    'sandwich_role': None,
                    'profit': None,
                    'cost': None,
                    'revenue': None,
                    'pnl_url': None,
                    'eigentx_url': None
                }
        elif current_tx:
            # 交易属性（支持不同的缩进）
            if '- Types: ' in line:
                types_str = line.split('- Types: ')[1].strip()
                current_tx['types'] = [t.strip() for t in types_str.split(',')]
            elif '- Sandwich Role: ' in line:
                current_tx['sandwich_role'] = line.split('- Sandwich Role: ')[1].strip()
            elif '- Profit: ' in line:
                profit_str = line.split('- Profit: ')[1].strip()
                current_tx['profit'] = profit_str.replace(' USD', '').strip()
            elif '- Cost: ' in line:
                cost_str = line.split('- Cost: ')[1].strip()
                current_tx['cost'] = cost_str.replace(' USD', '').strip()
            elif '- Revenue: ' in line:
                revenue_str = line.split('- Revenue: ')[1].strip()
                current_tx['revenue'] = revenue_str.replace(' USD', '').strip()
            elif '- EigenPhi PnL: ' in line:
                current_tx['pnl_url'] = line.split('- EigenPhi PnL: ')[1].strip()
            elif '- EigenTx: ' in line:
                current_tx['eigentx_url'] = line.split('- EigenTx: ')[1].strip()
    
    if current_tx:
        result['transactions'].append(current_tx)
    
    return result

def generate_html(block_data, output_dir):
    """生成 HTML 文件"""
    block_number = block_data['block_number']
    
    # 计算总利润
    total_profit = sum(float(tx['profit']) for tx in block_data['transactions'] if tx['profit'])
    
    # 统计交易类型
    type_counts = {}
    for tx in block_data['transactions']:
        for tx_type in tx['types']:
            type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>区块 {block_number} - MEV 交易 Token Flow Graph</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .transaction {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .transaction-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .tx-index {{
            font-size: 18px;
            font-weight: bold;
            color: #2196F3;
        }}
        .tx-hash {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #666;
        }}
        .tx-type {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .type-arbitrage {{
            background-color: #E3F2FD;
            color: #1976D2;
        }}
        .type-liquidation {{
            background-color: #FFF3E0;
            color: #F57C00;
        }}
        .type-sandwich {{
            background-color: #FCE4EC;
            color: #C2185B;
        }}
        .tx-info {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .info-item {{
            font-size: 14px;
        }}
        .info-label {{
            color: #999;
            margin-right: 5px;
        }}
        .info-value {{
            color: #333;
            font-weight: 500;
        }}
        .profit-positive {{
            color: #4CAF50;
        }}
        .profit-negative {{
            color: #F44336;
        }}
        .tx-links {{
            display: flex;
            gap: 15px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}
        .tx-link {{
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            background-color: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            transition: background-color 0.2s;
        }}
        .tx-link:hover {{
            background-color: #1976D2;
        }}
        .tx-link.pnl {{
            background-color: #4CAF50;
        }}
        .tx-link.pnl:hover {{
            background-color: #45a049;
        }}
        .svg-container {{
            width: 100%;
            overflow-x: auto;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 10px;
            background: #fafafa;
            margin-top: 15px;
        }}
        .svg-container svg {{
            display: block;
            margin: 0 auto;
        }}
        .summary {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2196F3;
        }}
        .stat-label {{
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>区块 {block_number} - MEV 交易 Token Flow Graph</h1>
        <div class="subtitle">共 {len(block_data['transactions'])} 笔 MEV 交易 | 总利润: {total_profit:+.2f} USD</div>

        <div class="summary">
            <h2>区块汇总</h2>
            <div class="summary-stats">
                <div class="stat-item">
                    <div class="stat-value">{len(block_data['transactions'])}</div>
                    <div class="stat-label">MEV 交易数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value profit-positive">{total_profit:+.2f}</div>
                    <div class="stat-label">总利润 (USD)</div>
                </div>'''
    
    # 添加类型统计
    for tx_type, count in type_counts.items():
        html += f'''
                <div class="stat-item">
                    <div class="stat-value">{count}</div>
                    <div class="stat-label">{tx_type} 交易</div>
                </div>'''
    
    html += '''
            </div>
        </div>'''
    
    # 生成每笔交易的 HTML
    for tx in block_data['transactions']:
        tx_type_class = 'type-arbitrage'
        if 'Liquidation' in tx['types']:
            tx_type_class = 'type-liquidation'
        elif 'Sandwich' in tx['types']:
            tx_type_class = 'type-sandwich'
        
        profit_class = 'profit-positive' if tx['profit'] and float(tx['profit']) >= 0 else 'profit-negative'
        profit_sign = '+' if tx['profit'] and float(tx['profit']) >= 0 else ''
        
        types_text = ', '.join(tx['types'])
        
        html += f'''
        <!-- Transaction {tx['index']} -->
        <div class="transaction">
            <div class="transaction-header">
                <div>
                    <span class="tx-index">[{tx['index']}]</span>
                    <span class="tx-hash">{tx['tx_hash']}</span>
                </div>
                <span class="tx-type {tx_type_class}">{types_text}</span>
            </div>
            <div class="tx-info">
                <div class="info-item">
                    <span class="info-label">利润:</span>
                    <span class="info-value {profit_class}">{profit_sign}{tx['profit']} USD</span>
                </div>
                <div class="info-item">
                    <span class="info-label">成本:</span>
                    <span class="info-value">{tx['cost']} USD</span>
                </div>
                <div class="info-item">
                    <span class="info-label">收入:</span>
                    <span class="info-value">{tx['revenue']} USD</span>
                </div>'''
        
        if tx['sandwich_role']:
            html += f'''
                <div class="info-item">
                    <span class="info-label">Sandwich Role:</span>
                    <span class="info-value">{tx['sandwich_role']}</span>
                </div>'''
        
        html += '''
            </div>
            <div class="tx-links">'''
        
        if tx['pnl_url']:
            html += f'''
                <a href="{tx['pnl_url']}" target="_blank" class="tx-link pnl">📊 EigenPhi PnL</a>'''
        
        if tx['eigentx_url']:
            html += f'''
                <a href="{tx['eigentx_url']}" target="_blank" class="tx-link">🔗 EigenTx</a>'''
        
        html += '''
            </div>
            <div class="svg-container">
                <object data="''' + tx['tx_hash'][:20] + '''_flow.svg" type="image/svg+xml" style="width: 100%; height: auto;"></object>
            </div>
        </div>'''
    
    html += '''
    </div>
</body>
</html>'''
    
    # 保存文件
    output_file = os.path.join(output_dir, 'index.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 已生成 HTML 文件: {output_file}")
    return output_file

def main():
    if len(sys.argv) < 2:
        print("用法: python3 generate_mev_block_html.py <block_number>")
        sys.exit(1)
    
    block_number = int(sys.argv[1])
    # 使用项目根目录（CallTraceSniffer）
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent  # 从 scripts/ 到项目根
    output_dir = base_dir / 'token_flow_graphs' / f'block_{block_number}'
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 输出目录: {output_dir}")
    
    print(f"📊 获取区块 {block_number} 的 MEV 数据...")
    block_data = get_block_mev_data(block_number)
    
    if not block_data:
        print("❌ 获取区块数据失败")
        sys.exit(1)
    
    print(f"✅ 获取到 {len(block_data['transactions'])} 笔交易")
    if len(block_data['transactions']) == 0:
        print("⚠️  警告: 没有解析到任何交易，检查解析逻辑")
        # 调试输出
        print("\n调试信息:")
        print(f"区块号: {block_data['block_number']}")
        print(f"类型汇总数: {len(block_data['type_summaries'])}")
        return
    
    print(f"📝 生成 HTML 文件到: {output_dir}")
    generate_html(block_data, str(output_dir))
    print(f"🎉 完成！")

if __name__ == '__main__':
    main()

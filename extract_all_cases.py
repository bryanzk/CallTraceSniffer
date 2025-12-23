#!/usr/bin/env python3
"""
批量提取test_cases.yaml中所有交易的BlockSec数据
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re

# 从test_cases.yaml中提取的交易列表
TRANSACTIONS = [
    {
        'case': 'case9',
        'tx_hash': '0x4036183ad1acab4c38a6d3027eb6e734fcc587477b6f26a109f1c6f49cbd5ec1'
    },
    {
        'case': 'case12',
        'tx_hash': '0x3d59ac33bcc54b76ba9000443983c0fa9b347423348231be1810d07aa724ae69'
    },
    {
        'case': 'case21',
        'tx_hash': '0xe8e213f71cad840d681b6ae34870e7f75518c6d66ebdbc2500d0e49b9112a873'
    },
    {
        'case': 'case33',
        'tx_hash': '0x1fc91d998a44718d7cc917aa418abf80af3eab79d89c798212b7746857f1be1c'
    }
]

async def extract_transaction(case_name: str, tx_hash: str):
    """提取单个交易的BlockSec数据"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
        print(f"\n[{case_name}] 正在访问: {url}")
        
        # 监听API响应
        trace_data = None
        async def handle_response(response):
            nonlocal trace_data
            if '/api/v1/onchain/tx/trace' in response.url:
                try:
                    trace_data = await response.json()
                    print(f"[{case_name}] ✓ 成功获取trace数据")
                except Exception as e:
                    print(f"[{case_name}] 解析trace数据时出错: {e}")
        
        page.on('response', handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            print(f"[{case_name}] 页面已加载")
            
            # 等待API响应
            await page.wait_for_timeout(15000)
            
            # 保存结果
            result = {
                'case': case_name,
                'tx_hash': tx_hash,
                'trace_data': trace_data
            }
            
            output_file = f'{case_name}_blocksec_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"[{case_name}] ✓ 数据已保存到 {output_file}")
            if trace_data:
                if isinstance(trace_data, dict):
                    print(f"[{case_name}]   - Trace数据键: {list(trace_data.keys())}")
            
            return result
            
        except Exception as e:
            print(f"[{case_name}] 错误: {e}")
            return None
        finally:
            await browser.close()

async def extract_all():
    """提取所有交易"""
    results = []
    for tx_info in TRANSACTIONS:
        result = await extract_transaction(tx_info['case'], tx_info['tx_hash'])
        if result:
            results.append(result)
        # 在交易之间稍作延迟
        await asyncio.sleep(2)
    
    print(f"\n✓ 总共提取了 {len(results)} 个交易的数据")
    return results

if __name__ == "__main__":
    asyncio.run(extract_all())


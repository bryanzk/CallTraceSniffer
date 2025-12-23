#!/usr/bin/env python3
"""
提取交易 0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004 的BlockSec数据
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def extract_invocation_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        tx_hash = "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004"
        url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
        print(f"正在访问: {url}")
        
        # 监听API响应
        trace_data = None
        async def handle_response(response):
            nonlocal trace_data
            if '/api/v1/onchain/tx/trace' in response.url:
                try:
                    trace_data = await response.json()
                    print(f"✓ 成功获取trace数据")
                except Exception as e:
                    print(f"解析trace数据时出错: {e}")
        
        page.on('response', handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            print("页面已加载")
            
            # 等待API响应
            await page.wait_for_timeout(15000)
            
            # 保存结果
            result = {
                'tx_hash': tx_hash,
                'trace_data': trace_data
            }
            
            output_file = 'case0_blocksec_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ 数据已保存到 {output_file}")
            if trace_data:
                print(f"  - Trace API数据: 已获取")
                if isinstance(trace_data, dict):
                    print(f"  - Trace数据键: {list(trace_data.keys())}")
            
        except Exception as e:
            print(f"错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_invocation_flow())



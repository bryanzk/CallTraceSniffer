#!/usr/bin/env python3
"""
提取BlockSec页面中的invocation flow数据
"""
import asyncio
from playwright.async_api import async_playwright
import json
import re

async def extract_invocation_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        url = "https://app.blocksec.com/explorer/tx/eth/0x404e80ee3d321a6db4673a06c42db85231e95aea5a88d74b5cf28b0b8f3218c3/"
        print(f"正在访问: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=120000)
        
        # 等待页面加载
        await page.wait_for_timeout(10000)
        
        # 尝试查找并展开所有可展开的元素
        print("正在查找可展开的元素...")
        expand_buttons = await page.query_selector_all('button[aria-expanded="false"]')
        print(f"找到 {len(expand_buttons)} 个可展开的按钮")
        
        # 展开所有可展开的元素
        for i, button in enumerate(expand_buttons):
            try:
                await button.click()
                await page.wait_for_timeout(500)
                print(f"已展开第 {i+1} 个元素")
            except Exception as e:
                print(f"展开第 {i+1} 个元素时出错: {e}")
        
        # 等待内容加载
        await page.wait_for_timeout(3000)
        
        # 尝试查找包含"invocation"或"flow"的元素
        print("\n正在查找invocation flow相关内容...")
        
        # 方法1: 查找所有文本内容
        all_text = await page.evaluate("""
            () => {
                const texts = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    if (text && text.length > 5) {
                        texts.push(text);
                    }
                }
                return texts;
            }
        """)
        
        # 查找包含调用相关的文本
        invocation_texts = [t for t in all_text if any(keyword in t.lower() for keyword in 
                       ['invocation', 'flow', 'call', 'trace', '0x', 'function'])]
        
        print(f"\n找到 {len(invocation_texts)} 个相关文本片段")
        for i, text in enumerate(invocation_texts[:50]):  # 只显示前50个
            print(f"{i+1}. {text[:100]}...")
        
        # 方法2: 提取所有表格数据
        print("\n正在提取表格数据...")
        tables = await page.evaluate("""
            () => {
                const tables = [];
                const tableElements = document.querySelectorAll('table');
                tableElements.forEach((table, index) => {
                    const rows = [];
                    table.querySelectorAll('tr').forEach(tr => {
                        const cells = [];
                        tr.querySelectorAll('td, th').forEach(cell => {
                            cells.push(cell.textContent.trim());
                        });
                        if (cells.length > 0) {
                            rows.push(cells);
                        }
                    });
                    if (rows.length > 0) {
                        tables.push({index, rows});
                    }
                });
                return tables;
            }
        """)
        
        print(f"找到 {len(tables)} 个表格")
        for i, table in enumerate(tables):
            print(f"\n表格 {i+1} ({len(table['rows'])} 行):")
            for j, row in enumerate(table['rows'][:10]):  # 只显示前10行
                print(f"  行 {j+1}: {row}")
        
        # 方法3: 尝试从API响应中提取数据
        print("\n正在监听网络请求...")
        trace_data = None
        
        async def handle_response(response):
            nonlocal trace_data
            if '/api/v1/onchain/tx/trace' in response.url:
                try:
                    trace_data = await response.json()
                    print("成功获取trace数据!")
                except:
                    pass
        
        page.on('response', handle_response)
        
        # 重新加载页面以捕获API响应
        await page.reload(wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(10000)
        
        # 保存结果
        result = {
            'invocation_texts': invocation_texts,
            'tables': tables,
            'trace_data': trace_data
        }
        
        with open('invocation_flow_data.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据已保存到 invocation_flow_data.json")
        print(f"找到 {len(invocation_texts)} 个相关文本片段")
        print(f"找到 {len(tables)} 个表格")
        if trace_data:
            print("成功获取trace API数据")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_invocation_flow())


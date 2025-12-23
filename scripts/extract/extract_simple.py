#!/usr/bin/env python3
"""
简化版：提取BlockSec页面中的invocation flow数据
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
        
        url = "https://app.blocksec.com/explorer/tx/eth/0x404e80ee3d321a6db4673a06c42db85231e95aea5a88d74b5cf28b0b8f3218c3/"
        print(f"正在访问: {url}")
        
        # 监听API响应
        trace_data = None
        async def handle_response(response):
            nonlocal trace_data
            if '/api/v1/onchain/tx/trace' in response.url:
                try:
                    trace_data = await response.json()
                    print(f"✓ 成功获取trace数据，包含 {len(str(trace_data))} 字符")
                except Exception as e:
                    print(f"解析trace数据时出错: {e}")
        
        page.on('response', handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            print("页面已加载")
            
            # 等待API响应
            await page.wait_for_timeout(15000)
            
            # 尝试展开所有可展开的元素
            print("正在展开可展开的元素...")
            expand_buttons = await page.query_selector_all('button[aria-expanded="false"], [aria-expanded="false"]')
            print(f"找到 {len(expand_buttons)} 个可展开的元素")
            
            for i, button in enumerate(expand_buttons[:20]):  # 只展开前20个
                try:
                    await button.scroll_into_view_if_needed()
                    await button.click(timeout=2000)
                    await page.wait_for_timeout(300)
                except:
                    pass
            
            await page.wait_for_timeout(5000)
            
            # 提取所有表格数据
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
                                const text = cell.textContent.trim();
                                if (text) cells.push(text);
                            });
                            if (cells.length > 0) {
                                rows.push(cells);
                            }
                        });
                        if (rows.length > 0) {
                            tables.push({index, rows, rowCount: rows.length});
                        }
                    });
                    return tables;
                }
            """)
            
            print(f"找到 {len(tables)} 个表格")
            
            # 提取所有包含地址或函数调用的文本
            print("\n正在提取调用相关信息...")
            call_info = await page.evaluate("""
                () => {
                    const results = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        const text = node.textContent.trim();
                        // 查找包含地址(0x开头)或函数调用的文本
                        if (text && (text.match(/0x[a-fA-F0-9]{40}/) || 
                                     text.toLowerCase().includes('call') ||
                                     text.toLowerCase().includes('invocation') ||
                                     text.toLowerCase().includes('function'))) {
                            results.push(text);
                        }
                    }
                    return results;
                }
            """)
            
            print(f"找到 {len(call_info)} 个相关文本片段")
            
            # 保存结果
            result = {
                'tables': tables,
                'call_info': call_info[:500],  # 只保存前500个
                'trace_data': trace_data
            }
            
            output_file = 'invocation_flow_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ 数据已保存到 {output_file}")
            print(f"  - 表格数量: {len(tables)}")
            print(f"  - 调用信息片段: {len(call_info)}")
            if trace_data:
                print(f"  - Trace API数据: 已获取")
                # 尝试提取嵌套调用结构
                if isinstance(trace_data, dict):
                    print(f"  - Trace数据键: {list(trace_data.keys())}")
            
        except Exception as e:
            print(f"错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_invocation_flow())



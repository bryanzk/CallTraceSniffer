"""
BlockSec数据提取服务
"""
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright
from ..config import config


class BlockSecExtractor:
    """BlockSec数据提取器"""
    
    async def extract_blocksec_data(self, tx_hash: str) -> Optional[Dict]:
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
                
                if trace_data:
                    return {
                        'success': True,
                        'tx_hash': tx_hash,
                        'trace_data': trace_data
                    }
                else:
                    return {
                        'success': False,
                        'tx_hash': tx_hash,
                        'error': '未找到trace数据'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'tx_hash': tx_hash,
                    'error': str(e)
                }
            finally:
                await browser.close()


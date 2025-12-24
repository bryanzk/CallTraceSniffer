"""
BlockSec数据提取服务
"""
import json
import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
from ..config import config


class BlockSecExtractor:
    """BlockSec数据提取器"""

    @staticmethod
    def parse_simulation_url(sim_url: str) -> Tuple[str, str]:
        """解析并校验BlockSec模拟交易URL，返回(tx_hash, normalized_url)"""
        if not sim_url:
            raise ValueError("模拟URL不能为空")
        parsed = urlparse(sim_url)
        if parsed.scheme not in ("http", "https") or "blocksec.com" not in parsed.netloc:
            raise ValueError("无效的BlockSec URL")
        match = re.search(r"/explorer/tx/eth/(0x[a-fA-F0-9]{64})", parsed.path)
        if not match:
            raise ValueError("URL中未找到交易哈希")
        tx_hash = match.group(1)
        query = parse_qs(parsed.query)
        event = query.get("event", [""])[0]
        if event and event != "simulation":
            raise ValueError("URL不是simulation类型")
        return tx_hash, sim_url

    @staticmethod
    def _find_trace_payload(payload: object) -> Optional[Dict]:
        if isinstance(payload, dict):
            if "dataMap" in payload and "mainTrace" in payload:
                return payload
            for key in ("data", "result"):
                sub = payload.get(key)
                if isinstance(sub, dict) and "dataMap" in sub and "mainTrace" in sub:
                    return sub
        return None

    async def _extract_trace_from_page(self, url: str) -> Optional[Dict]:
        trace_data = None
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()

            async def handle_response(response):
                nonlocal trace_data
                if "/api/" not in response.url:
                    return
                try:
                    payload = await response.json()
                except Exception:
                    return
                trace = self._find_trace_payload(payload)
                if trace:
                    trace_data = trace

            page.on('response', handle_response)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                await page.wait_for_timeout(15000)
            finally:
                await browser.close()

        return trace_data
    
    async def extract_blocksec_data(self, tx_hash: str) -> Optional[Dict]:
        """提取BlockSec数据"""
        url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
        trace_data = await self._extract_trace_from_page(url)
        if trace_data:
            return {
                'success': True,
                'tx_hash': tx_hash,
                'trace_data': trace_data
            }
        return {
            'success': False,
            'tx_hash': tx_hash,
            'error': '未找到trace数据'
        }

    async def extract_blocksec_simulation_data(self, sim_url: str) -> Optional[Dict]:
        """提取BlockSec模拟交易数据"""
        tx_hash, normalized_url = self.parse_simulation_url(sim_url)
        trace_data = await self._extract_trace_from_page(normalized_url)
        if trace_data:
            return {
                'success': True,
                'tx_hash': tx_hash,
                'trace_data': trace_data
            }
        return {
            'success': False,
            'tx_hash': tx_hash,
            'error': '未找到simulation trace数据'
        }

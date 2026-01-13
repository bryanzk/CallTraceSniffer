#!/usr/bin/env python3
"""
BlockSec Simulation API Client

直接调用 BlockSec 的 API 执行模拟，无需浏览器自动化。
支持两种模式:
1. 纯 API 模式（需要提取 cookies/cf_clearance）
2. Session 模式（从浏览器提取认证信息）
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.blocksec_simulation import (
    build_simulation_request_payload,
    run_simulation_with_payload,
)


@dataclass
class SimulationParams:
    """模拟参数"""
    sender: str
    receiver: str
    input_data: str
    value: str  # 十六进制或十进制
    gas_limit: int
    gas_price: Optional[str] = None
    block_number: Optional[int] = None
    position_in_block: Optional[int] = None
    chain: str = "eth"
    simulation_type: int = 0  # 0=call, 1=deploy ?
    
    def to_api_payload(self) -> Dict[str, Any]:
        """转换为 API payload 格式"""
        # 处理 value - 确保是正确的格式
        value = self.value
        if isinstance(value, str) and value.startswith("0x"):
            value = str(int(value, 16))
        
        payload = {
            "chain": self.chain,
            "from": self.sender.lower(),
            "to": self.receiver.lower(),
            "data": self.input_data,
            "value": value,
            "gasLimit": str(self.gas_limit),
            "simulationType": self.simulation_type,
        }
        
        if self.gas_price:
            payload["gasPrice"] = self.gas_price
        if self.block_number:
            payload["blockNumber"] = self.block_number
        if self.position_in_block is not None:
            payload["position"] = self.position_in_block
            
        return payload


def _load_api_payload(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    if raw.startswith("@"):
        file_path = raw[1:]
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"指定的 API payload 文件不存在: {file_path}")
        with open(path) as f:
            return json.load(f)
    return json.loads(raw)


def extract_cookies_from_browser(
    output_file: str = "blocksec_cookies.json",
    browser_channel: str = "chrome",
    user_data_dir: Optional[str] = None,
) -> None:
    """
    从浏览器提取 cookies（需要手动完成 Cloudflare 验证）
    
    优先使用系统 Chrome（channel="chrome"）以减少内置 Chromium 崩溃风险。
    如失败会回退到默认的 chromium。
    """
    import asyncio
    from playwright.async_api import async_playwright
    from playwright._impl._errors import TargetClosedError
    
    async def _extract():
        async with async_playwright() as p:
            # 使用持久化配置目录
            ud = Path(user_data_dir) if user_data_dir else Path.home() / ".blocksec_browser_profile"
            ud.mkdir(parents=True, exist_ok=True)
            
            async def _launch(channel: Optional[str]):
                return await p.chromium.launch_persistent_context(
                    str(ud),
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                    channel=channel,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
            
            context = None
            last_err = None
            # 优先尝试用户指定 channel（默认 chrome），失败则回退 chromium
            for ch in [browser_channel, None] if browser_channel != "chromium" else [None]:
                try:
                    context = await _launch(ch)
                    break
                except TargetClosedError as e:
                    last_err = e
                except Exception as e:
                    last_err = e
            
            if context is None:
                raise RuntimeError(f"无法启动浏览器用于提取 cookies: {last_err}")
            
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://app.blocksec.com/explorer", wait_until="domcontentloaded")
            
            print("=" * 60)
            print("浏览器已打开。请完成 Cloudflare 验证。")
            print("验证完成后，页面应该正常加载。")
            print("完成后请回到终端按 Enter 继续保存 cookies...")
            print("=" * 60)
            
            input()
            
            # 获取 cookies
            cookies = await context.cookies()
            
            # 保存到文件
            with open(output_file, "w") as f:
                json.dump(cookies, f, indent=2)
            
            print(f"Cookies 已保存到: {output_file}")
            
            await context.close()
    
    asyncio.run(_extract())


def run_simulation_with_api(
    params: Optional[SimulationParams],
    cookie_file: Optional[str] = None,
    output_file: Optional[str] = None,
    get_trace: bool = False,
    custom_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    使用 API 执行模拟
    
    Args:
        params: 模拟参数
        cookie_file: cookies 文件路径
        output_file: 输出文件路径
        get_trace: 是否获取 trace 数据
        
    Returns:
        模拟结果
    """
    print("正在模拟交易...")
    if custom_payload is not None:
        payload_to_send = custom_payload
    else:
        raw_payload = params.to_api_payload()
        payload_to_send = build_simulation_request_payload(raw_payload, convert_value_for_flat=False)

    sim_result = run_simulation_with_payload(
        payload_to_send,
        cookie_file=Path(cookie_file) if cookie_file else None,
        fetch_trace=get_trace,
    )

    print("模拟成功!")
    print(f"  Simulation ID: {sim_result.simulation_id}")
    print(f"  TX Hash: {sim_result.tx_hash}")
    print(f"  Result URL: {sim_result.simulation_url}")

    full_result = {
        "simulationId": sim_result.simulation_id,
        "txHash": sim_result.tx_hash,
        "resultUrl": sim_result.simulation_url,
        "timestamp": sim_result.timestamp_ms,
    }

    if get_trace and sim_result.trace_data:
        full_result["trace"] = sim_result.trace_data
    if output_file:
        with open(output_file, "w") as f:
            json.dump(full_result, f, indent=2)
        print(f"结果已保存到: {output_file}")
    return full_result


# 默认测试参数
DEFAULT_PARAMS = SimulationParams(
    sender="0x39E2B0f5c451AA82aB5713461599660F0501EbC0",
    receiver="0xc2fE164D2cFcfeB6164242b807C57c691F7cfb37",
    input_data=(
        "0x308618e0554a476a092703abdb3ef35c80e0d76d32939f20c156feaccb7f750b"
        "997b36a68625c7c596f0b41a580ac03e362010af608f182004514906fc121c787"
        "8424a5c928cad1852cc54589200e975f6003004608dadd4b1673a651a4cd35729"
        "fc657e76a1f9e600d9e5b600001f30c8691c9c0b050c2c3d46dad37b1b4c3666f"
        "13ecfce0f9067471800029001ff0fd7d80010"
    ),
    value="0x204f9fae",
    gas_limit=5000000,
    block_number=24065056,
    position_in_block=5,
)


def main():
    parser = argparse.ArgumentParser(
        description="BlockSec Simulation API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 1. 首先提取 cookies（只需要做一次）
  python blocksec_api.py --extract-cookies

  # 2. 使用默认参数运行模拟
  python blocksec_api.py --cookie-file blocksec_cookies.json

  # 3. 使用自定义参数
  python blocksec_api.py --cookie-file blocksec_cookies.json \\
      --sender 0x... --receiver 0x... --input-data 0x... \\
      --value 0x204f9fae --gas-limit 5000000 --block 24065056

  # 4. 获取 trace 数据
  python blocksec_api.py --cookie-file blocksec_cookies.json --trace

  # 5. 使用已抓到的 custom payload（JSON 字符串或 @file）
  python blocksec_api.py --cookie-file blocksec_cookies.json \\
      --api-payload '{"chainID":1,"simulationType":"custom", ... }'
        """
    )
    
    parser.add_argument("--extract-cookies", action="store_true",
                        help="从浏览器提取 cookies")
    parser.add_argument("--browser-channel", default="chrome",
                        help="提取 cookies 时使用的浏览器 channel (chrome/msedge/chromium)")
    parser.add_argument("--user-data-dir", dest="extract_user_data_dir",
                        default=str(Path.home() / ".blocksec_browser_profile"),
                        help="提取 cookies 使用的持久化目录 (默认: ~/.blocksec_browser_profile)")
    parser.add_argument("--cookie-file", default="blocksec_cookies.json",
                        help="Cookies 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--trace", action="store_true", help="获取 trace 数据")
    
    # 模拟参数
    parser.add_argument("--sender", help="发送者地址")
    parser.add_argument("--receiver", help="接收者地址")
    parser.add_argument("--input-data", help="调用数据 (calldata)")
    parser.add_argument("--value", help="发送值 (wei，十六进制或十进制)")
    parser.add_argument("--gas-limit", type=int, help="Gas 限制")
    parser.add_argument("--gas-price", help="Gas 价格")
    parser.add_argument("--block", type=int, help="目标区块号")
    parser.add_argument("--position", type=int, help="区块内位置")
    parser.add_argument("--chain", default="eth", help="链 (eth, bsc, polygon 等)")
    
    # JSON 参数
    parser.add_argument("--params-json", help="JSON 格式的参数")
    parser.add_argument(
        "--api-payload",
        help="直接给出完整的 api payload（JSON 字符串或 @file）",
    )
    parser.add_argument("--simulation-type", type=int, default=0, help="simulationType 字段 (默认 0)")
    
    args = parser.parse_args()
    
    # 提取 cookies 模式
    if args.extract_cookies:
        extract_cookies_from_browser(
            output_file=args.cookie_file,
            browser_channel=args.browser_channel,
            user_data_dir=args.extract_user_data_dir,
        )
        return
    
    custom_payload = _load_api_payload(args.api_payload)
    if args.params_json and custom_payload:
        print("警告: --params-json 与 --api-payload 同时指定，将优先使用 api payload")
    params = None
    # 构建参数
    if custom_payload is None:
        if args.params_json:
            params_dict = json.loads(args.params_json)
            params = SimulationParams(
                sender=params_dict.get("sender", DEFAULT_PARAMS.sender),
                receiver=params_dict.get("receiver", DEFAULT_PARAMS.receiver),
                input_data=params_dict.get("inputData", DEFAULT_PARAMS.input_data),
                value=params_dict.get("value", DEFAULT_PARAMS.value),
                gas_limit=params_dict.get("gasLimit", DEFAULT_PARAMS.gas_limit),
                gas_price=params_dict.get("gasPrice"),
                block_number=params_dict.get("targetBlock", DEFAULT_PARAMS.block_number),
                position_in_block=params_dict.get("targetIndex", DEFAULT_PARAMS.position_in_block),
                chain=params_dict.get("chain", DEFAULT_PARAMS.chain),
                simulation_type=params_dict.get("simulationType", args.simulation_type),
            )
        else:
            params = SimulationParams(
                sender=args.sender or DEFAULT_PARAMS.sender,
                receiver=args.receiver or DEFAULT_PARAMS.receiver,
                input_data=args.input_data or DEFAULT_PARAMS.input_data,
                value=args.value or DEFAULT_PARAMS.value,
                gas_limit=args.gas_limit or DEFAULT_PARAMS.gas_limit,
                gas_price=args.gas_price,
                block_number=args.block or DEFAULT_PARAMS.block_number,
                position_in_block=args.position if args.position is not None else DEFAULT_PARAMS.position_in_block,
                chain=args.chain,
                simulation_type=args.simulation_type,
            )
    
    # 检查 cookie 文件是否存在
    if not Path(args.cookie_file).exists():
        print(f"错误: Cookie 文件不存在: {args.cookie_file}")
        print("请先运行: python blocksec_api.py --extract-cookies")
        return 1
    
    # 执行模拟
    try:
        run_simulation_with_api(
            params,
            cookie_file=args.cookie_file,
            output_file=args.output,
            get_trace=args.trace,
            custom_payload=custom_payload,
        )
    except PermissionError as e:
        print(f"\n{e}")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

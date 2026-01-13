#!/usr/bin/env python3
"""
Use Playwright to run a BlockSec simulation and print the resulting URL.

自动化方案:
1. 使用持久化用户配置目录 (--user-data-dir) 保存 Cloudflare 验证状态
2. 首次运行时需要手动完成验证，之后可以自动运行
3. 支持 stealth 模式来避免被检测

用法示例:
  # 首次运行（需要手动验证）
  python simulate_blocksec.py --user-data-dir ~/.blocksec_profile

  # 之后可以自动运行
  python simulate_blocksec.py --user-data-dir ~/.blocksec_profile --headless
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from playwright.async_api import async_playwright, BrowserContext
from calltrace.services.blocksec_simulation import build_simulation_request_payload

# 尝试导入 stealth 插件
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    stealth_async = None


DEFAULT_URL = (
    "https://app.blocksec.com/explorer/tx/eth/"
    "0xc45de9e0cba1ab5fa10fe54c970103d6db8451780edd023d6671ea8389f1d9e9"
)

DEFAULT_PAYLOAD = {
    "gasLimit": 5000000,
    "inputData": (
        "0x308618e0554a476a092703abdb3ef35c80e0d76d32939f20c156feaccb7f750b"
        "997b36a68625c7c596f0b41a580ac03e362010af608f182004514906fc121c787"
        "8424a5c928cad1852cc54589200e975f6003004608dadd4b1673a651a4cd35729"
        "fc657e76a1f9e600d9e5b600001f30c8691c9c0b050c2c3d46dad37b1b4c3666f"
        "13ecfce0f9067471800029001ff0fd7d80010"
    ),
    "receiver": "0xc2fE164D2cFcfeB6164242b807C57c691F7cfb37",
    "sender": "0x39E2B0f5c451AA82aB5713461599660F0501EbC0",
    "sourceTxnHash": "0xc45de9e0cba1ab5fa10fe54c970103d6db8451780edd023d6671ea8389f1d9e9",
    "targetBlock": 24065056,
    "targetIndex": 5,
    "value": "0x204f9fae",
}


def _coerce_payload(raw: Optional[str]) -> dict:
    if not raw:
        return DEFAULT_PAYLOAD
    parsed = json.loads(raw)
    return _normalize_payload(parsed)


def _normalize_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return DEFAULT_PAYLOAD
    try:
        api_payload = build_simulation_request_payload(payload, convert_value_for_flat=False)
    except Exception:
        api_payload = payload

    form_payload = {
        "gasLimit": api_payload.get("gasLimit") or payload.get("gasLimit"),
        "inputData": api_payload.get("data") or payload.get("inputData"),
        "receiver": api_payload.get("to") or payload.get("receiver"),
        "sender": api_payload.get("from") or payload.get("sender"),
        "sourceTxnHash": payload.get("sourceTxnHash"),
        "targetBlock": api_payload.get("blockNumber") or payload.get("targetBlock"),
        "targetIndex": api_payload.get("position") or payload.get("targetIndex"),
        "value": api_payload.get("value") or payload.get("value"),
    }
    return form_payload


async def _fill_by_label(page, labels: Iterable[str], value: str) -> bool:
    for label in labels:
        label_locator = page.locator(f'xpath=//label[contains(normalize-space(), "{label}")]').first
        if await label_locator.count() == 0:
            continue
        input_locator = label_locator.locator(
            "xpath=following::input[1] | following::textarea[1]"
        ).first
        if await input_locator.count() == 0:
            continue
        await input_locator.fill(value)
        return True
    for label in labels:
        text_locator = page.get_by_text(label, exact=False).first
        if await text_locator.count() == 0:
            continue
        container = text_locator.locator(
            "xpath=ancestor::*[.//input or .//textarea][1]"
        ).first
        if await container.count() == 0:
            continue
        input_locator = container.locator("input, textarea").first
        if await input_locator.count() == 0:
            continue
        await input_locator.fill(value)
        return True
    for label in labels:
        placeholder_locator = page.locator(
            f'input[placeholder*="{label}"], textarea[placeholder*="{label}"]'
        ).first
        if await placeholder_locator.count() == 0:
            continue
        await placeholder_locator.fill(value)
        return True
    return False


async def _dump_visible_form_fields(page) -> None:
    fields = await page.evaluate(
        """
        () => {
            const results = [];
            const inputs = Array.from(document.querySelectorAll('input, textarea'));
            inputs.forEach((el) => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const placeholder = el.getAttribute('placeholder') || '';
                const name = el.getAttribute('name') || '';
                const id = el.getAttribute('id') || '';
                let labelText = '';
                if (id) {
                    const label = document.querySelector(`label[for="${id}"]`);
                    if (label) labelText = label.textContent.trim();
                }
                if (!labelText) {
                    const container = el.closest('div');
                    if (container) {
                        const label = container.querySelector('label, span, p, div');
                        if (label) labelText = label.textContent.trim();
                    }
                }
                results.push({ labelText, placeholder, name, id });
            });
            return results;
        }
        """
    )
    print("可见表单字段:")
    for item in fields:
        print(f"- label={item['labelText']} placeholder={item['placeholder']} name={item['name']} id={item['id']}")


async def _set_input_by_id(page, input_id: str, value: str) -> bool:
    locator = page.locator(f"#{input_id}").first
    if await locator.count() == 0:
        return False
    await page.evaluate(
        """
        ([id, val]) => {
            const el = document.getElementById(id);
            if (!el) return false;
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }
        """,
        [input_id, value],
    )
    return True


async def _wait_for_manual_ready(page) -> None:
    await page.wait_for_timeout(1200)
    await page.wait_for_load_state("domcontentloaded", timeout=120000)


async def _apply_stealth(context: BrowserContext) -> None:
    """应用 stealth 设置来避免被检测为自动化浏览器"""
    if HAS_STEALTH:
        for page in context.pages:
            await stealth_async(page)
    else:
        # 手动注入一些基本的反检测脚本
        await context.add_init_script("""
            // 隐藏 webdriver 属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 修改 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 修改 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // 隐藏自动化标记
            window.chrome = {
                runtime: {},
            };
        """)


async def _wait_for_cloudflare(page, timeout: int = 30000) -> bool:
    """等待 Cloudflare 验证完成"""
    try:
        # 检查是否有 Cloudflare 验证
        cf_challenge = page.locator("text=Verify you are human")
        if await cf_challenge.count() > 0:
            print("检测到 Cloudflare 验证，等待完成...")
            # 等待验证消失
            await cf_challenge.wait_for(state="hidden", timeout=timeout)
            print("Cloudflare 验证完成")
            return True
    except Exception:
        pass
    return False


async def run_simulation(
    url: str,
    payload: dict,
    headless: bool,
    channel: Optional[str],
    debug: bool,
    user_data_dir: Optional[str],
    manual: bool,
    cdp_endpoint: Optional[str],
    stealth: bool = True,
    wait_cloudflare: bool = True,
) -> str:
    async with async_playwright() as p:
        context = None
        browser = None
        
        if cdp_endpoint:
            browser = await p.chromium.connect_over_cdp(cdp_endpoint)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            # 更真实的浏览器配置
            launch_kwargs = {
                "headless": headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            }
            if channel:
                launch_kwargs["channel"] = channel
            
            # 更真实的上下文配置
            context_kwargs = {
                "viewport": {"width": 1600, "height": 1000},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "color_scheme": "light",
            }
            
            if user_data_dir:
                # 确保目录存在
                Path(user_data_dir).mkdir(parents=True, exist_ok=True)
                context = await p.chromium.launch_persistent_context(
                    user_data_dir,
                    **launch_kwargs,
                    **context_kwargs,
                )
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                browser = await p.chromium.launch(**launch_kwargs)
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
        
        # 应用 stealth 模式
        if stealth and not cdp_endpoint:
            await _apply_stealth(context)
        
        # 导航到页面
        await page.goto(url, wait_until="domcontentloaded", timeout=120000)
        
        # 等待 Cloudflare 验证
        if wait_cloudflare:
            await _wait_for_cloudflare(page)
        
        if manual:
            await _wait_for_manual_ready(page)
        
        # 等待页面完全加载
        await page.wait_for_timeout(2000)
        
        # 点击 Simulator 按钮
        await page.get_by_role("button", name=re.compile("Simulator", re.I)).click()

        await page.wait_for_timeout(800)
        if debug:
            await _dump_visible_form_fields(page)

        field_map = [
            {
                "labels": ["Gas Limit", "Gas limit", "GasLimit"],
                "value": str(payload["gasLimit"]),
                "ids": ["gasLimit"],
                "required": True,
            },
            {
                "labels": ["Input Data", "Input", "Call Data", "InputData", "rawdata"],
                "value": payload["inputData"],
                "ids": ["inputData"],
                "required": True,
            },
            {
                "labels": ["Receiver", "To"],
                "value": payload["receiver"],
                "ids": ["receiver"],
                "required": True,
            },
            {
                "labels": ["Sender", "From"],
                "value": payload["sender"],
                "ids": ["sender"],
                "required": True,
            },
            {
                "labels": ["Source Txn Hash", "Source Tx Hash", "Source Hash"],
                "value": payload["sourceTxnHash"],
                "ids": ["sourceTxnHash", "sourceHash"],
                "required": False,
            },
            {
                "labels": ["Target Block", "Block"],
                "value": str(payload["targetBlock"]),
                "ids": ["block"],
                "required": True,
            },
            {
                "labels": ["Target Index", "Index", "Position in Block"],
                "value": str(payload["targetIndex"]),
                "ids": ["position"],
                "required": True,
            },
            {
                "labels": ["Value"],
                "value": str(payload["value"]),
                "ids": ["value"],
                "required": True,
            },
        ]

        for field in field_map:
            value = field["value"]
            filled = False
            for input_id in field["ids"]:
                filled = await _set_input_by_id(page, input_id, value)
                if filled:
                    break
            if not filled:
                filled = await _fill_by_label(page, field["labels"], value)
            if not filled and field["required"]:
                if debug:
                    await _dump_visible_form_fields(page)
                raise RuntimeError(f"Unable to locate input for labels: {field['labels']}")

        await page.get_by_role("button", name=re.compile("Simulate", re.I)).click()

        await page.wait_for_url(re.compile(r"event=simulation|simulation"), timeout=120000)
        result_url = page.url

        await context.close()
        return result_url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run BlockSec simulation via Playwright.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
自动化示例:

  # 方案 1: 使用持久化配置目录（推荐）
  # 首次运行需要手动完成 Cloudflare 验证
  python simulate_blocksec.py --user-data-dir ~/.blocksec_profile
  
  # 之后可以 headless 运行
  python simulate_blocksec.py --user-data-dir ~/.blocksec_profile --headless

  # 方案 2: 连接到已打开的 Chrome（需要先启动带调试端口的 Chrome）
  # 启动 Chrome:
  #   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
  #     --remote-debugging-port=9222 \\
  #     --user-data-dir=/tmp/chrome-debug
  # 然后运行:
  python simulate_blocksec.py --cdp http://127.0.0.1:9222

  # 方案 3: 使用 API（见 blocksec_api.py）
  python blocksec_api.py --extract-cookies
  python blocksec_api.py --cookie-file blocksec_cookies.json
        """
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="BlockSec tx URL")
    parser.add_argument("--payload", help="Simulation JSON payload string")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument(
        "--channel",
        help="Browser channel to use (e.g. 'chrome', 'msedge') when bundled Chromium fails.",
    )
    parser.add_argument("--debug", action="store_true", help="Dump visible form fields")
    parser.add_argument(
        "--user-data-dir",
        default=str(Path.home() / ".blocksec_browser_profile"),
        help="Use a persistent browser profile directory (default: ~/.blocksec_browser_profile)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Allow manual Cloudflare verification without pausing for input",
    )
    parser.add_argument(
        "--cdp",
        help="Connect to an existing Chrome via CDP, e.g. http://127.0.0.1:9222",
    )
    parser.add_argument(
        "--no-stealth",
        action="store_true",
        help="Disable stealth mode (anti-detection)",
    )
    parser.add_argument(
        "--no-wait-cloudflare",
        action="store_true",
        help="Don't wait for Cloudflare verification",
    )
    args = parser.parse_args()

    # 检查 stealth 插件
    if not HAS_STEALTH and not args.no_stealth:
        print("提示: 安装 playwright-stealth 可以提高成功率:")
        print("  pip install playwright-stealth")
        print()

    payload = _coerce_payload(args.payload)
    
    try:
        result_url = asyncio.run(
            run_simulation(
                args.url,
                payload,
                args.headless,
                args.channel,
                args.debug,
                args.user_data_dir,
                args.manual,
                args.cdp,
                stealth=not args.no_stealth,
                wait_cloudflare=not args.no_wait_cloudflare,
            )
        )
        print(result_url)
    except Exception as e:
        print(f"错误: {e}")
        print("\n如果遇到 Cloudflare 验证问题，请尝试:")
        print("1. 先不使用 --headless 运行一次，手动完成验证")
        print("2. 使用 --user-data-dir 保存验证状态")
        print("3. 或者使用 blocksec_api.py 的 API 方案")
        raise


if __name__ == "__main__":
    main()

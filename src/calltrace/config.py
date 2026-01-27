"""
配置管理模块
"""
import os
from pathlib import Path
from typing import List


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'").strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


class Config:
    """应用配置"""
    
    # Flask配置
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    PORT: int = int(os.getenv('PORT', 5001))
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # Router地址配置
    ROUTER_ADDRESSES: List[str] = [
        '0x00000000009e50a7ddb7a7b0e2ee6604fd120e49',  # 0e49 as Router
        '0xe6f5c83b9d2005bf14333d7e48d3002fff4c93a7',
    ]
    
    # 常见Token地址
    WETH: str = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    USDC: str = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    
    # Transfer selector
    TRANSFER_SELECTOR: str = '0xa9059cbb'
    
    # BlockSec配置
    BLOCKSEC_BASE_URL: str = 'https://blocksec.com'
    
    # 数据提取配置
    MAX_BATCH_SIZE: int = 10  # 批量分析最大数量
    REQUEST_TIMEOUT: int = 30000  # 请求超时（毫秒）

    # EigenPhi 配置
    EIGENPHI_BASE_URL: str = os.getenv(
        "EIGENPHI_BASE_URL",
        "https://storage.googleapis.com/eigenphi-ethereum-tx/{tx_hash}",
    )

    # Dune 配置
    DUNE_TX_QUERY_ID: int = int(os.getenv("DUNE_TX_QUERY_ID", "6569281"))

    # RPC 配置
    ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "").strip()

    # MCP (Model Context Protocol) 配置
    MCP_EIGENPHI_SERVER: str = os.getenv(
        "MCP_EIGENPHI_SERVER",
        "/Users/kezheng/Codes/CursorDeveloper/MEVAL/eigenphi-backend-go/bin/mcp-server",
    ).strip()
    MCP_TIMEOUT_SECONDS: int = int(os.getenv("MCP_TIMEOUT_SECONDS", "120"))


# 创建全局配置实例
config = Config()

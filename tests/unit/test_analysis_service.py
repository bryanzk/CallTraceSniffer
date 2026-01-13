import asyncio
from calltrace.services import analysis_service
from calltrace.services.analysis_service import AnalysisService, ServiceResult


class MockExtractor:
    """Mock BlockSecExtractor for testing"""
    def __init__(self, result):
        self._result = result

    async def extract_blocksec_data(self, tx_hash):
        return dict(self._result)

    async def extract_blocksec_simulation_data(self, sim_url):
        return dict(self._result)

    @staticmethod
    def parse_simulation_url(sim_url: str):
        """Mock parse_simulation_url that validates URL format"""
        if not sim_url or "blocksec.com" not in sim_url:
            raise ValueError("无效的BlockSec URL")
        if "/explorer/tx/eth/" not in sim_url:
            raise ValueError("URL中未找到交易哈希")
        # Extract tx_hash from URL
        parts = sim_url.split("/explorer/tx/eth/")
        if len(parts) < 2:
            raise ValueError("URL中未找到交易哈希")
        tx_hash = parts[1].split("/")[0].split("?")[0]
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            raise ValueError("URL中未找到交易哈希")
        return tx_hash, sim_url


def test_analyze_tx_success_caches_and_builds_mermaid(monkeypatch):
    cache = {}
    tx_hash = "0x" + "a" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra, router_config=None):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    def fake_mermaid(ir_v1):
        return "graph TD"

    def extractor_factory():
        return MockExtractor(result)

    # Mock analysis_service 模块中导入的 process_tx_data
    import calltrace.services.analysis_service as analysis_service_module
    monkeypatch.setattr(analysis_service_module, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(
        cache,
        extractor_factory=extractor_factory,
        mermaid_builder=fake_mermaid,
    )

    service_result = service.analyze_tx(tx_hash)

    assert isinstance(service_result, ServiceResult)
    assert service_result.error is None
    assert service_result.status_code == 200
    assert service_result.payload["analysis"]["ir_v1_json"] == "{}"
    assert service_result.payload["mermaid_dag"] == "graph TD"
    assert tx_hash in cache


def test_analyze_tx_failure_returns_error():
    cache = {}
    tx_hash = "0x" + "b" * 64
    result = {"success": False, "error": "无法提取交易数据"}

    def extractor_factory():
        return MockExtractor(result)

    service = AnalysisService(cache, extractor_factory=extractor_factory)

    service_result = service.analyze_tx(tx_hash)

    assert service_result.payload is None
    assert service_result.error == "无法提取交易数据"
    assert service_result.status_code == 500


def test_analyze_tx_missing_trace_data_returns_error():
    cache = {}
    tx_hash = "0x" + "c" * 64
    result = {"success": True}  # 缺少 trace_data

    def extractor_factory():
        return MockExtractor(result)

    service = AnalysisService(cache, extractor_factory=extractor_factory)

    service_result = service.analyze_tx(tx_hash)

    assert service_result.payload is None
    assert service_result.error == "未找到trace数据"
    assert service_result.status_code == 500


def test_analyze_simulation_invalid_url_returns_400():
    cache = {}
    service = AnalysisService(cache, extractor_factory=lambda: MockExtractor({}))

    service_result = service.analyze_simulation("not-a-url")

    assert service_result.payload is None
    assert service_result.error
    assert service_result.status_code == 400


def test_analyze_simulation_success(monkeypatch):
    cache = {}
    sim_url = "https://app.blocksec.com/explorer/tx/eth/0x" + "d" * 64 + "?event=simulation"
    tx_hash = "0x" + "d" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra, router_config=None):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    def fake_mermaid(ir_v1):
        return "graph TD"

    def extractor_factory():
        return MockExtractor(result)

    # Mock analysis_service 模块中导入的 process_tx_data
    import calltrace.services.analysis_service as analysis_service_module
    monkeypatch.setattr(analysis_service_module, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(
        cache,
        extractor_factory=extractor_factory,
        mermaid_builder=fake_mermaid,
    )

    service_result = service.analyze_simulation(sim_url)

    assert isinstance(service_result, ServiceResult)
    assert service_result.error is None
    assert service_result.status_code == 200
    assert service_result.payload["tx_hash"] == tx_hash
    assert service_result.payload["analysis"]["ir_v1_json"] == "{}"
    assert tx_hash in cache


def test_analyze_simulation_failure_returns_error():
    cache = {}
    sim_url = "https://app.blocksec.com/explorer/tx/eth/0x" + "e" * 64 + "?event=simulation"
    result = {"success": False, "error": "无法提取模拟交易数据"}

    def extractor_factory():
        return MockExtractor(result)

    service = AnalysisService(cache, extractor_factory=extractor_factory)

    service_result = service.analyze_simulation(sim_url)

    assert service_result.payload is None
    assert service_result.error == "无法提取模拟交易数据"
    assert service_result.status_code == 500


def test_analyze_tx_process_tx_data_returns_none_returns_error(monkeypatch):
    """process_tx_data 返回 None 时返回错误"""
    cache = {}
    tx_hash = "0x" + "f" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra, router_config=None):
        return None  # 返回 None 模拟处理失败

    def extractor_factory():
        return MockExtractor(result)

    # Mock analysis_service 模块中导入的 process_tx_data
    import calltrace.services.analysis_service as analysis_service_module
    monkeypatch.setattr(analysis_service_module, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(cache, extractor_factory=extractor_factory)

    service_result = service.analyze_tx(tx_hash)

    assert service_result.payload is None
    assert service_result.error == "数据处理失败"
    assert service_result.status_code == 500


def test_analyze_tx_mermaid_builder_exception_handled_gracefully(monkeypatch):
    """mermaid_builder 抛出异常时优雅处理"""
    cache = {}
    tx_hash = "0x" + "g" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra, router_config=None):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    def failing_mermaid(ir_v1):
        raise Exception("Mermaid generation failed")

    def extractor_factory():
        return MockExtractor(result)

    # Mock analysis_service 模块中导入的 process_tx_data
    import calltrace.services.analysis_service as analysis_service_module
    monkeypatch.setattr(analysis_service_module, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(
        cache,
        extractor_factory=extractor_factory,
        mermaid_builder=failing_mermaid,
    )

    service_result = service.analyze_tx(tx_hash)

    # 应该成功，但 mermaid_dag 为 None
    assert service_result.error is None
    assert service_result.status_code == 200
    assert service_result.payload["mermaid_dag"] is None
    assert service_result.payload["analysis"] is not None


def test_service_result_ok_property():
    """测试 ServiceResult.ok 属性"""
    # 成功情况
    result = ServiceResult(payload={"data": "test"}, error=None, status_code=200)
    assert result.ok is True

    # 失败情况
    result = ServiceResult(payload=None, error="Error", status_code=500)
    assert result.ok is False

    # 空字符串错误也算失败
    result = ServiceResult(payload=None, error="", status_code=400)
    assert result.ok is False


def test_analyze_tx_empty_trace_data_handled(monkeypatch):
    """空 trace_data 的处理"""
    cache = {}
    tx_hash = "0x" + "h" * 64
    result = {"success": True, "trace_data": None}  # trace_data 为 None

    def extractor_factory():
        return MockExtractor(result)

    service = AnalysisService(cache, extractor_factory=extractor_factory)

    service_result = service.analyze_tx(tx_hash)

    assert service_result.payload is None
    assert service_result.error == "未找到trace数据"
    assert service_result.status_code == 500


def test_analyze_simulation_empty_url_returns_400():
    """空 URL 返回 400"""
    cache = {}
    service = AnalysisService(cache, extractor_factory=lambda: MockExtractor({}))

    service_result = service.analyze_simulation("")

    assert service_result.payload is None
    assert service_result.status_code == 400
    # MockExtractor 可能返回不同的错误消息，只要返回400即可
    assert service_result.error is not None


def test_cache_persistence_across_calls(monkeypatch):
    """验证缓存在不同调用间持久化"""
    cache = {}
    tx_hash = "0x" + "i" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra, router_config=None):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    def fake_mermaid(ir_v1):
        return "graph TD"

    def extractor_factory():
        return MockExtractor(result)

    # Mock analysis_service 模块中导入的 process_tx_data
    import calltrace.services.analysis_service as analysis_service_module
    monkeypatch.setattr(analysis_service_module, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(
        cache,
        extractor_factory=extractor_factory,
        mermaid_builder=fake_mermaid,
    )

    # 第一次调用
    service_result1 = service.analyze_tx(tx_hash)
    assert service_result1.error is None
    assert tx_hash in cache

    # 第二次调用应该使用缓存（虽然这里extractor仍会被调用，但cache应该被更新）
    service_result2 = service.analyze_tx(tx_hash)
    assert service_result2.error is None
    assert tx_hash in cache
    assert "trace_data" in cache[tx_hash]
    assert "analysis" in cache[tx_hash]

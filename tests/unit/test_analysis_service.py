from calltrace.services import analysis_service
from calltrace.services.analysis_service import AnalysisService, ServiceResult


class FakeExtractor:
    def __init__(self, result):
        self._result = result

    async def extract_blocksec_data(self, tx_hash):
        return dict(self._result)

    async def extract_blocksec_simulation_data(self, sim_url):
        return dict(self._result)


def test_analyze_tx_success_caches_and_builds_mermaid(monkeypatch):
    cache = {}
    tx_hash = "0x" + "a" * 64
    result = {"success": True, "trace_data": {"dataMap": {}, "mainTrace": {}}}

    def fake_process_tx_data(trace_data, tx_hash_arg, extra):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    def fake_mermaid(ir_v1):
        return "graph TD"

    monkeypatch.setattr(analysis_service, "process_tx_data", fake_process_tx_data)
    service = AnalysisService(
        cache,
        extractor_factory=lambda: FakeExtractor(result),
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
    service = AnalysisService(cache, extractor_factory=lambda: FakeExtractor(result))

    service_result = service.analyze_tx(tx_hash)

    assert service_result.payload is None
    assert service_result.error == "无法提取交易数据"
    assert service_result.status_code == 500


def test_analyze_simulation_invalid_url_returns_400():
    cache = {}
    service = AnalysisService(cache, extractor_factory=lambda: FakeExtractor({}))

    service_result = service.analyze_simulation("not-a-url")

    assert service_result.payload is None
    assert service_result.error
    assert service_result.status_code == 400

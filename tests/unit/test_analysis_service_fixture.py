import json

from calltrace.services import analysis_service
from calltrace.services.analysis_service import AnalysisService


class FailingExtractor:
    async def extract_blocksec_data(self, tx_hash):
        raise AssertionError("extractor should not be called when USE_FIXTURE is enabled")

    async def extract_blocksec_simulation_data(self, sim_url):
        raise AssertionError("extractor should not be called when USE_FIXTURE is enabled")


def test_use_fixture_env_overrides_extractor(monkeypatch, tmp_path):
    fixture_payload = {"dataMap": {}, "mainTrace": []}
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture_payload), encoding="utf-8")

    monkeypatch.setenv("USE_FIXTURE", "true")
    monkeypatch.setenv("FIXTURE_PATH", str(fixture_path))

    def fake_process_tx_data(trace_data, tx_hash, extra, router_config=None):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    monkeypatch.setattr(analysis_service, "process_tx_data", fake_process_tx_data)

    service = AnalysisService({}, extractor_factory=FailingExtractor)
    result = service.analyze_tx("0x" + "a" * 64)

    assert result.ok
    assert result.payload["analysis"]["ir_v1_json"] == "{}"

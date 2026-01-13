from flask import Flask

from calltrace.api import routes
from calltrace.services.analysis_service import ServiceResult


def test_response_from_service_result_success():
    app = Flask(__name__)
    result = ServiceResult(
        payload={
            "tx_hash": "0x" + "a" * 64,
            "analysis": {"ir_v1": {}, "ir_v1_json": "{}", "stats": {}},
            "mermaid_dag": "graph TD",
        },
        error=None,
        status_code=200,
    )
    with app.app_context():
        response = routes._response_from_service_result(result)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["tx_hash"] == result.payload["tx_hash"]
    assert payload["mermaid_dag"] == "graph TD"


def test_response_from_service_result_error():
    app = Flask(__name__)
    result = ServiceResult(payload=None, error="boom", status_code=500)
    with app.app_context():
        response = routes._response_from_service_result(result)
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error"] == "boom"

from calltrace.api import validators


class DummyRequest:
    def __init__(self, payload):
        self._payload = payload

    def get_json(self, silent=False):
        return self._payload


def test_parse_json_object_accepts_none():
    data, error = validators.parse_json_object(DummyRequest(None))
    assert data == {}
    assert error is None


def test_parse_json_object_rejects_non_object():
    data, error = validators.parse_json_object(DummyRequest([]))
    assert data is None
    assert error == "请求体必须为JSON对象"


def test_validate_tx_hash_rejects_empty():
    tx_hash, error = validators.validate_tx_hash({})
    assert tx_hash is None
    assert error == "交易哈希不能为空"


def test_validate_tx_hash_rejects_invalid():
    tx_hash, error = validators.validate_tx_hash({"tx_hash": "0x123"})
    assert tx_hash is None
    assert error == "无效的交易哈希格式"


def test_validate_tx_hash_accepts_valid():
    value = "0x" + "a" * 64
    tx_hash, error = validators.validate_tx_hash({"tx_hash": value})
    assert tx_hash == value
    assert error is None


def test_validate_simulation_url_rejects_empty():
    sim_url, error = validators.validate_simulation_url({})
    assert sim_url is None
    assert error == "模拟URL不能为空"


def test_validate_simulation_url_accepts_value():
    value = "https://app.blocksec.com/explorer/tx/eth/0x" + "b" * 64
    sim_url, error = validators.validate_simulation_url({"simulation_url": value})
    assert sim_url == value
    assert error is None

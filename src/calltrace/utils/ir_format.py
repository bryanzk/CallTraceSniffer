"""
IR output formatting (stable ordering at the output layer only).
"""
import json
from collections import OrderedDict


TOP_LEVEL_ORDER = ['pattern', 'baseTokenAmountIn', 'baseTokenAmountOut', 'rootTrace', 'children']
ROOT_TRACE_ORDER = ['type', 'swap', 'transfer', 'wethWrapOrUnwarp', 'callback', 'encoded']
SWAP_ORDER = ['swapIntent', 'executionArgs']
SWAP_INTENT_ORDER = [
    'poolId',
    'protocolId',
    'tokenIn',
    'tokenInDecimals',
    'tokenOut',
    'tokenOutDecimals',
    'amountIn',
    'amountInBig',
    'amountInEncoded',
    'amountOut',
    'amountOutBig',
    'amountOutEncoded',
]
EXEC_ARGS_ORDER = [
    'amount',
    'isAmountIn',
    'zeroForOne',
    'recipientIsBot',
    'recipient',
    'recipientType',
    'tokenInIsWETH',
    'tokenOutIsWETH',
]
TRANSFER_ORDER = ['tokenId', 'to', 'amount']


def _ordered_by_keys(data, key_order):
    ordered = OrderedDict()
    for key in key_order:
        if key in data:
            ordered[key] = data[key]
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def _order_ir_value(value):
    if isinstance(value, dict):
        return _order_ir_dict(value)
    if isinstance(value, list):
        return [_order_ir_value(item) for item in value]
    return value


def _order_ir_dict(data):
    processed = OrderedDict((key, _order_ir_value(value)) for key, value in data.items())

    if 'rootTrace' in processed and 'children' in processed:
        return _ordered_by_keys(processed, (['tx_hash'] if 'tx_hash' in processed else []) + TOP_LEVEL_ORDER)

    if 'swapIntent' in processed or 'executionArgs' in processed:
        ordered = _ordered_by_keys(processed, SWAP_ORDER)
        if 'swapIntent' in ordered and isinstance(ordered.get('swapIntent'), dict):
            ordered['swapIntent'] = _ordered_by_keys(ordered['swapIntent'], SWAP_INTENT_ORDER)
        if 'executionArgs' in ordered and isinstance(ordered.get('executionArgs'), dict):
            ordered['executionArgs'] = _ordered_by_keys(ordered['executionArgs'], EXEC_ARGS_ORDER)
        return ordered

    if 'poolId' in processed and 'protocolId' in processed and ('tokenIn' in processed or 'tokenOut' in processed):
        return _ordered_by_keys(processed, SWAP_INTENT_ORDER)

    if 'type' in processed and ('swap' in processed or 'transfer' in processed):
        return _ordered_by_keys(processed, ROOT_TRACE_ORDER)

    if set(TRANSFER_ORDER).issubset(processed.keys()):
        return _ordered_by_keys(processed, TRANSFER_ORDER)

    if 'tx_hash' in processed:
        return _ordered_by_keys(processed, ['tx_hash'])

    return processed


def order_ir_payload(payload, tx_hash=None):
    if isinstance(payload, dict):
        payload_data = payload
        if payload.get('tx_hash') is None and tx_hash:
            payload_data = dict(payload)
            payload_data['tx_hash'] = tx_hash
        return _order_ir_dict(payload_data)
    if isinstance(payload, list):
        return [order_ir_payload(item, tx_hash) if isinstance(item, dict) else item for item in payload]
    return payload


def serialize_ir_payload(payload, tx_hash=None):
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return payload
    ordered = order_ir_payload(payload, tx_hash)
    return json.dumps(ordered, ensure_ascii=True, indent=2)

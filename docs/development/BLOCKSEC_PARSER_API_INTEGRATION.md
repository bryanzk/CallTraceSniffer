# blocksec-parser 第三方接入文档

> 当前 CallTraceSniffer 通过 `BLOCKSEC_PARSER_API_BASE_URL` 调用 blocksec-parser HTTP API。

## 1. 接口信息
- Base URL: `http://<host>:4444`
- 健康检查: `GET /healthz`
- 交易解析: `POST /v1/parse/tx`
- Content-Type: `application/json`

## 2. 请求协议

```json
{
  "tx_hash": "0x<64位hex>",
  "strategy": "api"
}
```

- `tx_hash`: 必填，长度 66（含 `0x`）
- `strategy`: 可选，建议固定 `api`

## 3. 响应协议（固定 7 字段）

```json
{
  "success": true,
  "tx_hash": "0x...",
  "strategy_used": "api",
  "raw": {},
  "clean": {},
  "error": null,
  "meta": {
    "duration_ms": 1234,
    "retries": 0,
    "timestamp": 1772121467
  }
}
```

## 4. 状态码与错误处理
- `200`: 请求已处理，业务结果看 `success`
- `422`: 请求参数不合法（如 tx_hash 格式错误）
- `400/502/504`: 服务级错误（参数语义、上游失败、超时）

## 5. 调用方重试策略（建议）
- 仅对网络超时、`502`、`504` 重试
- 指数退避：`1s -> 2s -> 4s`，最多 3 次
- `422`、`400` 不重试（直接修正参数）

## 6. 超时与幂等
- 客户端超时建议：`30~60s`
- 幂等键建议：按 `tx_hash` 去重（同一 hash 结果可缓存）

## 7. 监控字段（建议上报）
- `http_status`
- `success`
- `error`（脱敏后）
- `meta.duration_ms`
- `meta.timestamp`
- `tx_hash`（可部分掩码）

## 8. cURL 示例

```bash
curl -X POST "http://<host>:4444/v1/parse/tx" \
  -H "Content-Type: application/json" \
  -d '{"tx_hash":"0xb4cce87a050dd757a1cb382a51798bdc20edf617e111ac6f607ad5ffa8220946","strategy":"api"}'
```

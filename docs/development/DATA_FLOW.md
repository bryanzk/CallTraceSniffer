# 数据流转文档 - V1

本项目已切换为 IR V1 生成流程，不再使用旧版 ExecutionTree/Swaps/Transfers 的处理链路。

## 流程概览

1. **数据提取**  
   `BlockSecExtractor` 从 BlockSec 页面抓取 `trace_data`。

2. **IR V1 生成**  
   `build_blocksec_ir()` 将 `trace_data` 映射为 IR V1 结构，并通过统一序列化输出 JSON。

3. **API 输出**  
   `/api/analyze`、`/api/analyze-batch`、`/api/analyze-simulation`、`/api/ir_parse` 返回 IR V1 JSON。

## 参考文档

- V1 流程与规则：`docs/development/IR_V1_FLOW.md`
- IR 规范：`docs/development/IR_SPEC.md`

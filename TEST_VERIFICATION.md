# 测试验证记录

## 2026-01-26
- 变更范围：MEV 区块 Tab 与 MCP 生成图谱
- 执行结果：已执行
- 命令：`python3 test_runner.py tests/unit/test_mev_block_service.py`
- 结果：通过（2 passed）
- 命令：`python3 test_runner.py`
- 结果：通过（174 passed，复跑确认 x2）

## 2026-01-20
- 变更范围：新增 tx metrics 服务与批量 API
- 执行结果：已执行
- 命令：`python3 test_runner.py tests/unit/test_tx_metrics_service.py`
- 结果：通过（2 passed）

## 2026-01-20
- 变更范围：冒烟测试（含 tx metrics）
- 执行结果：已执行
- 命令：`python3 test_runner.py -m smoke`
- 结果：通过（5 passed）

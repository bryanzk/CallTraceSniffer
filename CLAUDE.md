# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CallTraceSniffer is a web application for analyzing Ethereum transactions. It extracts call trace data from BlockSec pages and generates IR (Intermediate Representation) V1 JSON output for transaction analysis. The application supports single transaction analysis, batch processing, and BlockSec simulation analysis.

## Common Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run development server (http://localhost:5001)
python run.py
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_analysis_service.py

# Run specific test function
pytest tests/unit/test_analysis_service.py::test_analyze_tx_success_caches_and_builds_mermaid

# Run by marker
pytest -m unit        # unit tests
pytest -m integration # integration tests
pytest -m smoke       # smoke tests

# Run with coverage
pytest --cov=calltrace --cov-report=html
```

### Docker

```bash
# Quick start
./scripts/deploy/build_and_run.sh

# Manual build and run
docker build -t blocksec-analyzer:latest .
docker-compose up -d
```

## Architecture

The project uses a layered architecture located in `src/calltrace/`:

```
API Layer (api/)
    ↓
Service Layer (services/)
    ↓
Utils Layer (utils/)
```

### Key Components

**API Layer** (`api/routes.py`, `api/validators.py`):
- Flask routes for transaction analysis endpoints
- Request validation and response formatting
- Main endpoints: `/api/analyze`, `/api/analyze-simulation`, `/api/simulate-and-analyze`, `/api/analyze-batch`, `/api/ir_parse`, `/api/ir-to-mermaid`

**Service Layer**:
- `analysis_service.py`: Core `AnalysisService` class with dependency injection (extractor factory, mermaid builder, router config, fixture loader)
- `extractor.py`: `BlockSecExtractor` for scraping trace data from BlockSec pages using Playwright
- `ir_v1_blocksec.py`: BlockSec trace data to IR V1 mapping with protocol detection (V2/V3/V4)
- `mermaid_dag.py`: Generates Mermaid diagrams from IR data
- `blocksec_simulation.py`: BlockSec simulation API integration

**Utils Layer**:
- `analysis_utils.py`: Pure functions for IR processing (`count_ir_nodes`, `extract_total_gas`, `extract_transfer_edges`, `compute_flow_counts`, `process_tx_data`)
- `address.py`: Address formatting utilities
- `ir_format.py`: IR serialization and ordering

### Data Flow

1. `BlockSecExtractor` scrapes trace_data from BlockSec pages
2. `build_blocksec_ir()` converts trace_data to IR V1 structure
3. API endpoints return IR V1 JSON with optional Mermaid DAG

### IR V1 Structure

The IR V1 output schema (defined in `docs/development/IR_SPEC.md`):
- `tx_hash`: Transaction hash
- `rootTrace`: Tree of `ExecutionNode` (swap/transfer/unknown types)
- `baseTokenAmountIn/Out`: Optional token amounts

Protocol detection priority: V4 > V3 > V2 (via log topics)

### Testing Patterns

- Tests use fixtures from `tests/fixtures/` (JSON trace data, HAR files)
- `conftest.py` provides shared pytest fixtures
- Use `USE_FIXTURE=1` environment variable to use fixture data instead of live scraping
- `FIXTURE_PATH` environment variable specifies custom fixture file path

### Configuration

`config.py` contains:
- `ROUTER_ADDRESSES`: Known router contract addresses
- `WETH`, `USDC`: Common token addresses
- `BLOCKSEC_BASE_URL`: BlockSec API base URL
- `MAX_BATCH_SIZE`: Maximum transactions per batch (10)

## Token Optimization

- 大文件（>200行）先用 `grep -n` 定位目标函数，再用 `Read` 的 `offset`/`limit` 参数分段读取
- 代码审查拆分到多个会话，每次只处理 1-2 个文件
- 避免重复读取相同文件，优先使用缓存的上下文

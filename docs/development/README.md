# 开发文档

## 📚 文档索引

- [Web界面使用说明](README_WEB.md) - Web应用使用说明
- [数据流转文档](DATA_FLOW.md) - 数据在各模块间的流转过程（包含数据流图）
- [IR规范文档](IR_SPEC.md) - IR结构与字段规范（中英对照）
- [IR V1 解析流程](IR_V1_FLOW.md) - BlockSec→IR V1 标准流程（中英对照）
- [测试文档](../tests/README.md) - 单元测试和集成测试指南

## 开发指南

### Web界面开发
- [Web界面使用说明](README_WEB.md) - Web应用使用说明

### 数据流转
- [数据流转文档](DATA_FLOW.md) - 详细说明数据从BlockSec API到最终输出的完整流转过程

### IR规范
- [IR规范文档](IR_SPEC.md) - IR结构与字段规范（中英对照）

### 测试
- [测试文档](../tests/README.md) - 单元测试和集成测试指南

## 项目结构

项目采用模块化设计，主要代码位于 `src/calltrace/` 目录：

```
src/calltrace/
├── app.py              # Flask应用主文件
├── config.py           # 配置管理
├── services/           # 业务逻辑层
│   ├── ir_v1_blocksec.py  # IR V1 解析服务
│   └── extractor.py       # 数据提取服务
├── utils/              # 工具函数
│   └── address.py      # 地址处理
└── api/                # API路由
    └── routes.py       # 路由定义
```

## 开发环境设置

1. 克隆仓库
2. 创建虚拟环境：`python3 -m venv venv`
3. 激活虚拟环境：`source venv/bin/activate`
4. 安装依赖：`pip install -r requirements.txt`
5. 安装 Playwright：`playwright install chromium`

## 运行开发服务器

```bash
python run.py
```

服务器将在 http://localhost:5001 启动

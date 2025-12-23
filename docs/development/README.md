# 开发文档

## 开发指南

### Web界面开发
- [Web界面使用说明](README_WEB.md) - Web应用使用说明

### IR映射
- [IR映射文档](IR_MAPPING.md) - IR操作映射说明

### 测试
- [测试文档](../tests/README.md) - 单元测试和集成测试指南

## 项目结构

项目采用模块化设计，主要代码位于 `src/calltrace/` 目录：

```
src/calltrace/
├── app.py              # Flask应用主文件
├── config.py           # 配置管理
├── services/           # 业务逻辑层
│   ├── converter.py    # 数据转换服务
│   └── extractor.py    # 数据提取服务
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


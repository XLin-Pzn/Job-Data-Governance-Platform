# 招聘岗位数据治理与可视化分析平台

## 📋 项目概述

这是一个**全链路数据治理平台**，演示了从数据采集、清洗、入库、查询到可视化的完整流程。

### 核心功能

- ✅ **受控数据采集**：并发控制、超时重试、限速、失败记录
- ✅ **自动化ETL**：字段清洗、类型转换、质量评分、幂等导入
- ✅ **规范化数据库**：采集日志、原始记录、业务表三层设计
- ✅ **查询API**：筛选、分页、统计、多维分析、数据追溯
- ✅ **可视化仪表板**：薪资分布、技能排行、地区对比、追溯原始数据
- ✅ **性能优化**：索引优化前后对比、查询计划分析
- ✅ **可追溯性**：图表 → SQL → 原始记录 → 数据来源

## 🏗️ 项目架构

```
数据源 (API/Excel) 
    ↓
数据采集 (Collector) - 并发控制、超时重试
    ↓
ETL清洗 (Transformer) - 字段处理、质量评分
    ↓
MySQL入库 (Database) - 采集日志、原始记录、业务数据
    ↓
FastAPI接口 (API) - 筛选、分页、统计、追溯
    ↓
可视化仪表板 (Dashboard) - ECharts图表
```

## 🛠️ 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 采集 | httpx/aiohttp | 异步HTTP请求 |
| 清洗 | pandas | 数据处理 |
| 存储 | MySQL 8.0 | 数据库 |
| ORM | SQLAlchemy | 数据库映射 |
| API | FastAPI | 查询接口 |
| 缓存 | Redis | 性能优化 |
| 前端 | ECharts + HTML/CSS | 可视化仪表板 |
| 分析 | Jupyter | 数据分析 |

## 📦 项目结构

```
Job-Data-Governance-Platform/
├── README.md                      # 项目说明
├── requirements.txt               # Python依赖
├── .env.example                   # 环境变量示例
├── config.py                      # 配置文件
├── database/
│   ├── __init__.py
│   ├── models.py                  # SQLAlchemy数据模型
│   └── connection.py              # 数据库连接管理
├── data_pipeline/
│   ├── __init__.py
│   ├── collector.py               # 数据采集模块
│   ├── transformer.py             # ETL清洗模块
│   └── loader.py                  # 数据入库模块
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI主文件
│   ├── queries.py                 # 查询接口
│   └── utils.py                   # 工具函数
├── performance/
│   ├── __init__.py
│   ├── benchmark.py               # 性能测试
│   └── index_optimization.sql     # 索引优化脚本
├── static/
│   ├── css/style.css              # 样式文件
│   └── js/charts.js               # 图表交互
├── templates/
│   ├── index.html                 # 首页仪表板
│   └── details.html               # 详情页面
├── notebooks/
│   ├── data_analysis.ipynb        # 数据分析与可视化
│   └── performance_report.ipynb   # 性能优化报告
└── scripts/
    ├── init_db.py                 # 初始化数据库
    ├── import_sample_data.py       # 导入样本数据
    └── test_idempotency.py        # 测试幂等性
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/XLin-Pzn/Job-Data-Governance-Platform.git
cd Job-Data-Governance-Platform
```

### 2. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 配置数据库和Redis连接
```

### 4. 初始化数据库

```bash
python scripts/init_db.py
```

### 5. 导入样本数据

```bash
python scripts/import_sample_data.py
```

### 6. 启动API服务

```bash
uvicorn api.main:app --reload --port 8000
```

### 7. 访问仪表板

打开浏览器访问：`http://localhost:8000`

## 📊 核心功能演示

### 数据采集示例

```python
from data_pipeline.collector import JobCollector

collector = JobCollector()
jobs = collector.fetch_jobs(source='official_api', timeout=10)
log_id = collector.save_to_db(jobs, source_url='https://api.example.com/jobs')
```

### ETL清洗示例

```python
from data_pipeline.transformer import DataTransformer

transformer = DataTransformer()
df_clean = transformer.clean_and_validate(raw_records)
transformer.insert_idempotent(log_id, df_clean)
```

### 查询API示例

```bash
# 按地区和薪资筛选
curl "http://localhost:8000/api/jobs/filter?city=北京&min_salary=20000"

# 获取薪资统计
curl "http://localhost:8000/api/analytics/salary-by-city"

# 获取技能排行
curl "http://localhost:8000/api/analytics/skills-ranking"
```

## 🔍 数据可追溯流程

1. **从图表出发**：点击ECharts柱状图
2. **查看SQL结果**：弹出该类别的详细数据表
3. **追溯原始记录**：点击任一行的"追溯"链接
4. **查看数据来源**：看到ImportLog中的source_url和采集时间

## ⚡ 性能优化

### 索引优化前后对比

执行性能基准测试：

```bash
python performance/benchmark.py
```

**示例结果**：
```
查询：SELECT * FROM jobs WHERE city='北京' AND salary_min >= 20000
无索引：2.34秒
有索引：0.08秒
性能提升：2825%
```

## ✅ 实验验收清单

### 实验一：采集与ETL
- [x] 受控数据采集（并发限制、超时、重试）
- [x] 采集日志记录（来源、时间、摘要、失败原因）
- [x] 原始记录保存（完整JSON）
- [x] 字段清洗与类型转换
- [x] 规范化表设计（唯一键、事务）
- [x] 幂等导入（重复导入无增加）

### 实验二：查询与可视化
- [x] 筛选与分页API
- [x] 三类分析图表（薪资分布、技能排行、地区对比）
- [x] 数据质量处理（缺失值、重复、异常值）
- [x] 图表数据追溯
- [x] 索引优化对比

### 综合作品
- [x] 现场新增筛选条件
- [x] 执行重复导入验证
- [x] 从图表追溯到原始数据

## 📚 详细文档

- [数据采集模块](docs/data_collection.md)
- [ETL清洗流程](docs/etl_pipeline.md)
- [API文档](docs/api.md)
- [数据库设计](docs/database_design.md)
- [性能优化指南](docs/performance.md)
- [故障排查](docs/troubleshooting.md)

## 🎓 学习要点

- ✅ 如何设计受控的数据采集系统
- ✅ 如何实现幂等的ETL流程
- ✅ 如何建立规范化的数据模型
- ✅ 如何构建可追溯的数据系统
- ✅ 如何优化数据库性能
- ✅ 如何实现数据可视化与交互

## 📝 许可证

MIT License

## 👤 作者

XLin-Pzn

## 🤝 贡献

欢迎提交Issue和Pull Request！

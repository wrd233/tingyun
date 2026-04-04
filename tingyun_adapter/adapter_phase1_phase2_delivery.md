# Adapter 阶段 1-2 交付说明

这份文档说明 Tingyun adapter 在阶段 1 和阶段 2 已经完成了什么、当前可以直接运行什么，以及哪些能力被明确留到了后续阶段。

## 已完成范围

### 阶段 1：项目骨架与 Schema 层

已完成：

- `src/tingyun_adapter/` 项目包结构
- 配置模型与环境变量读取
- 核心上下文模型
- 各类对象引用模型
- 证据与 `PackEnvelope` 模型
- 领域实体与 pack payload 模型
- SDK / CLI 基础入口
- `pyproject.toml` 打包元数据

### 阶段 2：Raw Client 与归一化层

已完成：

- 听云核心 API 家族的原始 HTTP client
  - `webaction`
  - `graph`
  - `trace`
  - `Database`
  - `NoSQL`
  - `connection`
  - `logTrace`
- 关键字段归一化
  - `response / respTime / responseTime -> response_time_ms`
  - `totalResponse / totalResptime / totalResponseTime -> total_response_time_ms`
  - `throught / tps -> throughput`
- trace / component 键解析
- `tyBase64_` 风格 `opName` 解码
- 离线样本仓库 `CapturedApiRepository`
- 单元测试基础集

## 当前目录结构

```text
src/tingyun_adapter/
  clients/
  config/
  domain/
    models/
  invocation/
  normalizers/
  sources/
tests/unit/
```

## 当前可以直接运行的内容

运行单元测试：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

查看 adapter CLI 基础入口：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --captured-api-dir ./captured_api
```

安装为可编辑包：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -e .
tingyun-adapter --captured-api-dir ./captured_api
```

## 当前明确未纳入阶段 1-2 的内容

以下内容被有意推迟到后续阶段：

- 具体 use case builder
- 跨 API 编排
- `report_fact_pack`
- 在线 / 离线模式的用例级切换
- 缓存、持久化与批处理
- 面向 skill 的报告生成逻辑

## 当前质量门槛

阶段 1-2 视为可用，需要满足：

- adapter 包语法检查通过
- `tests/unit/` 单测通过
- CLI 能正常输出基础配置
- `CapturedApiRepository` 能读取真实 `captured_api/` 样本

## 下一步目标

下一阶段是阶段 3，主要是把用例层搭起来：

- `build_system_snapshot`
- `build_action_hotspot_pack`
- `build_trace_case_pack`
- `build_report_fact_pack`

这些 builder 都会直接复用阶段 1-2 完成的 schema、client、normalizer 和样本仓库。

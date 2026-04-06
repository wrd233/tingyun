# Tingyun Adapter Phase 6 Delivery

生成时间：2026-04-06

## 本轮交付范围

本轮围绕“系统层 adapter 缺口补齐”落地了 6 个新 pack：

- `instance_analysis_pack`
- `topology_dependency_pack`
- `external_dependency_pack`
- `slow_sql_pack`
- `sql_fact_sheet`
- `action_dependency_breakdown_pack`

## 新增能力说明

### 1. `instance_analysis_pack`

提供：

- 应用实例清单
- 选定实例的 CPU 图表摘要
- JVM 图表摘要
- 实例数、宿主分布、CPU 最新值/峰值等 summary

主要样本接口：

- `application/instance/select`
- `instance/cpu/chart`
- `instance/jvm/chart`

### 2. `topology_dependency_pack`

提供：

- 业务系统级拓扑摘要
- 当前业务系统明细拓扑摘要
- 节点健康度映射
- 依赖边列表

主要样本接口：

- `graph/queryBizSystenGraph`
- `graph/queryBizDetailGraph`
- `graph/queryGraphHealth`

### 3. `external_dependency_pack`

提供：

- 外部依赖节点清单
- 协议级聚合（`http` / `https` / `jsonrpc`）
- 响应时间 / 吞吐 / 错误率 / 健康度摘要
- 外部依赖与内部节点的连接关系

当前边界：

- 能做到协议级、拓扑级外部依赖分析
- 暂未稳定做到具体 URL / host 级 TopN

### 4. `slow_sql_pack`

提供：

- 业务系统范围内的慢 SQL 候选列表
- SQL 基础特征提取：
  - 语句类型
  - 表名候选
  - join / subquery / order by / group by / limit
- 语句类型聚合

主要样本接口：

- `Database/list`
- `Database/analysis`
- `Database/operate/analysisList`

### 5. `sql_fact_sheet`

提供：

- 单条 SQL 的事实页
- SQL 基础特征
- 关联 action 列表
- 关联 trace 列表
- 下钻 key（含 `opName` 编码）

主要样本接口：

- `Database/analysis`
- `Database/operate/analysisList`
- `component/database/actionList`
- `component/database/actionTraceList`

### 6. `action_dependency_breakdown_pack`

提供：

- 单个 action 的依赖拆解结果
- 组件维度耗时/次数/错误信息
- action 图谱摘要
- component type 聚合

主要样本接口：

- `webaction/performance/breakdown`
- `graph/queryActionGraph`
- `webaction/overview`

## 暂缓项

本轮明确暂缓：

- `impact_signals`
- `business_labels`
- `stability_signals`
- `comparison_signals`
- `page_experience_pack`

## 验证结果

已通过单元测试：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py' -v
```

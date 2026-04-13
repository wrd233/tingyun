# legal_diagnostic_report 章节说明

这份说明服务于后续 agent / renderer，在不引入重型中间输入层的前提下，直接读取同批次 `diagnostics/` 资产生成报告。

## 总规则

- 直接读取 `artifacts/monitored_systems/<system_key>/<batch_key>/diagnostics/`
- `02_master_tables/` 是对象主线
- `03_evidence_indexes/` 用于证据状态、截图计划、URL 与写作提示
- `04_deep_dive/` 只作为补充展开，不替代主表
- 资产缺失时允许占位，但不允许臆测

## 1 概述

### 1.1 巡检对象与时间范围

主要来源：

- 实例级 `report_config.yaml`
- `knowledge/monitored_systems/<system_key>/`

表达方式：

- 表格化展示系统名、统计窗口、主要分析对象

### 1.2 证据来源与分析口径

主要来源：

- `diagnostics/00_raw_exports/`
- `diagnostics/02_master_tables/`
- `diagnostics/03_evidence_indexes/`
- `diagnostics/04_deep_dive/`

表达方式：

- 自然语言说明“导出主线 + 主表 + deep-dive + 人工截图”的证据口径

## 2.1 部署架构与运行环境概况

优先来源：

- `00_raw_exports/` 中的 summary / registry
- capture 样例与系统知识
- 需要时补充 `report_materials/` 中的环境摘要

表达方式：

- `2.1.1`、`2.1.2`、`2.1.3` 优先表格化
- 主机、服务、端口、部署范围使用结构化表格
- 如果 diagnostics 下没有足够资产，应保留模板占位并标明“待人工补充”

## 2.2 系统接口检查

优先来源：

- `02_master_tables/request_master.csv`
- `03_evidence_indexes/request_evidence_index.csv`
- `04_deep_dive/request/`
- `04_deep_dive/interface_cluster/`

表达方式：

- 2.2.1 / 2.2.3 以表格列出对象清单
- 2.2.2 / 2.2.4 以“重点对象小节 + 关键数据 + 判断 + 现状/证据说明”展开
- 如果有截图计划或 direct URL，应在生成阶段插入图占位与 caption
- 如果只有 `url_missing_but_recoverable`，正文保留说明，但图位只输出占位说明

## 2.3 系统SQL检查

优先来源：

- `02_master_tables/sql_master.csv`
- `03_evidence_indexes/sql_evidence_index.csv`
- `04_deep_dive/sql/`
- `00_raw_exports/sql_database/`

表达方式：

- `2.3.1` 先给数据库实例和连接池整体检查摘要
- `2.3.2` 用表格列出重点慢 SQL
- `2.3.3` 用表格列出重点异常 SQL
- SQL 与接口存在明确关联时，可在自然语言里引用 `related_request_ids / related_object_ids`

## 3 结论

优先来源：

- 主表中的 `followup_status / followup_note`
- deep-dive registry 中已经完成的对象

表达方式：

- 结论应收敛为“建议排查与复核”
- 不要在这一章重新展开诊断细节

## 缺失数据时的处理

- 缺接口主表：章节保留，占位说明“request_master.csv 缺失”
- 缺 SQL 主表：章节保留，占位说明“sql_master.csv 缺失”
- 缺 evidence index：不臆造截图与 URL，只输出“待补证据”
- 缺 deep-dive：仍可用主表生成报告，不必阻塞整个第三阶段

# Missing Data Report

## 章节状态

- `chapter_1`: `filled`
  - 概述与证据来源已按当前 diagnostics 摘要填充。
- `chapter_2_1`: `partial`
  - 仅基于 preparation/materialization 摘要填充，主机级部署信息仍占位。
- `chapter_2_2`: `filled`
  - 接口主表、证据索引和 request deep-dive 已接入。
- `chapter_2_3`: `filled`
  - SQL 主表、证据索引和 sql deep-dive 已接入。
- `chapter_3`: `partial`
  - 结论已生成，但仍是测试轮次的收敛摘要。

## 缺失项

- 2.1 缺少主机级部署与端口明细，当前仅能说明 prepared/master 摘要和批次 warning。
- 2.3.3 当前 sql_master 中没有 error_count > 0 的条目，异常 SQL 章节只能占位。
- 2.3.1 连接池详细指标尚未直接注入第三阶段上下文。

## 编译状态

- compiled: `False`
- reason: xelatex not available in current environment

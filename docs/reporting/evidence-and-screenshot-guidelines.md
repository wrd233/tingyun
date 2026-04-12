# Evidence And Screenshot Guidelines

本文件补充说明证据链与截图占位规则；上位设计以 [final-deliverable-and-report-expression.md](/Users/wangrundong/work/mywork/docs/reporting/final-deliverable-and-report-expression.md) 为准。

## 证据组织

- 证据应能回链到原始对象
- URL、trace、SQL、依赖、截图建议应保持可追溯
- 弱证据对象应保留观察项语义，不直接冒充主问题

## 截图语义

- 截图提示是写作辅助，不等于截图本身
- 应说明建议截图什么、突出什么、对应哪个对象或章节
- 如果截图属于某次批次的真实运行产物，应进入该批次目录

## 固定截图模板

建议统一使用以下字段描述截图占位：

- `截图目的`
- `页面 URL`
- `建议截图区域`
- `说明对象`
- `用途说明`

## 推荐落盘

- 证据索引：`report_materials/` 或 `evidence/`
- 截图建议：`report_materials/`
- 实际截图：`artifacts/monitored_systems/<system_key>/<batch_key>/evidence/`

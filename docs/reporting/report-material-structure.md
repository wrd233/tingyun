# Report Material Structure

报告材料不是单个 `report.md`，而是一套可复核、可二次加工的交付件。

## 典型组成

- 对象主表
- 证据索引
- writer input
- export views
- 诊断 markdown
- final report

## 主对象原则

- 表格是主对象
- JSON 是补充证据
- 每类对象应有自己的主表，而不是所有对象挤在一个总表里

## 推荐路径

- `report_materials/`
  - writer input、主表、证据索引、export views
- `reports/`
  - 最终报告正文

# Reporting

`docs/reporting/` 的当前主设计入口是：

- [final-deliverable-and-report-expression.md](/Users/wangrundong/work/mywork/docs/reporting/final-deliverable-and-report-expression.md)
  - 当前最终交付物形态与报告表达主文档

保留的补充说明：

- [report-output-terms.md](/Users/wangrundong/work/mywork/docs/reporting/report-output-terms.md)
- [evidence-and-screenshot-guidelines.md](/Users/wangrundong/work/mywork/docs/reporting/evidence-and-screenshot-guidelines.md)
- [capture-api-report-shortlist.md](/Users/wangrundong/work/mywork/docs/reporting/capture-api-report-shortlist.md)
- [stage3-report-generation-and-template-layout.md](/Users/wangrundong/work/mywork/docs/reporting/stage3-report-generation-and-template-layout.md)

第三阶段当前采用：

- 模板定义集中放在 `report_templates/`
- 报告实例落在 `artifacts/monitored_systems/<system_key>/<batch_key>/reports/`
- 直接读取同批次 `diagnostics/`，不引入新的重型 `report_input_bundle/`

`docs/decisions/` 中的报告相关文档只作为历史经验与阶段记录，不作为当前设计说明。

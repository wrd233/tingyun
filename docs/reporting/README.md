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

当前最小执行入口：

- `python3 report_templates/renderers/render_report_instance.py --config artifacts/monitored_systems/<system_key>/<batch_key>/reports/legal_diagnostic_report/report_config.yaml`

当前 renderer 会先在实例目录的 `generated/` 下生成骨架文件，再由后续 agent 继续补章节内容与最终排版。

它当前还会把构建状态、编译日志和最终 tex/pdf 落到实例目录的 `output/`，并在 diagnostics 缺失时稳定写入占位与 `missing_data_report.md`。

`docs/decisions/` 中的报告相关文档只作为历史经验与阶段记录，不作为当前设计说明。

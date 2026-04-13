# legal_diagnostic_report

`legal_diagnostic_report` 是当前仓库里的首个正式第三阶段报告模板定义，也是当前 stage-3 默认采用的单模板样板。

它基于用户提供的示例模板 [法务系统排查报告_模拟版.tex](</Users/wangrundong/Downloads/法务系统排查报告_模拟版.tex>) 建立，目标是作为“法务/业务系统巡检与排查类 LaTeX 报告”的母版。

## 适用范围

- 面向单个诊断批次的正式巡检/排查报告
- 直接读取同批次 `diagnostics/` 下的主表、证据索引、deep-dive、原始导出摘要等资产
- 允许人工补充截图、图表、备注，但不要求先把 diagnostics 全量复制为新的中间输入包
- 不负责保存某次报告实例的数据或输出结果

当前更适合：

- 以 `request_master.csv`、`sql_master.csv` 和对应 evidence index 为主线生成章节骨架
- 在 diagnostics 已有 deep-dive bundle 时补充对象现状说明
- 输出可人工继续修订的 `.tex/.pdf`

当前不适合：

- 自动补齐 diagnostics 本身缺失的部署/主机/连接池细项
- 在没有证据时自动臆造根因或补写结论
- 同时充当多种报告风格的通用母版

## 目录说明

- `template.tex`
  - 当前主模板入口
- `spec.yaml`
  - 这种报告类型的长期规格定义
- `chapter_guidelines.md`
  - 每章应该读取哪些 diagnostics 资产、如何组织表达
- `style/report_macros.tex`
  - 从示例模板中抽出的通用宏、颜色、字体和标题样式
- `fragments/*.tex`
  - 轻量拆分的页面与章节片段
- `notes.md`
  - 模板继承来源、当前稳定部分与待泛化部分

## 与报告实例的关系

- 这里保存的是“报告类型定义”
- 具体某一次批次的实例目录应落在 `artifacts/monitored_systems/<system_key>/<batch_key>/reports/legal_diagnostic_report/`
- 模板目录本身不保存实例级 diagnostics 副本、截图或生成结果
- 实例目录通过 `report_config.yaml` 指向同批次 sibling `diagnostics/`，而不是复制 diagnostics 资产

## 使用方式

未来 agent 或 renderer 应优先：

1. 读取 `spec.yaml` 理解章节树、所需资产和缺失处理规则。
2. 读取目标批次下的 `reports/legal_diagnostic_report/report_config.yaml`。
3. 直接从同级 `diagnostics/` 读取资产。
4. 生成中间 tex/md/json 到实例目录的 `generated/`。
5. 输出最终 `.tex/.pdf/.docx` 到实例目录的 `output/`。

当前 renderer 还会补充：

- `generated/missing_data_report.md`
- `output/build_status.json`
- `output/build_xelatex*.log`

如果宿主机没有 `xelatex`，renderer 会在不改变 direct-read 结构的前提下，优先尝试 Docker 中的 `texlive/texlive` 完成编译。

当前最小 renderer 入口：

- `python3 report_templates/renderers/render_report_instance.py --config artifacts/monitored_systems/<system_key>/<batch_key>/reports/legal_diagnostic_report/report_config.yaml`

当前这份模板先服务于 `bizsystem_1065 / 2026-04-12-live-export-test-2210` 这个真实批次实例。

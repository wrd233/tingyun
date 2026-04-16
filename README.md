# Tingyun Multi-System Workspace

这个仓库现在按“3 个主工程 + 5 类支撑目录”的目标状态整理，服务于多个待监测系统、同一系统多个监测批次，以及机器 A / 机器 B 协作下的诊断与报告材料生成。

## 顶层结构

- `tingyun_cdp_capture/`
  - 平台行为抓取、接口样本沉淀、关键链路回放工程
- `tingyun_adapter/`
  - 诊断中间层，负责候选对象筛选、证据组织、知识增强、报告素材导出
- `tingyun_adapter_client/`
  - 机器 B 上的远程调用器与本地物化器
- `docs/`
  - 架构、流程、报告语义、关键历史决策
- `skills/`
  - 项目级 skill 定义目录，集中放围绕诊断、主表、deep-dive 和报告生成的可复用工作单元
- `report_templates/`
  - 第三阶段报告模板定义目录，集中放长期稳定的模板规格、渲染脚手架与 LaTeX 母版
- `reference/`
  - 平台手册、模板、长期外部参考资料
- `samples/`
  - 允许入库、供回归和阅读的稳定样例
- `knowledge/`
  - 系统级长期知识，按系统组织
- `artifacts/`
  - 本地运行产物工作区，按系统 / 批次组织，默认不入库

## 三大主工程如何协作

1. `tingyun_cdp_capture/` 负责确认平台真实可用的接口、页面链路和取证入口。
2. `tingyun_adapter/` 把原始平台能力重组为更适合诊断和报告消费的中间对象与导出视图。
3. `tingyun_adapter_client/` 在机器 B 上远程调用 adapter，并把结果物化为本地材料目录。

可以把它理解为：

- capture 保证来源可信
- adapter 保证结构清晰
- client 保证远程可消费、本地可落地

## 多系统 / 多批次路径语义

### 系统级长期知识

放在：

`knowledge/monitored_systems/<system_key>/`

典型内容：

- 系统画像
- 命名映射
- 手工上下文
- review queue

### 批次级运行结果

放在：

`artifacts/monitored_systems/<system_key>/<batch_key>/`

典型内容：

- capture 结果
- pack 导出
- diagnostics
- evidence
- report materials
- final reports

### 入库样例

放在：

`samples/monitored_systems/<system_key>/<sample_batch_key>/`

这里保存的是整理后的稳定样例，而不是完整真实运行目录。

## 样例、知识、运行产物的边界

- `samples/`：可长期保留、可入库、用于说明结构和回归比对
- `knowledge/`：跨批次复用的系统级长期知识
- `artifacts/`：当前或历史批次的本地运行产物，默认忽略
- 主工程目录：只保留代码、最小运行入口、工程自身 README
- `report_templates/`：报告类型定义；具体某次报告实例仍落在对应批次的 `artifacts/.../<batch_key>/reports/`
- `skills/`：项目级 skill 定义；回答“围绕这些目录和资产该怎么做”，不替代 adapter/client/report_templates 本身

## 当前主设计入口

- 项目整体架构与协作：[project-overall-architecture-and-collaboration.md](/Users/wangrundong/work/mywork/docs/architecture/project-overall-architecture-and-collaboration.md)
- Adapter 设计思路与中间产物：[adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md)
- 最终交付物形态与报告表达：[final-deliverable-and-report-expression.md](/Users/wangrundong/work/mywork/docs/reporting/final-deliverable-and-report-expression.md)

补充文档：

- 仓库目标状态：[repo-target-state.md](/Users/wangrundong/work/mywork/docs/architecture/repo-target-state.md)
- 系统 / 批次语义：[system-and-batch-semantics.md](/Users/wangrundong/work/mywork/docs/architecture/system-and-batch-semantics.md)
- 输出术语统一：[report-output-terms.md](/Users/wangrundong/work/mywork/docs/reporting/report-output-terms.md)
- APM 导出到主表流水线：[apm-export-tables-to-master-tables.md](/Users/wangrundong/work/mywork/docs/workflows/apm-export-tables-to-master-tables.md)
- Deep-dive 阶段与主表衔接：[deep-dive-stage-and-adapter-bridge.md](/Users/wangrundong/work/mywork/docs/architecture/deep-dive-stage-and-adapter-bridge.md)
- 第三阶段报告结构：[stage3-report-generation-and-template-layout.md](/Users/wangrundong/work/mywork/docs/reporting/stage3-report-generation-and-template-layout.md)
- Skill 体系入口：[skill-system-and-project-skills.md](/Users/wangrundong/work/mywork/docs/architecture/skill-system-and-project-skills.md)
- Skill 设计与演进：[skill-design-and-evolution-for-tingyun-project.md](/Users/wangrundong/work/mywork/docs/architecture/skill-design-and-evolution-for-tingyun-project.md)

历史设计与阶段文档统一放在 [docs/decisions/](/Users/wangrundong/work/mywork/docs/decisions/)，不作为当前事实来源。

## 最小阅读顺序

1. 先读本文件了解顶层边界。
2. 再读 [project-overall-architecture-and-collaboration.md](/Users/wangrundong/work/mywork/docs/architecture/project-overall-architecture-and-collaboration.md) 看 capture / adapter / client 主链路。
3. 如果要接手 adapter 设计，读 [adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md)。
4. 如果要接手报告交付，读 [final-deliverable-and-report-expression.md](/Users/wangrundong/work/mywork/docs/reporting/final-deliverable-and-report-expression.md)。
5. 如果要接手具体系统，读 `knowledge/monitored_systems/<system_key>/`。
6. 如果要接手某次诊断，读 `artifacts/monitored_systems/<system_key>/<batch_key>/` 或对应 `samples/`。
7. 如果要接手项目级 skill，先读 `skills/` 和 `docs/architecture/skill-system-and-project-skills.md`。
   再读 `docs/architecture/skill-design-and-evolution-for-tingyun-project.md`，理解为什么 skill 这样组织、经验应该沉淀到哪里。
8. 如果要接手第三阶段报告模板，读 `report_templates/` 和 `docs/reporting/stage3-report-generation-and-template-layout.md`。

## 配置文件

本地配置文件默认不入库：

- `tingyun_cdp_capture/config.local.json`
- `tingyun_adapter/config.local.json`
- `tingyun_adapter_client/config.local.json`

初始化可参考各主工程 README。

# Architecture

`docs/architecture/` 中只有以下三类内容应被当作当前事实来源：

- [project-overall-architecture-and-collaboration.md](/Users/wangrundong/work/mywork/docs/architecture/project-overall-architecture-and-collaboration.md)
  - 当前顶层架构与协作主文档
- [adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md)
  - 当前 adapter 主设计文档
- [repo-target-state.md](/Users/wangrundong/work/mywork/docs/architecture/repo-target-state.md)
  - 仓库目标状态与目录语义参考

补充说明文档：

- [adapter-internal-boundaries.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-internal-boundaries.md)
- [deep-dive-stage-and-adapter-bridge.md](/Users/wangrundong/work/mywork/docs/architecture/deep-dive-stage-and-adapter-bridge.md)
- [skill-system-and-project-skills.md](/Users/wangrundong/work/mywork/docs/architecture/skill-system-and-project-skills.md)
- [system-and-batch-semantics.md](/Users/wangrundong/work/mywork/docs/architecture/system-and-batch-semantics.md)
- [directory-responsibilities.md](/Users/wangrundong/work/mywork/docs/architecture/directory-responsibilities.md)

其中 `skill-system-and-project-skills.md` 对应仓库根 `skills/` 目录，用于说明项目级 skill 如何与 adapter / client / report_templates 协作。

已降级或历史设计请查看 `docs/decisions/`，不要把它们当成当前主设计。

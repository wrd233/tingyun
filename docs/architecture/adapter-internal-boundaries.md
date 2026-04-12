# Adapter Internal Boundaries

本文件是 adapter 内部边界补充文档；上位设计以 [adapter-design-and-intermediate-artifacts.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-design-and-intermediate-artifacts.md) 为准。

`tingyun_adapter/src/tingyun_adapter/` 继续按工程能力分层，但解释方式已经统一到“诊断中间层”语义，而不是简单接口镜像。

## 目录职责

- `clients/`
  - 对听云能力的客户端封装
- `config/`
  - 配置与默认项
- `domain/`
  - pack、实体、知识对象等领域模型
- `invocation/`
  - CLI、SDK、export runner 等入口
- `normalizers/`
  - 字段、metric、key、关系归一化
- `service/`
  - HTTP 服务暴露层
- `sources/`
  - 样本仓和知识仓访问
- `usecases/`
  - 面向诊断与导出的业务组织层

## `usecases/` 的职责分组

虽然当前仍以多个 builder 文件存在，但语义上已经分成以下几类：

- candidate 构建
- component 构建
- evidence enhancement
- export materialization support
- report support
- knowledge enhancement

## 输出层次

adapter 相关输出统一按以下层次理解：

1. `pack`
2. `writer input`
3. `export view`
4. `materialized report pack`
5. `sample bundle`
6. `final report`

它们是不同层次的对象，不再混用命名。

# Tingyun Adapter

`tingyun_adapter/` 是整个仓库的诊断中间层与结构中心。它不是简单的平台代理，而是把听云平台能力重组为更适合候选对象筛选、证据组织、知识增强和报告消费的中间能力。

## 在整体链路中的位置

- 上游接 `tingyun_cdp_capture/` 提供的样本与平台理解
- 下游由 `tingyun_adapter_client/` 在机器 B 上远程消费并物化

## 负责什么

- 候选对象筛选
- 对象深挖与证据增强
- 系统级知识读取与增强
- writer input、export view、report support 等输出层

## 不负责什么

- 不退化为简单接口透传层
- 不在源码目录长期保存某系统某批次的真实运行产物
- 不替代 client 做最终本地材料归档

## 主要源码目录

- `src/tingyun_adapter/clients/`
- `src/tingyun_adapter/config/`
- `src/tingyun_adapter/domain/`
- `src/tingyun_adapter/invocation/`
- `src/tingyun_adapter/normalizers/`
- `src/tingyun_adapter/service/`
- `src/tingyun_adapter/sources/`
- `src/tingyun_adapter/usecases/`

`usecases/` 当前主要按以下职责分组理解：

- candidate 构建
- component 构建
- evidence enhancement
- export materialization support
- report support
- knowledge enhancement

## 输入输出边界

输入：

- 听云平台 live 数据
- capture 样本
- 系统级知识目录

输出：

- `pack`
- `writer input`
- `export view`

这些输出由 client 进一步物化为本地材料目录。

## 与多系统 / 多批次的关系

- 系统级长期知识应放在：
  - `knowledge/monitored_systems/<system_key>/`
- 某次批次的本地运行材料应放在：
  - `artifacts/monitored_systems/<system_key>/<batch_key>/`
- adapter 自身不把某个系统或批次固化在源码目录里

## 本地配置

先复制：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json
```

配置示例中的知识目录已对齐到共享知识区：

```json
{
  "captured_api_dir": "../tingyun_cdp_capture/captured_api",
  "knowledge_dir": "../knowledge/monitored_systems"
}
```

## 最小运行入口

安装：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install -e .
```

查看 CLI：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --help
```

启动 HTTP 服务：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api
```

## 关键文档

- [adapter-internal-boundaries.md](/Users/wangrundong/work/mywork/docs/architecture/adapter-internal-boundaries.md)
- [deep-dive-stage-and-adapter-bridge.md](/Users/wangrundong/work/mywork/docs/architecture/deep-dive-stage-and-adapter-bridge.md)
- [report-output-terms.md](/Users/wangrundong/work/mywork/docs/reporting/report-output-terms.md)
- [adapter-service-local-and-public.md](/Users/wangrundong/work/mywork/docs/workflows/adapter-service-local-and-public.md)

# MyWork 工作区

这个仓库现在按项目拆成了 3 个部分：

- `reference/`
  - 存放参考资料与外部文档
- `tingyun_cdp_capture/`
  - 听云平台接口抓取、样本沉淀、链路回放项目
- `tingyun_adapter/`
  - 面向分析与报告场景的 adapter 项目

## 目录说明

### `reference/`

- `基调听云应用与微服务用户使用手册.pdf`

### `tingyun_cdp_capture/`

负责：

- 通过 CDP 抓取听云页面触发的 `/server-api/` 请求
- 归档 `captured_api/` 和 `raw_logs/`
- 用真实 HTTP 请求回放关键诊断链路
- 沉淀接口分析文档和系统骨架文档

### `tingyun_adapter/`

负责：

- 把听云原始接口整理成稳定的对象、关系、证据和 pack
- 为后续 skill / 大模型分析提供更适合消费的结构化输入
- 逐步建设：
  - `system_snapshot`
  - `action_hotspot_pack`
  - `trace_case_pack`
  - `report_fact_pack`
  - `database_component_pack`
  - `nosql_component_pack`
  - `connection_pool_pack`

## 配置文件

两个项目都改成了优先读取本地配置文件：

- `tingyun_cdp_capture/config.local.json`
- `tingyun_adapter/config.local.json`

这两个文件都已经加入 `.gitignore`，不会提交到 git。

可以先复制示例文件：

```bash
cp /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json.example /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json
cp /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json
```

## 建议使用顺序

1. 先在 `tingyun_cdp_capture/` 里抓样本与回放链路
2. 再在 `tingyun_adapter/` 里基于样本或真实调用构建 pack
3. 最后再让上层 skill / 大模型消费这些 pack 做分析与报告

# Tingyun Adapter Client

这个项目运行在机器 B，用来调用机器 A 上已经发布好的 `tingyun_adapter` HTTP 服务。

它的定位很简单：

- 不持有听云 token
- 不直接调用听云原始接口
- 只负责调用机器 A 的 adapter 服务
- 输出机器 A 返回的 pack JSON

这样做的好处是：

- 机器 A 统一管理听云 token、样本目录和 live/sample 能力
- 机器 B 只持有服务地址和 `service_api_key`
- 本机大模型、agent、Codex 都可以通过 CLI 稳定使用这些 pack

现在 client 不只是拿到结构化对象 pack，也能直接拿到：

- 可点击的听云控制台链接
- 截图建议
- 页面能力边界
- 更清晰的证据链关联
- `screenshot_index_pack` 这类面向正式报告取证的索引输出
- `knowledge_context_pack` 这类面向大模型业务记忆复用的上下文输出
- `knowledge_update_proposal_pack` 这类把模型建议沉淀到 `review_queue` 的写入入口
- `build-report-pack` 这类把多个 pack 组装成本地 `report_pack/` 素材目录的导出入口

## 本地配置

机器 B 的配置文件放在：

- [config.local.json](/Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json)

如果本地还没初始化，可以先复制：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json
```

建议填写：

```json
{
  "service_base_url": "https://your-adapter-service.example.com",
  "service_api_key": "机器 A 上配置的 service_api_key",
  "timeout_seconds": 30,
  "default_source_mode": "sample"
}
```

说明：

- `service_base_url`
  - 机器 A 服务地址
  - 本地联调时可以写 `http://127.0.0.1:8000`
  - 公网发布后写 Cloudflare Tunnel 或反向代理域名
- `service_api_key`
  - 机器 A 上服务的访问密钥
- `default_source_mode`
  - 如果 CLI 不显式传 `--source-mode`，默认用这个值

## 安装

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
python3 -m pip install -e .
```

如果不想安装到环境里，也可以直接用模块方式运行：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli
```

## 如何启动

这个项目不是长期运行的服务，不需要驻留进程。

它是一个按次调用的 CLI，机器 B 上需要用的时候直接执行即可。

## 本地测试

### 1. 看配置是否生效

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli
```

### 2. 调机器 A 的健康检查

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli healthz
```

### 3. 查看机器 A 支持的 pack

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli meta
```

### 4. 构建 `system_snapshot`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### 5. 构建 `diagnostic_candidate_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type diagnostic_candidate_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 6. 构建 `action_fact_sheet`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type action_fact_sheet \
  --biz-system-id 1065 \
  --application-id 1644 \
  --action-id 13220 \
  --action-type TX \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 7. 构建 `screenshot_index_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type screenshot_index_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 8. 构建 `knowledge_context_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type knowledge_context_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --limit 5
```

### 9. 构建 `knowledge_update_proposal_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-pack \
  --pack-type knowledge_update_proposal_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --proposal-file ./proposal.example.json \
  --persist-proposals
```

### 10. 构建本地 `report_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter_client
PYTHONPATH=./src python3 -m tingyun_adapter_client.cli build-report-pack \
  --biz-system-id 1065 \
  --start-time '2025-12-20' \
  --end-time '2026-03-31' \
  --source-mode live \
  --limit 6 \
  --output-dir /Users/wangrundong/work/mywork/report_pack
```

这个命令会：

- 先调用远端 `healthz` / `meta`
- 再按时间窗批量拉取 `report_fact_pack`、`screenshot_index_pack`、`page_experience_pack`、`slow_sql_pack` 等核心 packs
- 自动补抓重点 `action_fact_sheet`、`trace_fact_sheet`、`database_component_pack`、`sql_fact_sheet`、`instance_analysis_pack`
- 在本地生成 `00_internal/` 到 `05_knowledge/` 的 `report_pack` 目录
- 输出新版本 `screenshot_index.csv` 和带 `canonical_issue_key / primary_section / duplicate_of / evidence_role` 的 `issues.csv`

补充说明：

- client 现在会把 `queryTimestamp` 统一按字符串发给远端服务，避免 `trace_fact_sheet` 调用时出现 `422`
- 如果要调用 `sql_fact_sheet`，现在也可以通过 `--op-name` 传入 SQL 操作名

## 适合下游怎么消费

如果目标是正式巡检报告，而不是只看 JSON，建议优先关注 pack 里的这些字段：

- `page_links`
  - 适合直接插入 Word 的可点击链接
- `screenshot_hints`
  - 可直接转成“建议截图什么 / 标注什么”的说明
- `coverage_boundary`
  - 可判断某个章节是强证据还是弱证据
- `metric_semantics`
  - 可帮助写出带主语和统计口径的描述
- `evidence_linkage`
  - 可帮助把时间窗、接口、trace、SQL、依赖串成证据链
- `build-report-pack` 的导出目录
  - 适合把结构化 pack 继续转成可直接交给上层报告生成器消费的章节素材包

## 适合给 Codex 怎么用

机器 B 上的 Codex 最适合直接调用这个 CLI。

典型方式：

1. 先调用 `meta` 了解服务能力
2. 再调用 `diagnostic_candidate_pack`
3. 对重点对象继续调用：
   - `action_fact_sheet`
   - `trace_fact_sheet`
   - `database_component_pack`
   - `nosql_component_pack`
   - `connection_pool_pack`
   - `knowledge_context_pack`

更详细的面向模型 / agent 的说明见：

- [machine_b_agent_adapter_usage.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/machine_b_agent_adapter_usage.md)

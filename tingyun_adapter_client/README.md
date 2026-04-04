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

更详细的面向模型 / agent 的说明见：

- [machine_b_agent_adapter_usage.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/machine_b_agent_adapter_usage.md)

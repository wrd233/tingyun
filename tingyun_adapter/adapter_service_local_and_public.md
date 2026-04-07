# Tingyun Adapter 服务化与发布说明

生成时间：2026-04-04  
项目目录：`/Users/wangrundong/work/mywork/tingyun_adapter`

## 1. 目标

这份文档说明两件事：

1. 如何在机器 A 本地把 `tingyun_adapter` 跑成一个 HTTP 服务
2. 如何验证本地服务
3. 如何把这个服务通过公网发布给机器 B 上的模型 / agent 调用

当前实现的是：

- 本地 FastAPI 服务
- 健康检查
- pack 构建接口
- 基于 `service_api_key` 的简单鉴权
- 基于最小请求间隔和每分钟上限的基础节流
- 面向正式报告取证的深链、截图建议、覆盖边界与截图索引输出

## 2. 配置

先编辑本地配置文件：

- [config.local.json](/Users/wangrundong/work/mywork/tingyun_adapter/config.local.json)

建议至少填写：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "你的听云 Bearer Token",
  "lang": "zh_CN",
  "timezone": "Asia/Shanghai",
  "timeout_seconds": 30,
  "captured_api_dir": "../tingyun_cdp_capture/captured_api",
  "knowledge_dir": "./knowledge",
  "console_public_base_url": "https://your-tingyun-console.example.com",
  "service_host": "127.0.0.1",
  "service_port": 8000,
  "service_api_key": "请改成一个随机长字符串",
  "service_public_base_url": "",
  "service_min_interval_ms": 800,
  "service_max_requests_per_minute": 30
}
```

说明：

- `token`
  - live 模式请求听云接口时需要
- `captured_api_dir`
  - sample 模式需要
- `console_public_base_url`
  - 用于生成适合 Word 报告使用的可点击控制台链接
  - 当前输出以“控制台根地址 + 页面类型 + 导航路径 + 筛选条件”为主
- `knowledge_dir`
  - 用于保存业务系统维度的 confirmed knowledge / pending proposals / judgment log
  - 默认建议使用项目下的 `./knowledge`
- `service_host`
  - 本地启动监听地址
- `service_port`
  - 本地启动端口
- `service_api_key`
  - 对外暴露时用于保护服务
- `service_min_interval_ms`
  - 同一个调用方两次请求之间的最小间隔
- `service_max_requests_per_minute`
  - 同一个调用方每分钟允许的最大请求数

## 3. 安装依赖

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install -e .
```

如果只想显式安装服务依赖，也可以：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install --user fastapi uvicorn
```

如果你的 macOS 系统 Python 较老，`pip install -e .` 可能会被系统目录权限或旧版 `pip` 的 editable 行为卡住。在这种情况下，推荐直接使用：

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install --user fastapi uvicorn
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api
```

## 4. 本地启动服务

### 方式一：通过脚本入口

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
tingyun-adapter-service
```

### 方式二：通过模块启动

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api
```

### 方式三：显式指定 host / port / config

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.service.http_api \
  --config ./config.local.json \
  --host 127.0.0.1 \
  --port 8000
```

## 5. 本地验证

### 5.1 健康检查

```bash
curl http://127.0.0.1:8000/healthz
```

预期会返回：

- `status: ok`
- 当前 `base_url`
- 当前 `console_public_base_url`
- 当前 `knowledge_dir`
- `captured_api_attached`
- `knowledge_repository_configured`
- `has_tingyun_token`
- 当前节流参数

### 5.2 查看支持的 pack

```bash
curl http://127.0.0.1:8000/v1/meta
```

### 5.3 构建 `system_snapshot`

如果你配置了 `service_api_key`，需要带请求头：

```bash
export ADAPTER_API_KEY='你在 config.local.json 里配置的 service_api_key'
```

```bash
curl http://127.0.0.1:8000/v1/packs/system_snapshot \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1059,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample"
  }'
```

### 5.4 构建 `diagnostic_candidate_pack`

```bash
curl http://127.0.0.1:8000/v1/packs/diagnostic_candidate_pack \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample",
    "limit": 5
  }'
```

### 5.4.1 构建 `screenshot_index_pack`

```bash
curl http://127.0.0.1:8000/v1/packs/screenshot_index_pack \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample",
    "limit": 5
  }'
```

### 5.4.2 构建 `knowledge_context_pack`

```bash
curl http://127.0.0.1:8000/v1/packs/knowledge_context_pack \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample",
    "limit": 5
  }'
```

### 5.4.3 构建 `knowledge_update_proposal_pack`

```bash
curl http://127.0.0.1:8000/v1/packs/knowledge_update_proposal_pack \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample",
    "proposalItems": [
      {
        "proposal_type": "action_labels",
        "target_file_hint": "action_labels",
        "target_ref": {
          "kind": "action",
          "biz_system_id": 1065,
          "application_id": 1644,
          "action_id": 13220,
          "action_type": "TX"
        },
        "summary": "模型建议该 action 可能属于核心业务链路。",
        "attributes": {
          "candidate_labels": ["core_business_path"]
        },
        "reasoning_summary": "来自当前一次分析的结构化建议。"
      }
    ],
    "persistProposals": true
  }'
```

### 5.5 构建 `action_fact_sheet`

```bash
curl http://127.0.0.1:8000/v1/packs/action_fact_sheet \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "applicationId": 1644,
    "actionId": 13220,
    "actionType": "TX",
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample",
    "limit": 5
  }'
```

### 5.6 构建 `trace_fact_sheet`

```bash
curl http://127.0.0.1:8000/v1/packs/trace_fact_sheet \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1062,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample"
  }'
```

说明：

- `queryTimestamp` 在 HTTP 接口里按字符串接收
- 如果这个值来自别的 pack 中的数值时间戳，客户端应先转成字符串再透传

## 6. `sample` 与 `live` 的使用建议

### `sample`

适合：

- 本地开发
- API 结构验证
- 机器 B 上先验证调用链

### `live`

适合：

- 真实诊断
- 当前报告生成
- 线上最新时间窗分析

示例：

```bash
curl http://127.0.0.1:8000/v1/packs/action_hotspot_pack \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: $ADAPTER_API_KEY" \
  -d '{
    "bizSystemId": 1065,
    "endTime": "2026-04-04 10:30",
    "periodMinutes": 30,
    "sourceMode": "live"
  }'
```

## 6.1 正式报告取证相关输出

重点 pack 现在会带上这些统一字段：

- `page_links`
- `primary_console_url`
- `related_console_urls`
- `screenshot_hints`
- `metric_semantics`
- `coverage_boundary`
- `evidence_linkage`

其中：

- `page_links`
  - 给出页面类型、链接、建议导航路径和建议筛选条件
- `screenshot_hints`
  - 给出建议截图内容、建议标注内容和建议使用章节
- `coverage_boundary`
  - 明确页面体验是否是真实覆盖还是代理证据
- `screenshot_index_pack`
  - 聚合成可直接给 Word 报告使用的截图候选卡片
- `knowledge_context_pack`
  - 聚合业务知识、待确认提议和判断日志，适合给大模型直接消费
- `knowledge_update_proposal_pack`
  - 作为后续人工确认或审批流程的结构化落点

## 7. 公网发布建议

### 推荐方案：Cloudflare Tunnel

这是最适合机器 A 为 macOS 的快速发布方案。

思路是：

1. 本地先把服务跑在：
   - `127.0.0.1:8000`
2. 用 Cloudflare Tunnel 把本地端口映射成一个 HTTPS 公网域名

优点：

- 不要求机器 A 有公网 IP
- 不必自己处理复杂端口映射
- 自带 HTTPS
- 很适合给机器 B 的 agent / skill 调用

### 基本步骤

#### 1. 安装 cloudflared

```bash
brew install cloudflared
```

#### 2. 登录 Cloudflare

```bash
cloudflared tunnel login
```

#### 3. 创建 tunnel

```bash
cloudflared tunnel create tingyun-adapter
```

#### 4. 创建配置文件

例如：

`~/.cloudflared/config.yml`

```yaml
tunnel: tingyun-adapter
credentials-file: /Users/你的用户名/.cloudflared/xxxxx.json

ingress:
  - hostname: tingyun-adapter.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

#### 5. 运行 tunnel

```bash
cloudflared tunnel run tingyun-adapter
```

### 发布后如何调用

例如公网地址是：

- `https://tingyun-adapter.example.com`

则机器 B 可直接请求：

```bash
curl https://tingyun-adapter.example.com/v1/packs/system_snapshot \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Adapter-API-Key: 你的 service_api_key" \
  -d '{
    "bizSystemId": 1059,
    "endTime": "2026-04-03 12:20",
    "periodMinutes": 30,
    "sourceMode": "sample"
  }'
```

## 8. 公网发布时的安全建议

至少建议做到：

1. `service_api_key` 必须改成随机长字符串
2. 只通过 HTTPS 暴露
3. 不要把听云 token 输出给调用方
4. 先用 `sample` 验证，再开放 `live`
5. 如果后续有多个调用方，建议再加一层：
   - IP allowlist
   - 反向代理鉴权
   - 请求日志
   - 限流

## 9. 机器 B 后续如何接

当机器 A 上这个服务跑通后，机器 B 上有三种典型接入方式：

1. 直接 HTTP 调用
2. 包一层 Python client / CLI
3. 再往上包成 MCP / plugin，让 agent / Codex 更自然地调用

当前阶段最推荐：

- 先用 HTTP + skill
- 后续再演进到 MCP / plugin

## 10. 机器 B 的接入项目

机器 B 现在已经有独立的远程 client 项目：

- [../tingyun_adapter_client/README.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/README.md)
- [../tingyun_adapter_client/machine_b_agent_adapter_usage.md](/Users/wangrundong/work/mywork/tingyun_adapter_client/machine_b_agent_adapter_usage.md)

建议机器 B：

1. 只配置 `service_base_url` 和 `service_api_key`
2. 先调用 `healthz` 和 `meta`
3. 再调用 `build-pack`
4. 先走 `sample`，验证通过后再切 `live`

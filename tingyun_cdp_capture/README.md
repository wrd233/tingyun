# Tingyun CDP 抓取项目

这个项目负责两件事：

- 抓取听云页面里的 `/server-api/` 请求，沉淀接口样本
- 回放关键诊断链路，验证接口能否独立模拟调用

它不再承载 `adapter` 源码；`adapter` 已经拆到同级目录 [tingyun_adapter](/Users/wangrundong/work/mywork/tingyun_adapter)。

## 主要内容

- `capture_tingyun_api.py`
  - 监听 Chrome CDP，按接口路径归档请求样本
- `replay_action_trace_flow.py`
  - 回放 `bizSystem -> action -> trace -> detail` 诊断链路
- `captured_api/`
  - 聚合后的接口样本
- `raw_logs/`
  - 更细粒度的请求 / 响应样本
- `api_analysis_priority.md`
- `api_report_shortlist.md`
- `tingyun_manual_context_and_component_mapping.md`
- `tingyun_system_skeleton_diagnostic_playbook.md`

## 本地配置

优先使用本地配置文件：

- `config.local.json`

先复制示例：

```bash
cp /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json.example /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json
```

示例结构：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "paste-your-token-here",
  "timeout": 30,
  "default_biz_system_id": 1065
}
```

`replay_action_trace_flow.py` 会按下面顺序取 token：

1. `--token`
2. `config.local.json` 中的 `token`
3. 环境变量 `TINGYUN_TOKEN`
4. 环境变量 `TOKEN`

## 抓取

### 1. 启动 Chrome 调试端口

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir=/tmp/tingyun-cdp-profile
```

### 2. 安装依赖

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -r requirements.txt
```

### 3. 查看可连接目标

```bash
python3 capture_tingyun_api.py --list-targets
```

### 4. 开始抓取

```bash
python3 capture_tingyun_api.py \
  --browser-url http://127.0.0.1:9222 \
  --api-prefix http://169.169.173.25:8080/server-api/ \
  --target-url-contains 169.169.173.25:8080 \
  --output-dir ./captured_api \
  --raw-log-dir ./raw_logs \
  --network-total-buffer-bytes 50000000 \
  --network-resource-buffer-bytes 5000000 \
  --verbose
```

## 回放 action -> trace 链路

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 replay_action_trace_flow.py --biz-system-id 1065 --time-period 30
```

如果要指定配置文件：

```bash
python3 replay_action_trace_flow.py --config ./config.local.json --biz-system-id 1065
```

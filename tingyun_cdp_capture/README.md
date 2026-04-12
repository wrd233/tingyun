# Tingyun CDP Capture

`tingyun_cdp_capture/` 是平台行为抓取、接口样本沉淀和关键链路回放工程。

## 在整体链路中的位置

- 它位于最靠近听云平台的一层
- 为 `tingyun_adapter/` 提供接口样本、链路理解和取证入口
- 不直接承担最终报告写作，也不承担批次级材料归档

## 当前目录负责什么

- `capture_tingyun_api.py`
  - 通过 Chrome CDP 抓取 `/server-api/` 请求
- `replay_action_trace_flow.py`
  - 回放 `bizSystem -> action -> trace -> detail` 关键链路
- `tests/`
  - 抓取工程自身测试
- `config.local.json.example`
  - 本地配置示例

## 不负责什么

- 不承担 adapter 中间层逻辑
- 不承担 client 本地物化目录组织
- 不长期保存真实批次的完整运行产物

## 样例与运行产物边界

- 当前仓库里保留了一份已入库 capture 样本，主要供 sample-mode 回归和测试使用
- 新增真实运行结果建议写入：
  - `artifacts/monitored_systems/<system_key>/<batch_key>/capture/`
- 需要长期保留的缩样样例建议进入：
  - `samples/monitored_systems/<system_key>/<sample_batch_key>/capture/`

更完整的边界说明见：

- [capture-runtime-artifacts.md](/Users/wangrundong/work/mywork/docs/workflows/capture-runtime-artifacts.md)

## 本地配置

先复制：

```bash
cp /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json.example /Users/wangrundong/work/mywork/tingyun_cdp_capture/config.local.json
```

示例：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "paste-your-token-here",
  "timeout": 30,
  "default_biz_system_id": 1065
}
```

## 最小运行入口

安装依赖：

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -r requirements.txt
```

列出可连接目标：

```bash
python3 capture_tingyun_api.py --list-targets
```

抓取时，建议显式把输出目录指向某个批次目录：

```bash
python3 capture_tingyun_api.py \
  --browser-url http://127.0.0.1:9222 \
  --api-prefix http://169.169.173.25:8080/server-api/ \
  --target-url-contains 169.169.173.25:8080 \
  --output-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/capture/captured_api \
  --raw-log-dir /Users/wangrundong/work/mywork/artifacts/monitored_systems/<system_key>/<batch_key>/capture/raw_logs
```

回放链路：

```bash
python3 replay_action_trace_flow.py --biz-system-id 1065 --time-period 30
```

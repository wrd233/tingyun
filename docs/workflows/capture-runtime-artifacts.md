# Capture Runtime Artifacts

`tingyun_cdp_capture/` 目录自身只保留抓取工程所需的脚本、测试、配置样例和工程 README。

## 运行时产物

真实抓取或回放产物不应长期留在主工程目录中，建议放入：

`artifacts/monitored_systems/<system_key>/<batch_key>/capture/`

可细分为：

- `captured_api/`
- `raw_logs/`
- `replay_notes/`

## 已入库样例

如果需要保留一个可读样例，应只保留缩样后的稳定子集，并放到：

`samples/monitored_systems/<system_key>/<sample_batch_key>/capture/`

## 当前仓库说明

当前 `tingyun_cdp_capture/` 下保留了一份已入库 capture 样本，用于 sample-mode 回归与测试；新增真实运行结果仍应优先进入 `artifacts/`。

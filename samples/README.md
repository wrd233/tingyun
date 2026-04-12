# Samples

`samples/` 只放经过挑选和整理、愿意长期入库的稳定样例。

## 组织方式

路径：

`samples/monitored_systems/<system_key>/<sample_batch_key>/`

典型子目录：

- `capture/`
- `diagnostics/`
- `report_bundle/`
- `reports/`

## 边界

- 这里不是完整真实运行目录
- 真实批次产物应进入 `artifacts/`
- 样例应控制体量，并保持便于阅读和回归

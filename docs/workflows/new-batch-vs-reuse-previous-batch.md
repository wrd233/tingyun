# New Batch Vs Reuse Previous Batch

## 新开批次

适用场景：

- 希望完全重新开始
- 不希望历史运行结果污染本次判断

做法：

1. 新建 `artifacts/monitored_systems/<system_key>/<batch_key>/`
2. 只读取 `knowledge/monitored_systems/<system_key>/` 下的长期知识
3. 本次 capture、packs、diagnostics、reports 全部写入新批次目录

## 复用上次监测沉淀

适用场景：

- 需要延续系统画像、命名映射、review queue
- 需要参考上一批次的中间表或证据入口

边界：

- 系统级知识直接复用 `knowledge/`
- 历史批次结果只可作为输入来源，不与本批次共用同一套运行文件
- 复用后的整理结果仍必须写回当前批次目录

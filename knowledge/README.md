# Knowledge

`knowledge/` 用来保存系统级长期知识，而不是某次运行的瞬时结果。

## 组织方式

路径：

`knowledge/monitored_systems/<system_key>/`

典型子目录：

- `system_profile/`
- `mappings/`
- `context/`
- `review_queue/`

## 边界

- 这里的内容跨批次复用
- 不直接存放本次运行的 pack、report materials 或临时调试文件

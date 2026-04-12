# Three Main Projects

仓库围绕三大主工程协作展开：

## `tingyun_cdp_capture/`

定位：

- 平台行为抓取
- 接口样本沉淀
- 关键页面链路回放

负责：

- 确认平台真实可调用能力
- 为 adapter 提供样本和链路理解基础

不负责：

- 最终报告写作
- 批次级材料归档
- 机器 B 本地物化目录组织

## `tingyun_adapter/`

定位：

- 诊断中间层
- 整个项目的结构中心

负责：

- 候选对象筛选
- 证据增强与关系组织
- 知识读取与增强
- writer input / export view 等报告素材层输出

不负责：

- 退化为简单平台代理
- 在源码目录长期存放真实批次产物
- 替代 client 做本地材料归档

## `tingyun_adapter_client/`

定位：

- 远程调用器
- 本地物化器

负责：

- 调用机器 A 上的 adapter 服务
- 获取 pack 与 export view
- 按系统 / 批次落地本地材料目录

不负责：

- 替代 capture
- 在源码目录长期保留真实报告结果
- 定义唯一最终成文路径

## 主链路

1. capture 建立平台真实能力理解。
2. adapter 重组能力为诊断和写作可消费的中间层。
3. client 把中间层物化为本地目录，供 agent、写作者和脚本继续消费。

## 机器 A / 机器 B

- 机器 A 主要承载 `tingyun_adapter/` 服务能力，以及对听云平台的访问。
- 机器 B 主要承载 `tingyun_adapter_client/`、agent、Codex、写作者消费链路。
- `tingyun_cdp_capture/` 服务于平台理解与样本验证，但不等于每次报告生产入口。

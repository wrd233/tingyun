# Tingyun Adapter

这个项目负责把听云平台原始接口整理成更适合分析与报告场景的结构化 pack。

当前已经完成的核心能力：

- 阶段 1-2
  - schema / ref / envelope / entity
  - raw client
  - 字段归一化
  - `opName` 解码
  - `CapturedApiRepository`
- 阶段 3
  - `system_snapshot`
  - `action_hotspot_pack`
  - `trace_case_pack`
  - `report_fact_pack`
- 阶段 4
  - `database_component_pack`
  - `nosql_component_pack`
  - `connection_pool_pack`

## 本地配置

优先使用本地配置文件：

- `config.local.json`

先复制示例：

```bash
cp /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json.example /Users/wangrundong/work/mywork/tingyun_adapter/config.local.json
```

示例结构：

```json
{
  "base_url": "http://169.169.173.25:8080",
  "token": "paste-your-token-here",
  "lang": "zh_CN",
  "timezone": "Asia/Shanghai",
  "timeout_seconds": 30,
  "captured_api_dir": "../tingyun_cdp_capture/captured_api"
}
```

`tingyun_adapter` 会按下面顺序读取配置：

1. CLI 参数
2. `config.local.json`
3. 环境变量
4. 默认值

其中 token 额外支持：

- `TINGYUN_TOKEN`
- `TOKEN`

## 安装

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
python3 -m pip install -e .
```

## 运行测试

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

## 查看 CLI

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --help
```

## 典型调用

### `system_snapshot`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `report_fact_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack report_fact_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

### `database_component_pack`

```bash
cd /Users/wangrundong/work/mywork/tingyun_adapter
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --build-pack database_component_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL'
```

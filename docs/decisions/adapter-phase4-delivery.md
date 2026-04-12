# Adapter 阶段 4 交付说明

这份文档说明 Tingyun adapter 在阶段 4 已完成的 `Database / NoSQL / Connection` 组件闭环能力，并给出每部分的典型输入输出。

## 阶段 4 完成了什么

当前已经补齐 3 个新的组件 pack builder：

- `build_database_component_pack`
- `build_nosql_component_pack`
- `build_connection_pool_pack`

对应代码位置：

- `src/tingyun_adapter/usecases/component_builders.py`

同时补充了：

- `Database/actionName/list`
- `Database/applicationName/list`
- `NoSQL/actionName/list`
- `NoSQL/applicationName/list`

对应 client 方法，方便 live 模式下真正走通组件下钻链路。

## 当前闭环能力

### 1. Database 闭环

当前已经打通：

- `Database/list`
- `Database/info`
- `Database/analysis`
- `component/database/actionList`
- `component/database/actionTraceList`
- `graph/component/queryDataBaseGraph`
- `connection/database/chart`

这条链路可以整理出：

- 热点 Database 组件
- 组件总体指标
- 热点 SQL / 热点操作
- 受影响动作
- 相关 trace 摘要
- 组件拓扑
- 连接时间图表摘要

### 2. NoSQL 闭环

当前已经打通：

- `NoSQL/list`
- `NoSQL/overview`
- `NoSQL/analysis`
- `NoSQL/actionName/list`
- `NoSQL/trace`
- `NoSQL/errorTypeAmount`
- `graph/component/queryNosqlGraph`

这条链路可以整理出：

- 热点 NoSQL 组件
- 热点操作
- 受影响动作
- trace 列表
- 错误类型统计
- NoSQL 拓扑

说明：

- 当前样本里 `NoSQL/trace` 返回为空，所以 pack 会显式给 warning，而不是伪造 trace 结论。

### 3. Connection 闭环

当前已经打通：

- `connection/list`
- `connection/chart`
- `connection/database/chart`

这条链路可以整理出：

- 热点连接池对象
- 当前使用量 / 空闲量 / 最大连接数
- 连接池分钟级时序
- 数据库连接时间图
- 等待连接风险摘要

## SDK 与 CLI 调用方式

### SDK 调用

#### Database

```python
from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import DatabaseComponentRef
from tingyun_adapter.invocation.sdk import Adapter

adapter = Adapter(AdapterSettings(captured_api_dir="./captured_api"))
context = adapter.build_context(
    biz_system_id=1065,
    end_time="2026-04-03 12:20",
    period_minutes=30,
)

pack = adapter.build_database_component_pack(
    context,
    source_mode="sample",
    component_ref=DatabaseComponentRef(
        biz_system_id=1065,
        component_name="10.190.22.21:3306",
        component_subtype="MySQL",
    ),
)
```

#### NoSQL

```python
from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import NoSQLComponentRef
from tingyun_adapter.invocation.sdk import Adapter

adapter = Adapter(AdapterSettings(captured_api_dir="./captured_api"))
context = adapter.build_context(
    biz_system_id=1065,
    end_time="2026-04-03 12:20",
    period_minutes=30,
)

pack = adapter.build_nosql_component_pack(
    context,
    source_mode="sample",
    component_ref=NoSQLComponentRef(
        biz_system_id=1065,
        component_name="10.190.22.20:6379/5",
        component_subtype="Redis",
    ),
)
```

#### Connection

```python
from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ConnectionPoolRef
from tingyun_adapter.invocation.sdk import Adapter

adapter = Adapter(AdapterSettings(captured_api_dir="./captured_api"))
context = adapter.build_context(
    biz_system_id=1059,
    end_time="2026-04-03 12:20",
    period_minutes=30,
)

pack = adapter.build_connection_pool_pack(
    context,
    source_mode="sample",
    pool_ref=ConnectionPoolRef(
        biz_system_id=1059,
        metric_category="169.169.4.41:1521%2Fedidb1/Database-1dca1be1f5aaae369560473d420e30d6",
        application_id=1648,
        instance_id=2754,
    ),
)
```

### CLI 调用

#### Database

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack database_component_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --component-name '10.190.22.21:3306' \
  --component-subtype 'MySQL'
```

#### NoSQL

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack nosql_component_pack \
  --biz-system-id 1065 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --component-name '10.190.22.20:6379/5' \
  --component-subtype 'Redis'
```

#### Connection

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack connection_pool_pack \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample \
  --metric-category '169.169.4.41:1521%2Fedidb1/Database-1dca1be1f5aaae369560473d420e30d6' \
  --application-id 1648 \
  --instance-id 2754
```

## 典型输入输出

下面的示例来自当前样本目录中的真实结构，做了适度裁剪，目的是展示 pack 的典型形状。

### 1. `database_component_pack`

典型输入：

```json
{
  "bizSystemId": 1065,
  "endTime": "2026-04-03 12:20",
  "periodMinutes": 30,
  "componentName": "10.190.22.21:3306",
  "componentSubtype": "MySQL",
  "sourceMode": "sample"
}
```

典型输出摘要：

```json
{
  "pack_type": "database_component_pack",
  "payload": {
    "summary": {
      "component_name": "10.190.22.21:3306",
      "component_subtype": "MySQL",
      "response_time_ms": 8.0,
      "total_response_time_ms": 482262.0,
      "throughput": 33.42,
      "trace_count": 36,
      "operation_count": 1,
      "impacted_action_count": 10,
      "related_trace_count": 2
    },
    "top_operations": [
      {
        "op_name_raw": "tyBase64_...",
        "op_name_decoded": "select DISTINCT info.ID, ...",
        "response_time_ms": 2485.0,
        "count": 21
      }
    ],
    "top_impacted_actions": [
      {
        "actionId": 13238,
        "actionName": "URI/grcv5/dwr/call/plaincall/dwrTodolistService.setSeenFlag.dwr",
        "count": 524,
        "slowCount": 28
      }
    ],
    "top_related_traces": [
      {
        "actionId": 13238,
        "actionGuid": "7101fff31a80619e",
        "timestamp": 1775189172000,
        "resp_time_ms": 2522.765
      }
    ],
    "topology_summary": {
      "node_count": 51,
      "line_count": 50
    }
  }
}
```

### 2. `nosql_component_pack`

典型输入：

```json
{
  "bizSystemId": 1065,
  "endTime": "2026-04-03 12:20",
  "periodMinutes": 30,
  "componentName": "10.190.22.20:6379/5",
  "componentSubtype": "Redis",
  "sourceMode": "sample"
}
```

典型输出摘要：

```json
{
  "pack_type": "nosql_component_pack",
  "payload": {
    "summary": {
      "component_name": "10.190.22.20:6379/5",
      "component_subtype": "Redis",
      "response_time_ms": 1.0,
      "throughput": 0.22,
      "operation_count": 1,
      "trace_count": 0,
      "impacted_action_count": 23
    },
    "top_operations": [
      {
        "op_name_raw": "EVAL",
        "op_name_decoded": "EVAL",
        "response_time_ms": 1.0,
        "count": 472
      }
    ],
    "top_related_traces": [],
    "error_summary": {
      "series_count": 0,
      "series": []
    },
    "topology_summary": {
      "node_count": 3,
      "line_count": 2
    }
  },
  "meta": {
    "warnings": [
      {
        "code": "nosql_trace_empty"
      }
    ]
  }
}
```

### 3. `connection_pool_pack`

典型输入：

```json
{
  "bizSystemId": 1059,
  "endTime": "2026-04-03 12:20",
  "periodMinutes": 30,
  "metricCategory": "169.169.4.41:1521%2Fedidb1/Database-1dca1be1f5aaae369560473d420e30d6",
  "applicationId": 1648,
  "instanceId": 2754,
  "sourceMode": "sample"
}
```

典型输出摘要：

```json
{
  "pack_type": "connection_pool_pack",
  "payload": {
    "summary": {
      "framework": "Druid",
      "database_type": "Oracle",
      "current_used": 5,
      "current_idle": 55,
      "max_active": 60,
      "usage_ratio": 0.0833,
      "avg_time_ms": 0.29,
      "database_connection_time_avg_ms": 0.0,
      "pool_instance_count": 3
    },
    "time_series": {
      "used_connections": {
        "point_count": 30,
        "latest_used_connections": 3.0,
        "latest_waiter_connections": 0.0,
        "latest_usage_ratio_pct": 15.0,
        "max_waiter_connections": 0.0
      },
      "database_connection_time": {
        "overview": {
          "avg": 0.0
        },
        "point_count": 30
      }
    },
    "waiter_risk": {
      "latest_waiter_connections": 0.0,
      "max_waiter_connections": 0.0,
      "latest_usage_ratio_pct": 15.0,
      "risk_level": "low"
    }
  }
}
```

## 测试覆盖

阶段 4 的样本模式测试已经加入：

- `tests/unit/test_usecases.py`

新增覆盖项：

- `database_component_pack`
- `nosql_component_pack`
- `connection_pool_pack`

## 当前限制

当前阶段 4 仍然有几个明确边界：

- `sample` 模式依赖真实抓包样本，样本不全时只能回退或给 warning
- `component/database/actionTraceList` 当前样本只有 `actionGuid` 与 `actionTimestamp`，没有完整数值型 `traceId`，因此 Database pack 中的“related trace”目前仍是 trace 摘要，不是完整 detail
- `NoSQL/trace` 当前样本为空，所以 NoSQL pack 可以给出“热点操作 + 影响动作 + 拓扑”，但暂时不能给出完整 trace 案例
- `connection/list` 对 live 模式依赖 `bizSystemName` 与 `beginTime`，当前已经自动推断，但后续仍建议继续用真实环境验证

## 下一步建议

阶段 4 完成后，下一步最自然的是：

- 把 `report_fact_pack` 与这三类组件 pack 进一步联动
- 做“系统概览 -> 热点 action -> trace -> 组件”跨域下钻链路
- 让 skill 直接消费这些 pack，而不是重新解析听云原始字段

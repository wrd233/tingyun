# Adapter Phase 3 Delivery

This note records the current stage 3 scaffold for the Tingyun adapter project.

## Scope completed

Stage 3 now includes four initial pack builders:

- `build_system_snapshot`
- `build_action_hotspot_pack`
- `build_trace_case_pack`
- `build_report_fact_pack`

These builders can work in:

- `sample` mode, backed by `captured_api/`
- `live` mode, backed by real HTTP calls
- `auto` mode, which prefers `captured_api/` when attached

## New modules

Core usecase layer:

- `src/tingyun_adapter/usecases/builders.py`

Supporting clients added for stage 3:

- `src/tingyun_adapter/clients/application_client.py`
- `src/tingyun_adapter/clients/health_client.py`

SDK integration:

- `Adapter.build_system_snapshot(...)`
- `Adapter.build_action_hotspot_pack(...)`
- `Adapter.build_trace_case_pack(...)`
- `Adapter.build_report_fact_pack(...)`

CLI integration:

- `--build-pack system_snapshot`
- `--build-pack action_hotspot_pack`
- `--build-pack trace_case_pack`
- `--build-pack report_fact_pack`

## What each builder currently does

### system_snapshot

Collects:

- business overview
- health level statistics
- response / throughput / error trend summaries

Builds:

- normalized biz-system snapshot payload
- trend summaries suitable for report consumption
- evidence list

### action_hotspot_pack

Collects:

- action list
- matching action overview when available

Builds:

- ranked hotspots
- ranking rationale
- severity score
- evidence

### trace_case_pack

Collects:

- selected trace detail
- call tree summary when available
- exception summary when available

Builds:

- normalized trace case
- selector and drilldown path
- evidence

### report_fact_pack

Composes:

- system snapshot
- action hotspots
- trace case

Builds:

- report scope
- executive summary
- first-pass issue list
- drilldown path
- merged evidence

## Test coverage

Stage 3 sample-mode tests now exist for all four builders under:

- `tests/unit/test_usecases.py`

## Example commands

Run all unit tests:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

Build a system snapshot from samples:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack system_snapshot \
  --biz-system-id 1059 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

Build a trace case from samples:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli \
  --captured-api-dir ./captured_api \
  --build-pack trace_case_pack \
  --biz-system-id 1062 \
  --end-time '2026-04-03 12:20' \
  --period-minutes 30 \
  --source-mode sample
```

## Known limitations

Current stage 3 is intentionally still a first scaffold:

- sample mode depends on what is present in `captured_api/`
- some sample domains are not perfectly aligned by bizSystemId
- `trace_current_overview` in sample mode is not yet reconstructed from captured variants, so sample trace selection currently falls back to captured trace detail samples
- issue extraction is still heuristic rather than policy-driven

## Next target

The next natural step is stage 4:

- database component pack
- NoSQL component pack
- connection pool pack
- richer cross-domain drilldown builders

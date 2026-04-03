# Adapter Phase 1-2 Delivery

This note records what has been completed for stage 1 and stage 2 of the Tingyun adapter plan, what is now runnable, and what remains intentionally deferred to later stages.

## Scope completed

Stage 1 completed:

- project package scaffold under `src/tingyun_adapter/`
- adapter config model and environment loading
- domain schema for context, refs, evidence, envelope, entities, and pack payloads
- CLI bootstrap and SDK bootstrap
- packaging metadata in `pyproject.toml`

Stage 2 completed:

- raw HTTP clients for the core API families:
  - `webaction`
  - `graph`
  - `trace`
  - `Database`
  - `NoSQL`
  - `connection`
  - `logTrace`
- normalization helpers for metric fields and inconsistent trace/component keys
- `opName` decoding for `tyBase64_`-style values
- offline `CapturedApiRepository` for replaying sample responses from `captured_api/`
- initial unit-test suite for schema serialization, resolvers, normalizers, SDK bootstrap, and sample replay

## Package layout

```text
src/tingyun_adapter/
  clients/
  config/
  domain/
    models/
  invocation/
  normalizers/
  sources/
tests/unit/
```

## What is runnable now

Run unit tests:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

Inspect adapter bootstrap:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --captured-api-dir ./captured_api
```

Install as editable package:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -e .
tingyun-adapter --captured-api-dir ./captured_api
```

## What is intentionally not in stage 1-2

These are deferred to later phases on purpose:

- concrete pack builders such as `build_system_snapshot`
- cross-API orchestration logic
- report fact aggregation
- online/offline execution mode switching at use-case level
- caching, persistence, and batch pipelines
- skill-facing report generation logic

## Current quality gate

The current stage 1-2 delivery is considered healthy when all of the following pass:

- Python syntax check for the adapter package
- unit tests under `tests/unit/`
- CLI bootstrap help output
- captured-api repository can read real sample files from `captured_api/`

## Next implementation target

The next natural phase is stage 3:

- `build_system_snapshot`
- `build_action_hotspot_pack`
- `build_trace_case_pack`
- `build_report_fact_pack`

Those builders will sit on top of the schema, raw clients, normalizers, and sample repository completed here.

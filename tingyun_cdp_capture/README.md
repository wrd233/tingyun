# Tingyun CDP Capture

This tool listens to Chrome DevTools Protocol (CDP), keeps only requests under a target `/server-api/` prefix, writes one JSON file per endpoint path plus a top-level `index.json`, and also stores one best raw request/response sample per request signature under `raw_logs/`.

The folder also contains `replay_action_trace_flow.py`, a standalone HTTP replay script that can:

- find the slowest action inside one `bizSystemId`
- fetch that action's overview
- query the trace list for that action
- pick one trace row and print key fields from `action/trace/detail`

The folder now also contains an initial `tingyun_adapter` project skeleton under `src/`, covering stage 1 and stage 2 of the adapter plan:

- core schema / ref / pack envelope models
- raw source clients for the main API families
- field normalizers and key resolvers
- offline captured-api repository for sample replay
- basic SDK / CLI scaffolding
- unit tests for the core normalization logic

Stage 3 is now scaffolded too:

- `system_snapshot`
- `action_hotspot_pack`
- `trace_case_pack`
- `report_fact_pack`

## What it does

- Connects to one or more Chrome tabs through the remote debugging port
- Captures `XHR` and `Fetch` requests whose URL starts with a chosen API prefix
- Groups requests by the path after `/server-api/`
- Writes endpoint samples such as `graph/query/overview.json`
- Stores method variants, query examples, body examples, response metadata, a basic inferred purpose, and a replayable sample `curl`
- Stores one best raw request/response JSON per request signature so you can inspect full payloads later

## Folder layout

```text
tingyun_cdp_capture/
  capture_tingyun_api.py
  replay_action_trace_flow.py
  pyproject.toml
  src/
    tingyun_adapter/
  tests/
  requirements.txt
  README.md
  captured_api/
    index.json
    graph/
      query/
        overview.json
  raw_logs/
    graph/
      query/
        overview/
          POST__request_overview__xxxxxxxxxxxx.json
```

## 1. Start Chrome with CDP enabled

Use a separate Chrome instance so the debugging port is predictable:

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir=/tmp/tingyun-cdp-profile
```

Then open your Tingyun page in that Chrome window and log in normally.

## 2. Install dependency

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -r requirements.txt
```

## 3. Optional: list available targets

```bash
python3 capture_tingyun_api.py --list-targets
```

If you have multiple tabs:

- `--target-id` attaches to one exact tab
- `--target-url-contains` now attaches to every matching page tab
- with no target filter, the tool attaches to all page tabs whose URL matches the API host
- while running, it can keep polling Chrome and attach newly opened matching tabs automatically

## 4. Start capturing

Basic run:

```bash
python3 capture_tingyun_api.py --verbose
```

A more explicit run:

```bash
python3 capture_tingyun_api.py \
  --browser-url http://127.0.0.1:9222 \
  --api-prefix http://169.169.173.25:8080/server-api/ \
  --target-url-contains 169.169.173.25:8080 \
  --output-dir ./captured_api \
  --raw-log-dir ./raw_logs \
  --network-total-buffer-bytes 50000000 \
  --network-resource-buffer-bytes 5000000 \
  --verbose
```

Now use the page normally. Each matching request will update:

- `captured_api/index.json`
- `captured_api/<path>.json`
- `raw_logs/<path>/<METHOD>__<variant>__<hash>.json`

Press `Ctrl+C` when you want to stop.

## Output shape

Each endpoint file contains:

- `relative_path`
- `path`
- `count_seen`
- `methods`
- per-method query variants
- per-method body variants
- sample requests
- sample responses
- inferred purpose
- replay info including a sample `curl`

Each raw log file contains:

- the request signature used for deduplication
- the full request URL, query, headers, and parsed body
- the full response status, headers, encoded size, and parsed body when available
- capture metadata and a completeness score

Raw logs are deduplicated by normalized request signature:

- same method
- same endpoint path
- same normalized query
- same normalized request body

If the same request kind is captured many times, the tool keeps only one raw log file and updates it only when a new capture is more complete.

If you see errors like `Request content was evicted from inspector cache`, raise:

- `--network-total-buffer-bytes`
- `--network-resource-buffer-bytes`

These options enlarge Chrome's CDP network buffer so response bodies are less likely to be evicted before capture.

## Notes

- Existing JSON files in `captured_api/` are loaded on startup, so repeated runs keep accumulating observations.
- The tool keeps request headers small on purpose and redacts `Authorization`.
- Raw logs keep a fuller request/response sample, but still only try to capture response bodies for small text or JSON responses.
- For trace-heavy pages, prefer a larger CDP buffer such as `--network-total-buffer-bytes 50000000`.

## Replay one full workflow

Export a valid bearer token first:

```bash
export TINGYUN_TOKEN='your bearer token here'
```

Then run:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 replay_action_trace_flow.py --biz-system-id 1065 --time-period 30
```

Useful options:

- `--end-time '2026-04-03 12:20'`
- `--application-id 0`
- `--page-size 15`
- `--base-url http://169.169.173.25:8080`

The script prints:

- the top actions returned by `webaction/list/actionList`
- the chosen slowest action
- the action overview
- the trace candidates returned by `trace_current_overview`
- a summary of the selected trace detail

## Adapter Skeleton

You can run the current stage 1 / stage 2 unit tests with:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

You can also inspect the initial CLI scaffold with:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --help
```

You can point the adapter bootstrap at your captured samples:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
PYTHONPATH=./src python3 -m tingyun_adapter.invocation.cli --captured-api-dir ./captured_api
```

If you want the project import path and script metadata locally, you can also install it in editable mode:

```bash
cd /Users/wangrundong/work/mywork/tingyun_cdp_capture
python3 -m pip install -e .
tingyun-adapter --captured-api-dir ./captured_api
```

Build a stage 3 pack from captured samples:

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

You can swap `system_snapshot` for:

- `action_hotspot_pack`
- `trace_case_pack`
- `report_fact_pack`

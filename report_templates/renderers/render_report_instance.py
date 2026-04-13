#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_scalar(text: str) -> Any:
    text = text.strip()
    if text == "":
        return ""
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text in {"null", "None", "~"}:
        return None
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return _strip_quotes(text)
    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except ValueError:
            return text
    if re.fullmatch(r"-?\d+\.\d+", text):
        try:
            return float(text)
        except ValueError:
            return text
    return text


def _parse_key(text: str) -> str:
    return _strip_quotes(text.strip())


def _next_meaningful(lines: list[tuple[int, str]], index: int) -> tuple[int, str] | None:
    if index >= len(lines):
        return None
    return lines[index]


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    current = _next_meaningful(lines, index)
    if current is None:
        return {}, index
    _, token = current
    if token.startswith("- "):
        items: list[Any] = []
        while index < len(lines):
            line_indent, raw = lines[index]
            if line_indent != indent or not raw.startswith("- "):
                break
            body = raw[2:].strip()
            index += 1
            if body == "":
                if index < len(lines) and lines[index][0] > indent:
                    nested, index = _parse_block(lines, index, lines[index][0])
                    items.append(nested)
                else:
                    items.append("")
            else:
                items.append(_parse_scalar(body))
        return items, index

    mapping: dict[str, Any] = {}
    while index < len(lines):
        line_indent, raw = lines[index]
        if line_indent != indent or raw.startswith("- "):
            break
        if ":" not in raw:
            raise ValueError(f"Unsupported YAML line: {raw}")
        key, value = raw.split(":", 1)
        key = _parse_key(key)
        value = value.strip()
        index += 1
        if value == "":
            if index < len(lines) and lines[index][0] > indent:
                nested, index = _parse_block(lines, index, lines[index][0])
                mapping[key] = nested
            else:
                mapping[key] = {}
        else:
            mapping[key] = _parse_scalar(value)
    return mapping, index


def load_minimal_yaml(path: Path) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.lstrip(" ")
        if stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(stripped)
        lines.append((indent, stripped))
    if not lines:
        return {}
    parsed, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError(f"YAML parser stopped early at line {index + 1} for {path}")
    if not isinstance(parsed, dict):
        raise ValueError(f"Top-level YAML node must be a mapping: {path}")
    return parsed


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"Could not locate repo root from {start}")


def resolve_repo_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_number(value: Any, *, digits: int = 0) -> str:
    number = parse_float(value)
    if digits == 0:
        return str(int(round(number)))
    return f"{number:.{digits}f}"


def latex_escape(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def top_rows(rows: list[dict[str, str]], key: str, *, limit: int = 5, positive_only: bool = False) -> list[dict[str, str]]:
    filtered = rows
    if positive_only:
        filtered = [row for row in rows if parse_float(row.get(key)) > 0]
    return sorted(filtered, key=lambda row: parse_float(row.get(key)), reverse=True)[:limit]


def collect_asset_status(root: Path, asset_paths: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for relative in asset_paths:
        full = root / relative
        results.append(
            {
                "relative_path": relative,
                "resolved_path": str(full),
                "exists": full.exists(),
                "kind": "directory" if full.is_dir() else "file",
            }
        )
    return results


def build_chapter_outline(spec: dict[str, Any]) -> list[dict[str, Any]]:
    tree = spec.get("chapter_tree") or {}
    order = spec.get("chapter_order") or list(tree.keys())
    outline: list[dict[str, Any]] = []
    for chapter_id in order:
        chapter = tree.get(str(chapter_id), {})
        outline.append(
            {
                "chapter_id": str(chapter_id),
                "title": chapter.get("title", ""),
                "sections": chapter.get("sections", {}),
            }
        )
    return outline


def assemble_main_tex(template_root: Path, chapters_root: Path, target_dir: Path) -> str:
    template_path = template_root / "template.tex"
    text = template_path.read_text(encoding="utf-8")
    rel_root = Path(os.path.relpath(template_root, target_dir)).as_posix()
    rel_chapters = Path(os.path.relpath(chapters_root, target_dir)).as_posix()
    text = text.replace(r"\input{style/report_macros.tex}", rf"\input{{{rel_root}/style/report_macros.tex}}")
    text = text.replace(r"\input{fragments/chapter_1.tex}", rf"\input{{{rel_chapters}/chapter_1.tex}}")
    text = text.replace(r"\input{fragments/chapter_2_1.tex}", rf"\input{{{rel_chapters}/chapter_2_1.tex}}")
    text = text.replace(r"\input{fragments/chapter_2_2.tex}", rf"\input{{{rel_chapters}/chapter_2_2.tex}}")
    text = text.replace(r"\input{fragments/chapter_2_3.tex}", rf"\input{{{rel_chapters}/chapter_2_3.tex}}")
    text = text.replace(r"\input{fragments/chapter_3.tex}", rf"\input{{{rel_chapters}/chapter_3.tex}}")
    text = text.replace(r"\input{fragments/cover.tex}", rf"\input{{{rel_root}/fragments/cover.tex}}")
    text = text.replace(r"\input{fragments/toc.tex}", rf"\input{{{rel_root}/fragments/toc.tex}}")
    header = [
        "% generated by report_templates/renderers/render_report_instance.py",
        "% this file keeps template layout stable and still reads diagnostics directly via report_context.json",
        "",
    ]
    return "\n".join(header) + text


def build_object_map(rows: list[dict[str, str]], key: str = "object_id") -> dict[str, dict[str, str]]:
    return {str(row.get(key, "")): row for row in rows if row.get(key)}


def build_latest_deep_dive_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    for row in rows:
        object_id = str(row.get("object_id", ""))
        if not object_id:
            continue
        existing = latest.get(object_id)
        if existing is None or str(row.get("generated_at", "")) > str(existing.get("generated_at", "")):
            latest[object_id] = row
    return latest


def render_request_table(rows: list[dict[str, str]], title: str, *, include_errors: bool = True) -> str:
    lines = [
        r"\setlength{\LTleft}{0pt}",
        r"\setlength{\LTright}{0pt}",
        r"\setlength{\tabcolsep}{3.6pt}",
        r"\renewcommand{\arraystretch}{1.35}",
        r"\begin{longtable}{>{\RaggedRight\arraybackslash}p{0.34\textwidth}>{\RaggedRight\arraybackslash}p{0.12\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}}",
        r"\hline",
        r"\cellcolor{HeaderBlue}\color{white}\bfseries 事务名称 & \cellcolor{HeaderBlue}\color{white}\bfseries 平均请求时间(ms) & \cellcolor{HeaderBlue}\color{white}\bfseries 请求数 & \cellcolor{HeaderBlue}\color{white}\bfseries 错误率(\%) & \cellcolor{HeaderBlue}\color{white}\bfseries 错误次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 慢次数 \\",
        r"\hline",
        r"\endfirsthead",
        r"\hline",
        r"\cellcolor{HeaderBlue}\color{white}\bfseries 事务名称 & \cellcolor{HeaderBlue}\color{white}\bfseries 平均请求时间(ms) & \cellcolor{HeaderBlue}\color{white}\bfseries 请求数 & \cellcolor{HeaderBlue}\color{white}\bfseries 错误率(\%) & \cellcolor{HeaderBlue}\color{white}\bfseries 错误次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 慢次数 \\",
        r"\hline",
        r"\endhead",
    ]
    for row in rows:
        lines.append(
            f"{latex_escape(row.get('display_name') or row.get('canonical_name'))} & "
            f"{latex_escape(format_number(row.get('avg_rt_ms'), digits=2))} & "
            f"{latex_escape(format_number(row.get('request_count')))} & "
            f"{latex_escape(format_number(row.get('error_rate_pct'), digits=2))} & "
            f"{latex_escape(format_number(row.get('error_count')))} & "
            f"{latex_escape(format_number(row.get('slow_count')))} \\\\"
        )
        lines.append(r"\hline")
    if not rows:
        lines.append(r"\multicolumn{6}{l}{【当前批次未获取到该项数据】}\\")
        lines.append(r"\hline")
    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def render_sql_table(rows: list[dict[str, str]], *, abnormal: bool = False) -> str:
    lines = [
        r"\setlength{\LTleft}{0pt}",
        r"\setlength{\LTright}{0pt}",
        r"\setlength{\tabcolsep}{3.2pt}",
        r"\renewcommand{\arraystretch}{1.35}",
        r"\begin{longtable}{>{\RaggedRight\arraybackslash}p{0.16\textwidth}>{\RaggedRight\arraybackslash}p{0.36\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}>{\RaggedRight\arraybackslash}p{0.10\textwidth}>{\RaggedRight\arraybackslash}p{0.08\textwidth}>{\RaggedRight\arraybackslash}p{0.08\textwidth}}",
        r"\hline",
        r"\cellcolor{HeaderBlue}\color{white}\bfseries 对象提示 & \cellcolor{HeaderBlue}\color{white}\bfseries SQL 片段 & \cellcolor{HeaderBlue}\color{white}\bfseries 平均响应(ms) & \cellcolor{HeaderBlue}\color{white}\bfseries 调用次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 慢次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 错误次数 \\",
        r"\hline",
        r"\endfirsthead",
        r"\hline",
        r"\cellcolor{HeaderBlue}\color{white}\bfseries 对象提示 & \cellcolor{HeaderBlue}\color{white}\bfseries SQL 片段 & \cellcolor{HeaderBlue}\color{white}\bfseries 平均响应(ms) & \cellcolor{HeaderBlue}\color{white}\bfseries 调用次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 慢次数 & \cellcolor{HeaderBlue}\color{white}\bfseries 错误次数 \\",
        r"\hline",
        r"\endhead",
    ]
    for row in rows:
        sql_text = str(row.get("representative_sql") or "")[:160]
        lines.append(
            f"{latex_escape(row.get('query_object_hint') or row.get('source_db_name'))} & "
            f"{latex_escape(sql_text)} & "
            f"{latex_escape(format_number(row.get('avg_rt_ms')))} & "
            f"{latex_escape(format_number(row.get('exec_count')))} & "
            f"{latex_escape(format_number(row.get('slow_count')))} & "
            f"{latex_escape(format_number(row.get('error_count')))} \\\\"
        )
        lines.append(r"\hline")
    if not rows:
        placeholder = "【当前批次未获取到异常SQL主表数据】" if abnormal else "【当前批次未获取到慢SQL主表数据】"
        lines.append(rf"\multicolumn{{6}}{{l}}{{{placeholder}}}\\")
        lines.append(r"\hline")
    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def render_focus_request(row: dict[str, str], evidence: dict[str, str] | None, deep_dive: dict[str, str] | None) -> str:
    name = latex_escape(row.get("display_name") or row.get("canonical_name"))
    lines = [
        rf"\vspace{{0.35em}}\noindent{{\color{{InterfaceBlue}}\bfseries\fontsize{{11pt}}{{13.2pt}}\selectfont {name}}}\par",
        "",
        rf"\noindent\textbf{{关键数据：}}请求 {latex_escape(format_number(row.get('request_count')))}，平均 {latex_escape(format_number(row.get('avg_rt_ms'), digits=2))}ms，错误 {latex_escape(format_number(row.get('error_count')))}，错误率 {latex_escape(format_number(row.get('error_rate_pct'), digits=2))}\%，慢次数 {latex_escape(format_number(row.get('slow_count')))}\par",
        "",
        rf"\noindent\textbf{{判断：}}当前条目来自 request\_master 主表，已进入主线对象；后续结论应继续以主表和证据索引为准。\par",
        "",
    ]
    if deep_dive:
        lines.append(
            rf"\noindent\textbf{{【现状】}} 已存在 deep-dive 结果：`{latex_escape(deep_dive.get('deep_dive_id'))}`，类型为 `{latex_escape(deep_dive.get('deep_dive_kind'))}`，摘要为 `{latex_escape(deep_dive.get('summary'))}`；证据数 {latex_escape(format_number(deep_dive.get('evidence_count')))}，页面链接 {latex_escape(format_number(deep_dive.get('page_link_count')))}。\par"
        )
    elif evidence:
        lines.append(
            rf"\noindent\textbf{{【现状】}} 当前已挂接证据状态 `{latex_escape(evidence.get('evidence_status'))}`，页面链接 {latex_escape(format_number(evidence.get('page_link_count')))}，trace 线索 {latex_escape(format_number(evidence.get('trace_link_count')))}，截图提示状态 `{latex_escape(evidence.get('screenshot_hint_status'))}`。\par"
        )
    else:
        lines.append(r"\noindent\textbf{【现状】} 【暂无充分证据支撑该判断】\par")
    return "\n".join(lines)


def render_focus_sql(row: dict[str, str], evidence: dict[str, str] | None, deep_dive: dict[str, str] | None) -> str:
    title = latex_escape(row.get("query_object_hint") or row.get("source_db_name") or row.get("object_id"))
    sql_text = latex_escape(str(row.get("representative_sql") or "")[:220])
    lines = [
        rf"\vspace{{0.35em}}\noindent{{\color{{InterfaceBlue}}\bfseries\fontsize{{11pt}}{{13.2pt}}\selectfont {title}}}\par",
        "",
        rf"\noindent\textbf{{关键数据：}}平均 {latex_escape(format_number(row.get('avg_rt_ms')))}ms，响应总时间 {latex_escape(format_number(row.get('total_time_ms')))}ms，调用次数 {latex_escape(format_number(row.get('exec_count')))}，错误 {latex_escape(format_number(row.get('error_count')))}。\par",
        "",
        rf"\noindent\textbf{{SQL 片段：}} {sql_text}\par",
        "",
    ]
    if deep_dive:
        lines.append(
            rf"\noindent\textbf{{【现状】}} 已存在 SQL deep-dive：`{latex_escape(deep_dive.get('deep_dive_id'))}`，摘要 `{latex_escape(deep_dive.get('summary'))}`，证据数 {latex_escape(format_number(deep_dive.get('evidence_count')))}，页面链接 {latex_escape(format_number(deep_dive.get('page_link_count')))}。\par"
        )
    elif evidence:
        lines.append(
            rf"\noindent\textbf{{【现状】}} 当前证据状态为 `{latex_escape(evidence.get('evidence_status'))}`，页面链接 {latex_escape(format_number(evidence.get('page_link_count')))}；如需进一步定位调用者，应继续补 deep-dive。\par"
        )
    else:
        lines.append(r"\noindent\textbf{【现状】} 【待补充】\par")
    return "\n".join(lines)


def chapter_1_tex(config: dict[str, Any], export_summary: dict[str, Any], preparation_summary: dict[str, Any], materialization_summary: dict[str, Any]) -> str:
    registry_count = len((export_summary.get("exports") or []))
    prepared_counts = preparation_summary.get("row_counts") or {}
    master_counts = materialization_summary.get("row_counts") or {}
    return "\n".join(
        [
            r"\SectionTitle{1概述}",
            "",
            rf"本次测试基于批次 `{latex_escape(config.get('batch_key'))}` 的现有 diagnostics 资产进行第三阶段单模板渲染验证，未重新复制 diagnostics，也未引入新的重型输入层。\par",
            "",
            r"\SubsectionTitle{1.1巡检对象与时间范围}",
            "",
            r"\begin{center}",
            r"\setlength{\tabcolsep}{4pt}",
            r"\renewcommand{\arraystretch}{1.6}",
            r"\begin{tabular}{>{\RaggedRight\arraybackslash}p{0.25\textwidth}>{\RaggedRight\arraybackslash}p{0.58\textwidth}}",
            r"\hline",
            r"\cellcolor{HeaderBlue}\color{white}\bfseries 项目 & \cellcolor{HeaderBlue}\color{white}\bfseries 内容 \\",
            r"\hline",
            rf"巡检对象 & {latex_escape(config.get('system_key'))} \\",
            r"\hline",
            r"统计时间范围 & 2026-01-01 00:00 至 2026-03-31 23:59 \\",
            r"\hline",
            rf"报告标题 & {latex_escape(config.get('report_title'))} \\",
            r"\hline",
            r"主要分析对象 & 接口主表、SQL主表、证据索引、deep-dive bundles \\",
            r"\hline",
            r"\end{tabular}",
            r"\end{center}",
            "",
            r"\SubsectionTitle{1.2证据来源与分析口径}",
            "",
            rf"本次生成直接读取同批次 `diagnostics/`：原始导出登记 {registry_count} 项，prepared 行数包括 request={latex_escape(prepared_counts.get('request'))}、interface\_cluster={latex_escape(prepared_counts.get('interface_cluster'))}、sql={latex_escape(prepared_counts.get('sql'))}；当前主表行数包括 request\_master={latex_escape(master_counts.get('request_master'))}、interface\_cluster\_master={latex_escape(master_counts.get('interface_cluster_master'))}、sql\_master={latex_escape(master_counts.get('sql_master'))}。\par",
            "",
            r"如果某章节所需资产不存在，本轮测试会输出固定占位而不是臆造判断。\par",
            "",
        ]
    )


def chapter_2_1_tex(preparation_summary: dict[str, Any], materialization_summary: dict[str, Any]) -> tuple[str, list[str]]:
    warnings = preparation_summary.get("warnings") or []
    master_counts = materialization_summary.get("row_counts") or {}
    missing: list[str] = []
    if not warnings:
        missing.append("2.1 缺少主机级部署与端口明细，只能基于 diagnostics 摘要占位。")
    else:
        missing.append("2.1 缺少主机级部署与端口明细，当前仅能说明 prepared/master 摘要和批次 warning。")
    text = "\n".join(
        [
            r"\SectionTitle{2系统运行现状与性能问题分析}",
            "",
            r"\SubsectionTitle{2.1 部署架构与运行环境概况}",
            "",
            r"\SubsubsectionTitle{2.1.1 系统规模总览}",
            "",
            rf"当前 diagnostics 中已经可直接读取的结构化资产包括 request\_master={latex_escape(master_counts.get('request_master'))}、interface\_cluster\_master={latex_escape(master_counts.get('interface_cluster_master'))}、sql\_master={latex_escape(master_counts.get('sql_master'))}、nosql\_master={latex_escape(master_counts.get('nosql_master'))}。\par",
            "",
            r"\SubsubsectionTitle{2.1.2 服务器资源与主机分布}",
            "",
            r"【当前批次未获取到该项数据】当前 diagnostics 下没有完整的主机级 CPU/内存/磁盘清单，本章节暂保留占位。\par",
            "",
            r"\SubsubsectionTitle{2.1.3服务与端口部署情况}",
            "",
            r"【当前批次未获取到该项数据】当前第三阶段测试没有额外复制主机部署信息，只保留直接从 diagnostics 可见的资产摘要。\par",
            "",
        ]
    )
    if warnings:
        text += "\n" + rf"补充说明：prepared 阶段 warning 为 `{latex_escape('；'.join(str(w) for w in warnings))}`。\par" + "\n"
    return text, missing


def chapter_2_2_tex(
    request_rows: list[dict[str, str]],
    request_evidence: dict[str, dict[str, str]],
    deep_dive_map: dict[str, dict[str, str]],
) -> tuple[str, list[str], dict[str, Any]]:
    slow_rows = top_rows(request_rows, "avg_rt_ms", limit=8)
    focus_rows = top_rows(request_rows, "total_time_ms", limit=4)
    error_rows = top_rows(request_rows, "error_rate_pct", limit=8, positive_only=True)
    high_error_focus = top_rows(request_rows, "error_count", limit=4, positive_only=True)
    lines = [
        r"\SubsectionTitle{2.2 系统接口检查}",
        "",
        r"本章节优先读取 request\_master.csv 与 request\_evidence\_index.csv，并在存在 deep-dive 时补充其摘要，不绕过主表主线。\par",
        "",
        r"\SubsubsectionTitle{2.2.1 平均响应时间高的慢接口}",
        "",
        render_request_table(slow_rows, "2.2.1"),
        "",
        r"\SubsubsectionTitle{2.2.2 访问量高\&响应时间差的重点接口(重点)}",
        "",
    ]
    for row in focus_rows:
        lines.extend(["", render_focus_request(row, request_evidence.get(row.get("object_id", "")), deep_dive_map.get(row.get("object_id", "")))])
    lines.extend(
        [
            "",
            r"\SubsubsectionTitle{2.2.3 平均错误率高的异常接口}",
            "",
            render_request_table(error_rows, "2.2.3"),
            "",
            r"\SubsubsectionTitle{2.2.4 访问量高\&错误率高的重点接口(重点)}",
            "",
        ]
    )
    for row in high_error_focus:
        lines.extend(["", render_focus_request(row, request_evidence.get(row.get("object_id", "")), deep_dive_map.get(row.get("object_id", "")))])

    missing = []
    if not error_rows:
        missing.append("2.2.3 当前主表中没有 error_rate_pct > 0 的对象，异常接口章节只能占位。")
    chapter_inputs = {
        "request_master_rows": len(request_rows),
        "request_evidence_rows": len(request_evidence),
        "deep_dive_hits": sum(1 for row in request_rows if row.get("object_id", "") in deep_dive_map),
    }
    return "\n".join(lines) + "\n", missing, chapter_inputs


def chapter_2_3_tex(
    sql_rows: list[dict[str, str]],
    sql_evidence: dict[str, dict[str, str]],
    deep_dive_map: dict[str, dict[str, str]],
) -> tuple[str, list[str], dict[str, Any]]:
    slow_rows = top_rows(sql_rows, "total_time_ms", limit=10)
    abnormal_rows = top_rows([row for row in sql_rows if parse_float(row.get("error_count")) > 0], "error_count", limit=10)
    focus_rows = top_rows(sql_rows, "total_time_ms", limit=3)
    core_db = slow_rows[0].get("source_db_name") if slow_rows else "【待补充】"
    lines = [
        r"\SubsectionTitle{2.3 系统SQL检查}",
        "",
        r"本章节优先读取 sql\_master.csv、sql\_evidence\_index.csv 与 04\_deep\_dive/sql/，原始导出只作为补充。\par",
        "",
        r"\SubsubsectionTitle{2.3.1 系统数据库整体检查}",
        "",
        r"\begin{center}",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.6}",
        r"\begin{tabular}{>{\Centering\arraybackslash}p{0.26\textwidth}>{\Centering\arraybackslash}p{0.56\textwidth}}",
        r"\hline",
        rf"\cellcolor{{HeaderBlue}}\color{{white}}\bfseries 核心数据库实例 & \cellcolor{{HeaderBlue}}\color{{white}}\bfseries {latex_escape(core_db)} \\",
        r"\hline",
        rf"\cellcolor{{HeaderBlue}}\color{{white}}\bfseries 已入主表 SQL 数 & {latex_escape(format_number(len(sql_rows)))} \\",
        r"\hline",
        rf"\cellcolor{{HeaderBlue}}\color{{white}}\bfseries 已挂接 deep-dive 的 SQL 数 & {latex_escape(format_number(sum(1 for row in sql_rows if row.get('object_id', '') in deep_dive_map)))} \\",
        r"\hline",
        r"\cellcolor{HeaderBlue}\color{white}\bfseries 连接池明细 & 【当前批次未直接沉淀到 diagnostics 中，待补充】 \\",
        r"\hline",
        r"\end{tabular}",
        r"\end{center}",
        "",
        r"\SubsubsectionTitle{2.3.2 慢SQL检查}",
        "",
        render_sql_table(slow_rows, abnormal=False),
        "",
    ]
    for row in focus_rows:
        lines.extend(["", render_focus_sql(row, sql_evidence.get(row.get("object_id", "")), deep_dive_map.get(row.get("object_id", "")))])
    lines.extend(
        [
            "",
            r"\SubsubsectionTitle{2.3.3 异常SQL检查}",
            "",
            render_sql_table(abnormal_rows, abnormal=True),
            "",
        ]
    )
    missing = []
    if not abnormal_rows:
        missing.append("2.3.3 当前 sql_master 中没有 error_count > 0 的条目，异常 SQL 章节只能占位。")
    missing.append("2.3.1 连接池详细指标尚未直接注入第三阶段上下文。")
    chapter_inputs = {
        "sql_master_rows": len(sql_rows),
        "sql_evidence_rows": len(sql_evidence),
        "sql_deep_dive_hits": sum(1 for row in sql_rows if row.get("object_id", "") in deep_dive_map),
    }
    return "\n".join(lines) + "\n", missing, chapter_inputs


def chapter_3_tex(request_rows: list[dict[str, str]], sql_rows: list[dict[str, str]], deep_dive_rows: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            r"\SectionTitle{3 结论}",
            "",
            rf"本次第三阶段最小闭环测试已直接读取 request 主表 {latex_escape(format_number(len(request_rows)))} 行、sql 主表 {latex_escape(format_number(len(sql_rows)))} 行，以及 deep-dive 注册表 {latex_escape(format_number(len(deep_dive_rows)))} 行。\par",
            "",
            r"当前已经能够稳定产出章节骨架、主表驱动的接口/SQL章节以及缺失项报告；但对主机部署信息、连接池明细和最终高质量正文组织，仍需下一轮继续补充。\par",
            "",
        ]
    )


def write_missing_data_report(path: Path, chapter_statuses: list[dict[str, Any]], missing_items: list[str], compile_status: dict[str, Any]) -> None:
    lines = ["# Missing Data Report", ""]
    lines.append("## 章节状态")
    lines.append("")
    for item in chapter_statuses:
        lines.append(f"- `{item['chapter']}`: `{item['status']}`")
        lines.append(f"  - {item['note']}")
    lines.append("")
    lines.append("## 缺失项")
    lines.append("")
    if missing_items:
        for item in missing_items:
            lines.append(f"- {item}")
    else:
        lines.append("- 无显式缺失项。")
    lines.append("")
    lines.append("## 编译状态")
    lines.append("")
    lines.append(f"- compiled: `{compile_status.get('compiled')}`")
    lines.append(f"- reason: {compile_status.get('reason')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def try_compile_xelatex(output_root: Path, tex_path: Path) -> dict[str, Any]:
    xelatex = shutil.which("xelatex")
    if not xelatex:
        return {"compiled": False, "reason": "xelatex not available in current environment"}
    proc = subprocess.run(
        [xelatex, "-interaction=nonstopmode", tex_path.name],
        cwd=output_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return {
        "compiled": proc.returncode == 0,
        "reason": "ok" if proc.returncode == 0 else f"xelatex exited with code {proc.returncode}",
        "log_excerpt": proc.stdout[-2000:],
    }


def render_instance(config_path: Path) -> dict[str, Any]:
    repo_root = find_repo_root(config_path.resolve())
    config = load_minimal_yaml(config_path)
    report_type_id = str(config.get("report_type_id", "")).strip()
    if not report_type_id:
        raise ValueError("report_type_id is required")

    diagnostics_root = resolve_repo_path(repo_root, str(config.get("diagnostics_root", "")))
    template_root = resolve_repo_path(repo_root, str(config.get("template_root", "")))
    reports_root = resolve_repo_path(repo_root, str(config.get("reports_root", "")))
    generated_root = resolve_repo_path(repo_root, str(config.get("generated_root", "")))
    output_root = resolve_repo_path(repo_root, str(config.get("output_root", "")))
    assets_root = resolve_repo_path(repo_root, str(config.get("assets_root", "")))
    chapters_root = generated_root / "chapters"

    for folder in (reports_root, generated_root, output_root, assets_root, chapters_root):
        ensure_dir(folder)

    spec = load_minimal_yaml(template_root / "spec.yaml")
    if not spec.get("direct_read_mode", False):
        raise ValueError(f"{template_root / 'spec.yaml'} does not enable direct_read_mode")

    required_assets = collect_asset_status(diagnostics_root, list(spec.get("required_assets") or []))
    optional_assets = collect_asset_status(diagnostics_root, list(spec.get("optional_assets") or []))
    missing_required = [item for item in required_assets if not item["exists"]]
    missing_required_notes = [f"required asset missing: {item['relative_path']}" for item in missing_required]

    request_rows = read_csv_rows(diagnostics_root / "02_master_tables/request_master.csv")
    sql_rows = read_csv_rows(diagnostics_root / "02_master_tables/sql_master.csv")
    interface_cluster_rows = read_csv_rows(diagnostics_root / "02_master_tables/interface_cluster_master.csv") if (diagnostics_root / "02_master_tables/interface_cluster_master.csv").exists() else []
    request_evidence_rows = read_csv_rows(diagnostics_root / "03_evidence_indexes/request_evidence_index.csv")
    sql_evidence_rows = read_csv_rows(diagnostics_root / "03_evidence_indexes/sql_evidence_index.csv")
    interface_cluster_evidence_rows = read_csv_rows(diagnostics_root / "03_evidence_indexes/interface_cluster_evidence_index.csv") if (diagnostics_root / "03_evidence_indexes/interface_cluster_evidence_index.csv").exists() else []
    deep_dive_rows = read_csv_rows(diagnostics_root / "04_deep_dive/deep_dive_registry.csv")
    export_summary = read_json(diagnostics_root / "00_raw_exports/export_registry.json")
    preparation_summary = read_json(diagnostics_root / "01_prepared_tables/preparation_summary.json")
    materialization_summary = read_json(diagnostics_root / "02_master_tables/materialization_summary.json")

    request_evidence_map = build_object_map(request_evidence_rows)
    sql_evidence_map = build_object_map(sql_evidence_rows)
    interface_cluster_evidence_map = build_object_map(interface_cluster_evidence_rows)
    deep_dive_map = build_latest_deep_dive_map(deep_dive_rows)

    chapter_1 = chapter_1_tex(config, export_summary, preparation_summary, materialization_summary)
    chapter_2_1, missing_2_1 = chapter_2_1_tex(preparation_summary, materialization_summary)
    chapter_2_2, missing_2_2, chapter_2_2_inputs = chapter_2_2_tex(request_rows, request_evidence_map, deep_dive_map)
    chapter_2_3, missing_2_3, chapter_2_3_inputs = chapter_2_3_tex(sql_rows, sql_evidence_map, deep_dive_map)
    chapter_3 = chapter_3_tex(request_rows, sql_rows, deep_dive_rows)

    chapter_files = {
        "chapter_1.tex": chapter_1,
        "chapter_2_1.tex": chapter_2_1,
        "chapter_2_2.tex": chapter_2_2,
        "chapter_2_3.tex": chapter_2_3,
        "chapter_3.tex": chapter_3,
    }
    for name, content in chapter_files.items():
        (chapters_root / name).write_text(content, encoding="utf-8")

    context = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type_id": report_type_id,
        "report_type_name": spec.get("report_type_name", report_type_id),
        "report_title": config.get("report_title", ""),
        "report_date": config.get("report_date", ""),
        "language": config.get("language", "zh-CN"),
        "path_mode": config.get("path_mode", "repo_relative"),
        "direct_read_mode": bool(spec.get("direct_read_mode", False)),
        "resolved_paths": {
            "repo_root": str(repo_root),
            "config_path": str(config_path),
            "diagnostics_root": str(diagnostics_root),
            "template_root": str(template_root),
            "reports_root": str(reports_root),
            "generated_root": str(generated_root),
            "chapters_root": str(chapters_root),
            "output_root": str(output_root),
            "assets_root": str(assets_root),
        },
        "diagnostics_reads": [
            "00_raw_exports/export_registry.json",
            "01_prepared_tables/preparation_summary.json",
            "02_master_tables/request_master.csv",
            "02_master_tables/sql_master.csv",
            "02_master_tables/interface_cluster_master.csv",
            "02_master_tables/materialization_summary.json",
            "03_evidence_indexes/request_evidence_index.csv",
            "03_evidence_indexes/sql_evidence_index.csv",
            "03_evidence_indexes/interface_cluster_evidence_index.csv",
            "04_deep_dive/deep_dive_registry.csv",
        ],
        "diagnostics_assets": {
            "required": required_assets,
            "optional": optional_assets,
            "missing_required_count": len(missing_required),
        },
        "chapter_outline": build_chapter_outline(spec),
        "chapter_inputs": {
            "chapter_1": {
                "assets": ["00_raw_exports/export_registry.json", "01_prepared_tables/preparation_summary.json", "02_master_tables/materialization_summary.json"],
                "status": "filled",
            },
            "chapter_2_1": {
                "assets": ["01_prepared_tables/preparation_summary.json", "02_master_tables/materialization_summary.json"],
                "status": "partial",
            },
            "chapter_2_2": {
                "assets": ["02_master_tables/request_master.csv", "03_evidence_indexes/request_evidence_index.csv", "04_deep_dive/deep_dive_registry.csv"],
                "status": "filled",
                "summary": chapter_2_2_inputs,
            },
            "chapter_2_3": {
                "assets": ["02_master_tables/sql_master.csv", "03_evidence_indexes/sql_evidence_index.csv", "04_deep_dive/deep_dive_registry.csv"],
                "status": "filled",
                "summary": chapter_2_3_inputs,
            },
            "chapter_3": {
                "assets": ["02_master_tables/request_master.csv", "02_master_tables/sql_master.csv", "04_deep_dive/deep_dive_registry.csv"],
                "status": "partial",
            },
        },
        "missing_items": missing_required_notes + missing_2_1 + missing_2_2 + missing_2_3,
        "rendering_rules": spec.get("rendering_rules", {}),
        "missing_data_policy": spec.get("missing_data_policy", {}),
        "notes": config.get("notes", []),
    }

    (generated_root / "report_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (generated_root / "asset_index_stub.json").write_text(
        json.dumps(
            {
                "generated_at": context["generated_at"],
                "assets_root": str(assets_root),
                "items": [],
                "note": "Stage 3 renderer currently creates an asset index stub and expects screenshots/attachments to be added in the instance assets directory.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (generated_root / "chapter_stubs.json").write_text(
        json.dumps(
            {
                "generated_at": context["generated_at"],
                "report_type_id": report_type_id,
                "chapters": [
                    {
                        "chapter_id": item["chapter_id"],
                        "title": item["title"],
                        "status": "template_stub",
                    }
                    for item in context["chapter_outline"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assembled_generated = assemble_main_tex(template_root, chapters_root, generated_root)
    (generated_root / "assembled_main.tex").write_text(
        assembled_generated,
        encoding="utf-8",
    )
    output_tex_path = output_root / f"{report_type_id}.tex"
    output_tex_path.write_text(
        assemble_main_tex(template_root, chapters_root, output_root),
        encoding="utf-8",
    )
    compile_status = try_compile_xelatex(output_root, output_tex_path)
    (output_root / "build_status.json").write_text(json.dumps(compile_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chapter_statuses = [
        {"chapter": "chapter_1", "status": "filled", "note": "概述与证据来源已按当前 diagnostics 摘要填充。"},
        {"chapter": "chapter_2_1", "status": "partial", "note": "仅基于 preparation/materialization 摘要填充，主机级部署信息仍占位。"},
        {"chapter": "chapter_2_2", "status": "filled", "note": "接口主表、证据索引和 request deep-dive 已接入。"},
        {"chapter": "chapter_2_3", "status": "filled", "note": "SQL 主表、证据索引和 sql deep-dive 已接入。"},
        {"chapter": "chapter_3", "status": "partial", "note": "结论已生成，但仍是测试轮次的收敛摘要。"},
    ]
    write_missing_data_report(generated_root / "missing_data_report.md", chapter_statuses, context["missing_items"], compile_status)
    return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a stage-3 report instance skeleton directly from diagnostics assets.")
    parser.add_argument("--config", required=True, help="Path to report_config.yaml")
    args = parser.parse_args(argv)
    config_path = Path(args.config).resolve()
    try:
        context = render_instance(config_path)
    except Exception as exc:
        print(f"[stage3-renderer] failed: {exc}", file=sys.stderr)
        return 1

    print("[stage3-renderer] rendered minimal report skeleton")
    print(f"report_type_id={context['report_type_id']}")
    print(f"diagnostics_root={context['resolved_paths']['diagnostics_root']}")
    print(f"generated_root={context['resolved_paths']['generated_root']}")
    print(f"missing_required_assets={context['diagnostics_assets']['missing_required_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

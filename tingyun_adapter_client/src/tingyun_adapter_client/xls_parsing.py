from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import xlrd


HEADER_ALIASES = {
    "sql_text": [
        "sql",
        "sql文本",
        "命令",
        "操作",
        "opname",
        "op_name",
    ],
    "avg_rt_ms": [
        "平均响应时间(ms)",
        "平均响应时间（ms）",
        "平均响应时间",
    ],
    "total_time_ms": [
        "响应总时间(ms)",
        "响应总时间（ms）",
        "响应总时间",
        "总耗时(ms)",
        "总耗时",
    ],
    "qps": [
        "吞吐率(qps)",
        "吞吐率（qps）",
        "吞吐率(tps)",
        "吞吐率（tps）",
        "吞吐率",
    ],
    "exec_count": [
        "sql执行次数",
        "执行次数",
        "请求数",
        "次数",
    ],
    "error_count": [
        "错误次数",
        "错误数",
    ],
    "slow_count": [
        "慢次数",
        "慢调用次数",
    ],
}


@dataclass
class ParsedXlsResult:
    rows: list[dict[str, Any]]
    warnings: list[str]


def parse_component_operation_xls(path: Path, *, kind: str) -> ParsedXlsResult:
    warnings: list[str] = []
    workbook = xlrd.open_workbook(path)
    sheet = _choose_sheet(workbook)
    if sheet is None:
        return ParsedXlsResult(rows=[], warnings=[f"{path.name} does not contain a readable worksheet."])

    header_row_idx, header_map = _find_header_row(sheet)
    if header_row_idx is None or not header_map.get("sql_text"):
        return ParsedXlsResult(rows=[], warnings=[f"{path.name} does not contain the expected SQL/NoSQL headers for xlrd parsing."])

    rows: list[dict[str, Any]] = []
    skipped_noise = 0
    skipped_empty = 0
    for row_idx in range(header_row_idx + 1, sheet.nrows):
        parsed = _parse_sheet_row(sheet, row_idx, header_map, kind=kind)
        if parsed is None:
            skipped_empty += 1
            continue
        if parsed == "__noise__":
            skipped_noise += 1
            continue
        rows.append(parsed)

    if skipped_noise:
        warnings.append(f"{path.name} skipped {skipped_noise} noise rows during xlrd parsing.")
    if not rows:
        warnings.append(f"{path.name} produced no structured rows after xlrd parsing.")
    return ParsedXlsResult(rows=rows, warnings=warnings)


def _choose_sheet(workbook: xlrd.book.Book) -> Any | None:
    for index in range(workbook.nsheets):
        sheet = workbook.sheet_by_index(index)
        if sheet.nrows > 0 and sheet.ncols > 0:
            return sheet
    return None


def _find_header_row(sheet: Any) -> tuple[int | None, dict[str, int]]:
    best_row_idx: int | None = None
    best_map: dict[str, int] = {}
    best_score = -1
    for row_idx in range(min(sheet.nrows, 12)):
        current_map: dict[str, int] = {}
        for col_idx in range(sheet.ncols):
            normalized = _normalize_header(sheet.cell_value(row_idx, col_idx))
            if not normalized:
                continue
            for target, aliases in HEADER_ALIASES.items():
                if target in current_map:
                    continue
                if normalized in aliases:
                    current_map[target] = col_idx
                    break
        score = len(current_map)
        if score > best_score:
            best_score = score
            best_row_idx = row_idx
            best_map = current_map
    if best_score < 3:
        return None, {}
    return best_row_idx, best_map


def _parse_sheet_row(sheet: Any, row_idx: int, header_map: dict[str, int], *, kind: str) -> dict[str, Any] | str | None:
    text = _string_cell(sheet, row_idx, header_map.get("sql_text"))
    if not text:
        return None
    if text in {"SQL", "SQL文本", "命令"}:
        return None
    if kind == "sql":
        if not _looks_like_sql_statement(text):
            return "__noise__"
    else:
        if not _looks_like_nosql_command(text):
            return "__noise__"

    return {
        "representative_sql": text,
        "representative_command": text,
        "avg_rt_ms": _number_cell(sheet, row_idx, header_map.get("avg_rt_ms")),
        "total_time_ms": _number_cell(sheet, row_idx, header_map.get("total_time_ms")),
        "qps": _number_cell(sheet, row_idx, header_map.get("qps")),
        "exec_count": _number_cell(sheet, row_idx, header_map.get("exec_count")),
        "error_count": _number_cell(sheet, row_idx, header_map.get("error_count")),
        "slow_count": _number_cell(sheet, row_idx, header_map.get("slow_count")),
        "parse_mode": "xls_xlrd",
    }


def _normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace(" ", "")
    return text


def _string_cell(sheet: Any, row_idx: int, col_idx: int | None) -> str:
    if col_idx is None:
        return ""
    value = sheet.cell_value(row_idx, col_idx)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value or "").strip()


def _number_cell(sheet: Any, row_idx: int, col_idx: int | None) -> float | None:
    if col_idx is None:
        return None
    value = sheet.cell_value(row_idx, col_idx)
    if value in {"", None}:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _looks_like_sql_statement(text: str) -> bool:
    upper = text.upper().strip()
    return upper.startswith(("SELECT ", "UPDATE ", "INSERT ", "DELETE ", "WITH "))


def _looks_like_nosql_command(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned or len(cleaned) > 120:
        return False
    if " " in cleaned or "(" in cleaned or ")" in cleaned:
        return False
    return cleaned.upper() == cleaned and any(ch.isalpha() for ch in cleaned)

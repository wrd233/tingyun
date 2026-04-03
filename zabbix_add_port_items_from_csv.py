#!/usr/bin/env python3
"""
Read a Zabbix exported hosts YAML file and a CSV file, then add missing
`net.tcp.listen[PORT]` items and triggers to matched hosts while preserving
the original YAML formatting as much as possible.

CSV columns:
  1. Server IP
  2. Critical application ports
  3. Critical application processes
  4. Monitoring URL

Usage:
  python3 zabbix_add_port_items_from_csv.py \
    --hosts-yaml hosts.yaml \
    --csv-file ports.csv \
    --output hosts.updated.yaml \
    --error-file zabbix_port_item_errors.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PORT_SPLIT_RE = re.compile(r"[、,;，/\s]+")
HOST_START_RE = re.compile(r"^    - host:\s*(.*?)\s*$")
TOP_LEVEL_SECTION_RE = re.compile(r"^  [^ ].*:\s*(?:#.*)?$")
PROPERTY_RE_TEMPLATE = r"^      {name}:\s*(?:.*)?$"
ITEM_START_RE = re.compile(r"^        - ")
KEY_LINE_RE = re.compile(r"^          key:\s*(.*?)\s*$")
TRIGGERS_LINE_RE = re.compile(r"^          triggers:\s*(?:.*)?$")
TRIGGER_EXPR_RE = re.compile(r"^            - expression:\s*(.*?)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add missing net.tcp.listen[port] items to Zabbix exported YAML."
    )
    parser.add_argument(
        "--hosts-yaml",
        required=True,
        help="Path to exported Zabbix hosts YAML file",
    )
    parser.add_argument(
        "--csv-file",
        required=True,
        help="Path to CSV file",
    )
    parser.add_argument(
        "--output",
        default="hosts.with_port_items.yaml",
        help="Output YAML file path, default: hosts.with_port_items.yaml",
    )
    parser.add_argument(
        "--error-file",
        default="zabbix_port_item_errors.txt",
        help="Error report file path, default: zabbix_port_item_errors.txt",
    )
    return parser.parse_args()


def load_yaml_with_python(path: Path) -> dict[str, Any]:
    import yaml  # type: ignore

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("YAML root is not a mapping.")
    return data


def load_yaml_with_ruby(path: Path) -> dict[str, Any]:
    cmd = [
        "ruby",
        "-ryaml",
        "-rjson",
        "-e",
        "data = YAML.load_file(ARGV[0]); puts JSON.generate(data)",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Ruby YAML load failed.")
    data = json.loads(proc.stdout)
    if not isinstance(data, dict):
        raise ValueError("YAML root is not a mapping.")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        return load_yaml_with_python(path)
    except ModuleNotFoundError:
        return load_yaml_with_ruby(path)


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def parse_ports(raw_value: str) -> tuple[list[str], list[str]]:
    value = normalize_text(raw_value)
    if not value or value in {"无", "none", "None", "NULL", "null", "-"}:
        return [], []

    valid_ports: list[str] = []
    invalid_tokens: list[str] = []

    for token in PORT_SPLIT_RE.split(value):
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            valid_ports.append(token)
        else:
            invalid_tokens.append(token)

    return list(dict.fromkeys(valid_ports)), list(dict.fromkeys(invalid_tokens))


def read_csv_mapping(csv_file: Path) -> tuple[dict[str, set[str]], list[str], int]:
    ip_to_ports: dict[str, set[str]] = {}
    report_lines: list[str] = []
    row_count = 0

    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row_number, row in enumerate(reader, start=1):
            row_count += 1
            row = list(row)
            if len(row) < 4:
                row.extend([""] * (4 - len(row)))

            ip = normalize_text(row[0])
            raw_ports = row[1]

            if not ip:
                report_lines.append(f"ROW {row_number}: missing IP, skipped.")
                continue

            ports, invalid_tokens = parse_ports(raw_ports)
            if invalid_tokens:
                report_lines.append(
                    f"ROW {row_number}: ip={ip} has non-numeric port tokens: {', '.join(invalid_tokens)}"
                )

            if not ports:
                continue

            ip_to_ports.setdefault(ip, set()).update(ports)

    return ip_to_ports, report_lines, row_count


def get_hosts_root(data: dict[str, Any]) -> list[dict[str, Any]]:
    export_root = data.get("zabbix_export")
    if not isinstance(export_root, dict):
        raise ValueError("YAML does not contain 'zabbix_export'.")

    hosts = export_root.get("hosts")
    if not isinstance(hosts, list):
        raise ValueError("YAML does not contain a valid 'zabbix_export.hosts' list.")

    valid_hosts: list[dict[str, Any]] = []
    for host in hosts:
        if isinstance(host, dict):
            valid_hosts.append(host)
    return valid_hosts


def add_host_mapping(mapping: dict[str, list[dict[str, Any]]], key: str, host: dict[str, Any]) -> None:
    key = normalize_text(key)
    if not key:
        return

    existing = mapping.setdefault(key, [])
    if host not in existing:
        existing.append(host)


def build_host_index(hosts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}

    for host in hosts:
        add_host_mapping(mapping, str(host.get("host", "")), host)
        add_host_mapping(mapping, str(host.get("name", "")), host)

        interfaces = host.get("interfaces", [])
        if isinstance(interfaces, list):
            for interface in interfaces:
                if not isinstance(interface, dict):
                    continue
                add_host_mapping(mapping, str(interface.get("ip", "")), host)

    return mapping


def choose_interface_ref(host: dict[str, Any], target_ip: str) -> str | None:
    interfaces = host.get("interfaces", [])
    if not isinstance(interfaces, list):
        return None

    for interface in interfaces:
        if not isinstance(interface, dict):
            continue
        if normalize_text(str(interface.get("ip", ""))) == target_ip:
            ref = normalize_text(str(interface.get("interface_ref", "")))
            if ref:
                return ref

    for interface in interfaces:
        if not isinstance(interface, dict):
            continue
        ref = normalize_text(str(interface.get("interface_ref", "")))
        if ref:
            return ref

    return None


def build_trigger_expression(host_key: str, port: str) -> str:
    return f"last(/{host_key}/net.tcp.listen[{port}])=0"


def single_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def parse_yaml_scalar(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def find_block_end(lines: list[str], start: int, end: int, parent_indent: int) -> int:
    for idx in range(start, end):
        if not lines[idx].strip():
            continue
        if line_indent(lines[idx]) <= parent_indent:
            return idx
    return end


def build_host_text_index(lines: list[str]) -> dict[str, tuple[int, int]]:
    mapping: dict[str, tuple[int, int]] = {}
    for idx, line in enumerate(lines):
        match = HOST_START_RE.match(line)
        if not match:
            continue

        host_key = parse_yaml_scalar(match.group(1))
        end = len(lines)
        for probe in range(idx + 1, len(lines)):
            if HOST_START_RE.match(lines[probe]) or TOP_LEVEL_SECTION_RE.match(lines[probe]):
                end = probe
                break
        mapping[host_key] = (idx, end)

    return mapping


def find_property_line(lines: list[str], start: int, end: int, name: str) -> int | None:
    pattern = re.compile(PROPERTY_RE_TEMPLATE.format(name=re.escape(name)))
    for idx in range(start, end):
        if pattern.match(lines[idx]):
            return idx
    return None


def find_items_range(lines: list[str], host_start: int, host_end: int) -> tuple[int, int] | None:
    items_line = find_property_line(lines, host_start, host_end, "items")
    if items_line is None:
        return None
    items_end = find_block_end(lines, items_line + 1, host_end, 6)
    return items_line, items_end


def iterate_item_ranges(lines: list[str], items_line: int, items_end: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    idx = items_line + 1
    while idx < items_end:
        if ITEM_START_RE.match(lines[idx]):
            item_end = find_block_end(lines, idx + 1, items_end, 8)
            ranges.append((idx, item_end))
            idx = item_end
            continue
        idx += 1
    return ranges


def find_item_range_by_key(
    lines: list[str], items_line: int, items_end: int, item_key: str
) -> tuple[int, int] | None:
    for item_start, item_end in iterate_item_ranges(lines, items_line, items_end):
        for idx in range(item_start, item_end):
            match = KEY_LINE_RE.match(lines[idx])
            if match and parse_yaml_scalar(match.group(1)) == item_key:
                return item_start, item_end
    return None


def find_triggers_line(lines: list[str], item_start: int, item_end: int) -> int | None:
    for idx in range(item_start, item_end):
        if TRIGGERS_LINE_RE.match(lines[idx]):
            return idx
    return None


def has_trigger_expression(lines: list[str], item_start: int, item_end: int, expression: str) -> bool:
    for idx in range(item_start, item_end):
        match = TRIGGER_EXPR_RE.match(lines[idx])
        if match and parse_yaml_scalar(match.group(1)) == expression:
            return True
    return False


def find_host_insert_index(lines: list[str], host_start: int, host_end: int) -> int:
    interfaces_line = find_property_line(lines, host_start, host_end, "interfaces")
    if interfaces_line is not None:
        return find_block_end(lines, interfaces_line + 1, host_end, 6)

    inventory_line = find_property_line(lines, host_start, host_end, "inventory_mode")
    if inventory_line is not None:
        return inventory_line

    return host_end


def render_item_lines(host_key: str, interface_ref: str, port: str) -> list[str]:
    expression = build_trigger_expression(host_key, port)
    return [
        f"        - name: port_{port}",
        f"          key: {single_quote(f'net.tcp.listen[{port}]')}",
        f"          interface_ref: {interface_ref}",
        "          triggers:",
        f"            - expression: {single_quote(expression)}",
        f"              name: port_{port}",
        "              priority: HIGH",
    ]


def render_triggers_block(host_key: str, port: str) -> list[str]:
    expression = build_trigger_expression(host_key, port)
    return [
        "          triggers:",
        f"            - expression: {single_quote(expression)}",
        f"              name: port_{port}",
        "              priority: HIGH",
    ]


def render_trigger_lines(host_key: str, port: str) -> list[str]:
    expression = build_trigger_expression(host_key, port)
    return [
        f"            - expression: {single_quote(expression)}",
        f"              name: port_{port}",
        "              priority: HIGH",
    ]


def extract_existing_items(host: dict[str, Any]) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    items = host.get("items", [])
    if not isinstance(items, list):
        return existing

    for item in items:
        if not isinstance(item, dict):
            continue
        key = normalize_text(str(item.get("key", "")))
        if key and key not in existing:
            existing[key] = item
    return existing


def extract_trigger_expressions(item: dict[str, Any]) -> set[str]:
    expressions: set[str] = set()
    triggers = item.get("triggers", [])
    if not isinstance(triggers, list):
        return expressions

    for trigger in triggers:
        if not isinstance(trigger, dict):
            continue
        expression = normalize_text(str(trigger.get("expression", "")))
        if expression:
            expressions.add(expression)
    return expressions


def write_report(path: Path, lines: list[str], summary: list[str]) -> None:
    content_lines = summary + [""] + (lines or ["No issues found."])
    path.write_text("\n".join(content_lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    hosts_yaml_path = Path(args.hosts_yaml)
    csv_path = Path(args.csv_file)
    output_path = Path(args.output)
    error_path = Path(args.error_file)

    try:
        yaml_data = load_yaml(hosts_yaml_path)
        hosts = get_hosts_root(yaml_data)
        ip_to_ports, report_lines, row_count = read_csv_mapping(csv_path)
        original_text = hosts_yaml_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    lines = original_text.splitlines()
    trailing_newline = original_text.endswith("\n")
    host_index = build_host_index(hosts)
    host_text_index = build_host_text_index(lines)

    insertions: list[tuple[int, list[str]]] = []

    added_items = 0
    added_triggers = 0
    unchanged_pairs = 0
    skipped_missing_hosts = 0
    skipped_ambiguous_hosts = 0
    skipped_missing_interface_ref = 0
    skipped_missing_host_block = 0

    for ip in sorted(ip_to_ports):
        ports = sorted(ip_to_ports[ip], key=lambda value: int(value))
        matched_hosts = host_index.get(ip, [])

        if not matched_hosts:
            report_lines.append(f"HOST NOT FOUND: ip={ip}, ports={','.join(ports)}")
            skipped_missing_hosts += 1
            continue

        if len(matched_hosts) > 1:
            host_names = ", ".join(
                normalize_text(str(host.get("host", ""))) or normalize_text(str(host.get("name", "")))
                for host in matched_hosts
            )
            report_lines.append(
                f"AMBIGUOUS HOST: ip={ip}, ports={','.join(ports)}, candidates={host_names}"
            )
            skipped_ambiguous_hosts += 1
            continue

        host = matched_hosts[0]
        host_key = normalize_text(str(host.get("host", "")))
        host_block = host_text_index.get(host_key)
        if host_block is None:
            report_lines.append(f"HOST BLOCK NOT FOUND IN YAML: ip={ip}, host={host_key}")
            skipped_missing_host_block += 1
            continue

        interface_ref = choose_interface_ref(host, ip)
        if not interface_ref:
            report_lines.append(
                f"NO INTERFACE REF: ip={ip}, host={host.get('host')}, ports={','.join(ports)}"
            )
            skipped_missing_interface_ref += 1
            continue

        host_start, host_end = host_block
        items_range = find_items_range(lines, host_start, host_end)
        existing_items = extract_existing_items(host)

        missing_item_ports: list[str] = []
        for port in ports:
            item_key = f"net.tcp.listen[{port}]"
            expression = build_trigger_expression(host_key, port)
            item = existing_items.get(item_key)

            if item is None:
                missing_item_ports.append(port)
                added_items += 1
                added_triggers += 1
                continue

            if expression in extract_trigger_expressions(item):
                unchanged_pairs += 1
                continue

            if items_range is None:
                report_lines.append(
                    f"ITEM EXISTS IN DATA BUT ITEMS BLOCK NOT FOUND IN TEXT: ip={ip}, host={host_key}, port={port}"
                )
                continue

            item_range = find_item_range_by_key(lines, items_range[0], items_range[1], item_key)
            if item_range is None:
                report_lines.append(
                    f"ITEM TEXT BLOCK NOT FOUND: ip={ip}, host={host_key}, port={port}, key={item_key}"
                )
                continue

            item_start, item_end = item_range
            if has_trigger_expression(lines, item_start, item_end, expression):
                unchanged_pairs += 1
                continue

            triggers_line = find_triggers_line(lines, item_start, item_end)
            if triggers_line is None:
                insertions.append((item_end, render_triggers_block(host_key, port)))
            else:
                triggers_end = find_block_end(lines, triggers_line + 1, item_end, 10)
                insertions.append((triggers_end, render_trigger_lines(host_key, port)))
            added_triggers += 1

        if missing_item_ports:
            rendered_items: list[str] = []
            for port in missing_item_ports:
                rendered_items.extend(render_item_lines(host_key, interface_ref, port))

            if items_range is None:
                host_insert_idx = find_host_insert_index(lines, host_start, host_end)
                insertions.append((host_insert_idx, ["      items:"] + rendered_items))
            else:
                insertions.append((items_range[1], rendered_items))

    for index, new_lines in sorted(insertions, key=lambda item: item[0], reverse=True):
        lines[index:index] = new_lines

    output_text = "\n".join(lines)
    if trailing_newline or output_text:
        output_text += "\n"

    try:
        output_path.write_text(output_text, encoding="utf-8")
    except Exception as exc:
        print(f"[ERROR] Failed to write YAML: {exc}", file=sys.stderr)
        return 1

    summary_lines = [
        f"Input YAML: {hosts_yaml_path.resolve()}",
        f"Input CSV: {csv_path.resolve()}",
        f"Output YAML: {output_path.resolve()}",
        f"CSV rows read: {row_count}",
        f"IPs with numeric ports: {len(ip_to_ports)}",
        f"Items added: {added_items}",
        f"Triggers added: {added_triggers}",
        f"Existing item+trigger unchanged: {unchanged_pairs}",
        f"Hosts not found: {skipped_missing_hosts}",
        f"Ambiguous hosts: {skipped_ambiguous_hosts}",
        f"Missing interface_ref: {skipped_missing_interface_ref}",
        f"Missing host block in YAML text: {skipped_missing_host_block}",
    ]
    write_report(error_path, report_lines, summary_lines)

    print(f"Updated YAML written to: {output_path.resolve()}")
    print(f"Error report written to: {error_path.resolve()}")
    print(f"Items added: {added_items}, triggers added: {added_triggers}, unchanged: {unchanged_pairs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

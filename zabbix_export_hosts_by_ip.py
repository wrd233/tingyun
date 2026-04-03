#!/usr/bin/env python3
"""
Export Zabbix hosts to a YAML file by a list of interface IPs.

Usage:
  python3 zabbix_export_hosts_by_ip.py \
    --url https://zabbix.example.com/api_jsonrpc.php \
    --token YOUR_API_TOKEN \
    --ip-file ips.txt \
    --output hosts.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Zabbix hosts as YAML by interface IP list."
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Zabbix API URL, for example: https://zabbix.example.com/api_jsonrpc.php",
    )
    parser.add_argument("--token", required=True, help="Zabbix API token")
    parser.add_argument(
        "--ip-file",
        required=True,
        help="Text file containing one IP per line",
    )
    parser.add_argument(
        "--output",
        default="zabbix_hosts_export.yaml",
        help="Output YAML file path",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds, default: 30",
    )
    return parser.parse_args()


def read_ip_file(ip_file: str) -> list[str]:
    ips: list[str] = []
    seen: set[str] = set()

    for raw_line in Path(ip_file).read_text(encoding="utf-8").splitlines():
        ip = raw_line.strip()
        if not ip or ip.startswith("#"):
            continue
        if ip not in seen:
            seen.add(ip)
            ips.append(ip)

    if not ips:
        raise ValueError("IP file is empty or contains no valid IP entries.")

    return ips


def zabbix_api_call(url: str, token: str, method: str, params: dict[str, Any], timeout: int) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json-rpc",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response: {body}") from exc

    if "error" in result:
        err = result["error"]
        raise RuntimeError(
            f"Zabbix API error {err.get('code')}: {err.get('message')} - {err.get('data')}"
        )

    return result.get("result")


def get_hosts_by_ips(url: str, token: str, ips: list[str], timeout: int) -> list[dict[str, Any]]:
    params = {
        "output": ["hostid", "host", "name"],
        "selectInterfaces": ["interfaceid", "ip", "type", "port", "main"],
        "selectHostGroups": ["groupid", "name"],
        "filter": {
            "ip": ips,
        },
    }
    return zabbix_api_call(url, token, "host.get", params, timeout)


def export_hosts_yaml(url: str, token: str, hostids: list[str], timeout: int) -> str:
    params = {
        "format": "yaml",
        "prettyprint": True,
        "options": {
            "hosts": hostids,
        },
    }
    result = zabbix_api_call(url, token, "configuration.export", params, timeout)
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("configuration.export returned an empty result.")
    return result


def main() -> int:
    args = parse_args()

    try:
        ips = read_ip_file(args.ip_file)
        hosts = get_hosts_by_ips(args.url, args.token, ips, args.timeout)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if not hosts:
        print("[ERROR] No hosts matched the provided IP list.", file=sys.stderr)
        return 1

    hostids: list[str] = []
    matched_ips: set[str] = set()

    print("Matched hosts:")
    for host in hosts:
        hostid = host["hostid"]
        hostids.append(hostid)

        interfaces = host.get("interfaces", [])
        for interface in interfaces:
            ip = interface.get("ip")
            if ip:
                matched_ips.add(ip)

        interface_ips = ", ".join(
            interface["ip"] for interface in interfaces if interface.get("ip")
        ) or "-"
        print(
            f"  hostid={hostid} host={host.get('host')} name={host.get('name')} "
            f"ips=[{interface_ips}]"
        )

    missing_ips = [ip for ip in ips if ip not in matched_ips]
    if missing_ips:
        print("\nIPs not matched to any host:")
        for ip in missing_ips:
            print(f"  {ip}")

    unique_hostids = list(dict.fromkeys(hostids))

    try:
        yaml_content = export_hosts_yaml(args.url, args.token, unique_hostids, args.timeout)
        output_path = Path(args.output)
        output_path.write_text(yaml_content, encoding="utf-8")
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"\nExported {len(unique_hostids)} host(s) to: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tingyun_adapter_client.xls_parsing import parse_component_operation_xls


class _FakeSheet:
    def __init__(self, rows: list[list[object]]) -> None:
        self._rows = rows
        self.nrows = len(rows)
        self.ncols = max((len(row) for row in rows), default=0)

    def cell_value(self, row_idx: int, col_idx: int) -> object:
        row = self._rows[row_idx]
        return row[col_idx] if col_idx < len(row) else ""


class _FakeBook:
    def __init__(self, rows: list[list[object]]) -> None:
        self._sheet = _FakeSheet(rows)
        self.nsheets = 1

    def sheet_by_index(self, index: int) -> _FakeSheet:
        return self._sheet


class XlsParsingTests(unittest.TestCase):
    def test_parse_component_operation_xls_reads_structured_metrics(self) -> None:
        fake_rows = [
            ["序号", "SQL", "平均响应时间(ms)", "响应总时间(ms)", "吞吐率(qps)", "SQL执行次数", "错误次数", "慢次数"],
            ["1", "SELECT * FROM foo", 12.0, 120.0, 1.5, 10.0, 0.0, 2.0],
            ["2", "SELECT * FROM bar", 18.0, 360.0, 0.5, 20.0, 1.0, 4.0],
        ]
        with patch("tingyun_adapter_client.xls_parsing.xlrd.open_workbook", return_value=_FakeBook(fake_rows)):
            result = parse_component_operation_xls(Path("/tmp/demo.xls"), kind="sql")
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.rows[0]["parse_mode"], "xls_xlrd")
        self.assertEqual(result.rows[0]["avg_rt_ms"], 12.0)
        self.assertEqual(result.rows[0]["total_time_ms"], 120.0)
        self.assertEqual(result.rows[0]["exec_count"], 10.0)
        self.assertEqual(result.rows[0]["slow_count"], 2.0)

    def test_parse_component_operation_xls_filters_nosql_noise(self) -> None:
        fake_rows = [
            ["序号", "SQL", "平均响应时间(ms)", "响应总时间(ms)", "吞吐率(qps)", "SQL执行次数", "错误次数", "慢次数"],
            ["1", "Arial1", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ["2", "PEXPIRE", 0.0, 41254.0, 1.06, 183504.0, 0.0, 0.0],
        ]
        with patch("tingyun_adapter_client.xls_parsing.xlrd.open_workbook", return_value=_FakeBook(fake_rows)):
            result = parse_component_operation_xls(Path("/tmp/demo.xls"), kind="nosql")
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]["representative_command"], "PEXPIRE")
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()

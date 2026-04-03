from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient


class LogTraceClient(BaseClient):
    def search(
        self,
        *,
        start_time: int,
        end_time: int,
        page_num: int = 1,
        page_size: int = 10000,
        trace_id: Optional[str] = None,
        application_id: Optional[int] = None,
    ) -> Any:
        payload = {
            "endTime": end_time,
            "lang": self.lang,
            "pageNum": page_num,
            "pageSize": page_size,
            "sortOrder": "desc",
            "startTime": start_time,
        }
        if trace_id is not None:
            payload["traceId"] = trace_id
        if application_id is not None:
            payload["applicationId"] = application_id
        return self.post_form("/server-api/data/logTrace/searchLogTrace", payload, query={"lang": self.lang})

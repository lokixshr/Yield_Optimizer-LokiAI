from __future__ import annotations
import json
import time
from typing import Dict, Any, Optional

from app.config import get_settings
from app.clients.http import http_client

settings = get_settings()

async def loki_log(level: str, message: str, labels: Optional[Dict[str, str]] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Send a log line to Loki Core. Endpoint path per spec: `${LOKI_URL}/api/logs`.
    """
    ts_ns = str(int(time.time() * 1_000_000_000))
    stream = labels or {"service": "yield-optimizer", "env": settings.ENV, "level": level}
    payload = {
        "streams": [
            {
                "stream": stream,
                "values": [
                    [ts_ns, json.dumps({"message": message, **(extra or {})})]
                ],
            }
        ]
    }
    url = f"{settings.LOKI_URL.rstrip('/')}/api/logs"
    try:
        resp = await http_client.post(url, json=payload, headers={"Content-Type": "application/json"})
        # Loki may return 204 No Content on success
        if resp.status_code >= 400:
            # Best-effort: do not raise to avoid breaking request flow
            pass
    except Exception:
        # Swallow logging exceptions
        pass

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.http import HttpClient

logger = logging.getLogger(__name__)


async def graphql_query(http: HttpClient, url: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"query": query, "variables": variables or {}}
    resp = await http.post(url, json=payload, headers={"Content-Type": "application/json"})
    data = resp.json()
    if "errors" in data:
        logger.warning(f"GraphQL errors from {url}: {data['errors']}")
        raise RuntimeError("GraphQL query failed")
    return data.get("data", {})

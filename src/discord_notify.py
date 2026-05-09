"""Post messages to Discord via incoming webhook (no extra dependencies)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def send_discord_webhook(webhook_url: str, content: str, timeout: float = 10.0) -> None:
    """POST plain text content to a Discord channel webhook URL."""
    url = (webhook_url or "").strip()
    if not url:
        return
    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        pass

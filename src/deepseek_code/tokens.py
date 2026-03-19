from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict

import tiktoken


def _encoding_for_model(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_message_tokens(messages: Iterable[Dict[str, Any]], model: str) -> int:
    encoding = _encoding_for_model(model)
    total = 0
    for message in messages:
        total += 4
        content = message.get("content") or ""
        total += len(encoding.encode(content))
        if message.get("role") == "tool":
            total += len(encoding.encode(message.get("name", "")))
        tool_calls = message.get("tool_calls") or []
        for call in tool_calls:
            func = call.get("function", {})
            total += len(encoding.encode(func.get("name", "")))
            total += len(encoding.encode(func.get("arguments", "")))
    total += 2
    return total

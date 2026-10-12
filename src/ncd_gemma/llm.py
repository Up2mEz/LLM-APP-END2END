from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from uuid import uuid4

from openai import APIConnectionError, OpenAI

from .config import Settings, proxy_ready


class ProxyError(RuntimeError):
    def __init__(self, category: str, attempts: int = 1):
        super().__init__(category)
        self.category = category
        self.attempts = attempts


class ProxyClient:
    def __init__(self, settings: Settings):
        if not proxy_ready():
            raise ProxyError("class_proxy_configuration_missing")
        self.settings = settings
        # Reads OPENAI_API_KEY and OPENAI_BASE_URL as required by the course.
        self.client = OpenAI(timeout=settings.request_timeout, max_retries=0)
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self.endpoint_identity = hashlib.sha256(os.environ["OPENAI_BASE_URL"].encode()).hexdigest()

    def complete(self, messages: list[dict], tools: list[dict], tool_choice, remaining: float):
        payload = {"model": self.settings.model, "messages": messages, "temperature": 0,
                   "max_tokens": self.settings.max_output_tokens}
        # The class proxy rejects tool_choice when no tools are supplied.
        if tools:
            payload.update(tools=tools, tool_choice=tool_choice)
        key = hashlib.sha256(json.dumps({"endpoint": self.endpoint_identity, "payload": payload},
                                       ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        path = self.settings.cache_dir / f"{key}.json"
        if path.exists():
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
                if result.get("cache_key") == key and isinstance(result["message"], dict):
                    return {**result, "cached": True, "latency_ms": 0}
            except (ValueError, KeyError):
                pass
        start = time.monotonic()
        attempts = 0
        for attempt in range(2):
            attempts += 1
            budget = remaining - (time.monotonic() - start)
            try:
                response = self.client.chat.completions.create(**payload, timeout=min(self.settings.request_timeout, budget))
                break
            except Exception as exc:
                # Never persist raw exceptions, which can contain secrets.
                if (isinstance(exc, APIConnectionError) and attempt == 0
                        and remaining - (time.monotonic() - start) > 7):
                    time.sleep(2.0)
                    continue
                status = getattr(exc, "status_code", None)
                headers = getattr(getattr(exc, 'response', None), 'headers', {})
                try:
                    delay = max(15.0, float(headers.get('retry-after', '15')))
                except (ValueError, TypeError):
                    delay = 15.0
                if status == 429 and attempt == 0 and delay <= 60 and remaining - (time.monotonic() - start) - delay > 5:
                    time.sleep(delay)
                    continue
                raise ProxyError(f"proxy_http_{status}" if status else type(exc).__name__, attempts) from None
        if not response.choices:
            raise ProxyError("empty_model_response")
        message = response.choices[0].message
        calls = [{"id": c.id, "type": c.type,
                  "function": {"name": c.function.name, "arguments": c.function.arguments}}
                 for c in (message.tool_calls or []) if c.type == "function"]
        result = {"cache_key": key, "message": {"role": "assistant", "content": message.content},
                  "usage": response.usage.model_dump() if response.usage else {},
                  "finish_reason": response.choices[0].finish_reason,
                  "cached": False, "api_attempts": attempts, "latency_ms": round((time.monotonic() - start) * 1000, 1)}
        if calls:
            result["message"]["tool_calls"] = calls
        temp = path.with_name(f"{key}.{uuid4().hex}.tmp")
        temp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)
        return result

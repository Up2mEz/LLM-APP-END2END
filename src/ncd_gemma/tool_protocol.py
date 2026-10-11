"""Decode JSON or Gemma 4's native tool syntax without executing model text.

Reference: https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4
The class proxy can wrap native Gemma syntax inside OpenAI function.arguments.
"""
import json
import re


def decode_arguments(raw: str, expected_name: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 5000:
        raise ValueError("Invalid argument size")
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
    except json.JSONDecodeError:
        prefix = f"<|tool_call>call:{expected_name}"
        if not raw.startswith(prefix) or not raw.endswith("<tool_call|>"):
            raise ValueError("Unknown tool argument format") from None
        value = _NativeParser(raw[len(prefix):-len("<tool_call|>")]).parse()
    if not isinstance(value, dict):
        raise ValueError("Tool arguments must be an object")
    return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate argument key")
        result[key] = value
    return result


class _NativeParser:
    def __init__(self, text):
        self.text, self.i = text, 0

    def skip(self):
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1

    def take(self, token):
        self.skip()
        if self.text.startswith(token, self.i):
            self.i += len(token)
            return True
        return False

    def require(self, token):
        if not self.take(token):
            raise ValueError("Malformed native tool arguments")

    def parse(self):
        value = self.value(0)
        self.skip()
        if self.i != len(self.text):
            raise ValueError("Trailing tool argument content")
        return value

    def value(self, depth):
        if depth > 4:
            raise ValueError("Tool arguments nested too deeply")
        self.skip()
        marker = '<|"|>'
        if self.take(marker):
            end = self.text.find(marker, self.i)
            if end < 0:
                raise ValueError("Unterminated native string")
            value = self.text[self.i:end]
            self.i = end + len(marker)
            return value
        if self.take("{"):
            pairs = []
            if self.take("}"):
                return {}
            while True:
                self.skip()
                match = re.match(r"[A-Za-z_][A-Za-z_0-9]*", self.text[self.i:])
                if not match:
                    raise ValueError("Invalid native argument key")
                key = match.group()
                self.i += len(key)
                self.require(":")
                pairs.append((key, self.value(depth + 1)))
                if len(pairs) > 32:
                    raise ValueError("Too many argument fields")
                if self.take("}"):
                    return _unique(pairs)
                self.require(",")
        # Search arguments do not need arrays, expressions, or unquoted strings.
        match = re.match(r"(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)", self.text[self.i:])
        if match:
            self.i += len(match.group())
            return json.loads(match.group())
        raise ValueError("Unsupported native argument value")

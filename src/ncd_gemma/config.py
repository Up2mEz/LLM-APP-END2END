from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MODEL = "gemma-4-E4B-it"


def load_environment():
    # This project's explicit .env wins over unrelated inherited OpenAI credentials.
    # Production can omit the file and supply the same variables in the environment.
    load_dotenv(ROOT / ".env", override=True)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


@dataclass(frozen=True)
class Settings:
    model: str = MODEL
    max_steps: int = 4
    max_searches: int = 3
    request_timeout: float = 45.0
    agent_timeout: float = 150.0
    max_output_tokens: int = 1400
    context_chars: int = 18000
    max_sources: int = 12
    cache_dir: Path = ROOT / ".cache/llm"

    @classmethod
    def from_env(cls):
        settings = cls(model=os.getenv("NCD_MODEL", MODEL), max_steps=int(os.getenv("NCD_MAX_STEPS", "4")),
                       request_timeout=float(os.getenv("NCD_REQUEST_TIMEOUT", "45")),
                       agent_timeout=float(os.getenv("NCD_AGENT_TIMEOUT", "150")))
        if settings.model != MODEL:
            raise ValueError("Project requires gemma-4-E4B-it")
        if not 2 <= settings.max_steps <= 6 or not 5 <= settings.request_timeout <= 90 or not 10 <= settings.agent_timeout <= 300:
            raise ValueError("Invalid timeout or step budget")
        return settings


def proxy_ready() -> bool:
    url = urlsplit(os.getenv("OPENAI_BASE_URL", ""))
    return bool(os.getenv("OPENAI_API_KEY")) and url.scheme == "https" and url.hostname == "llm.nat-d.uk" and not (url.username or url.password or url.query)

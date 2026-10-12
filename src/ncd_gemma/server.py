from __future__ import annotations

import base64
import binascii
import hmac
import os
import threading
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agent import Agent, out_of_scope_reply
from .config import ROOT, Settings, allowed_hosts, load_environment, proxy_ready
from .llm import ProxyClient
from .retrieval import EvidenceRetriever
from .schemas import AskRequest

load_environment()
app = FastAPI(title="NCD Evidence · Gemma", version="0.1.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
_agent = None
_load_lock = threading.Lock()
_request_slot = threading.BoundedSemaphore(1)


def _valid_demo_credentials(header: str, user: str, password: str) -> bool:
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return False
    supplied_user, separator, supplied_password = decoded.partition(":")
    return bool(separator) and hmac.compare_digest(supplied_user, user) and hmac.compare_digest(supplied_password, password)


def get_agent():
    global _agent
    with _load_lock:
        if _agent is None:
            settings = Settings.from_env()
            client = ProxyClient(settings)
            retriever = EvidenceRetriever()
            _agent = Agent(client, retriever, settings)
    return _agent


@app.middleware("http")
async def local_origin(request: Request, call_next):
    password = os.getenv("NCD_DEMO_PASSWORD", "")
    if password and request.url.path != "/api/health":
        if not _valid_demo_credentials(request.headers.get("authorization", ""),
                                       os.getenv("NCD_DEMO_USER", "demo"), password):
            return JSONResponse({"detail": "Authentication required"}, status_code=401,
                                headers={"WWW-Authenticate": 'Basic realm="NCD demo"'})
    origin = request.headers.get("origin")
    if request.method == "POST" and origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request.headers.get("host", "").lower() or parsed.path or parsed.query or parsed.fragment:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    return response


@app.get("/api/health")
def health():
    return {"status": "ready" if proxy_ready() else "configuration_needed", "proxy_configured": proxy_ready(),
            "model": "gemma-4-E4B-it", "retrieval_loaded": _agent is not None,
            "data_present": (ROOT / "data/index/dense-bge-m3-t128-v12/vectors.npy").is_file()}


@app.post("/api/ask")
def ask(request: AskRequest):
    greeting = out_of_scope_reply(request.question)
    if greeting:
        return JSONResponse(greeting)
    if not _request_slot.acquire(blocking=False):
        raise HTTPException(429, "กำลังตอบคำถามก่อนหน้า กรุณารอสักครู่")
    try:
        try:
            agent = get_agent()
        except Exception:
            raise HTTPException(503, "ยังโหลดระบบไม่ได้ โปรดตรวจ class proxy, data snapshot และ embedding cache ตาม README") from None
        result = agent.run(request.question)
        return JSONResponse(result, status_code=502 if result["status"] == "error" else 200)
    finally:
        _request_slot.release()


@app.get("/api/evaluation")
def evaluation():
    path = ROOT / "reports/retrieval_metrics.json"
    if not path.is_file():
        raise HTTPException(404, "ยังไม่ได้สร้างผล evaluation")
    import json
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/tokens.css", include_in_schema=False)
def design_tokens():
    return FileResponse(ROOT / "tokens.css", media_type="text/css")


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")

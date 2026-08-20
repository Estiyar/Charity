from __future__ import annotations

import os
import re
import time
import uuid
import asyncio
from typing import Optional

import httpx
import redis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.staticfiles import StaticFiles

SERVICE_URLS = {
    "identity": os.environ.get("IDENTITY_SERVICE_URL", "http://localhost:8001"),
    "profile": os.environ.get("PROFILE_SERVICE_URL", "http://localhost:8002"),
    "cards": os.environ.get("CARDS_SERVICE_URL", "http://localhost:8003"),
    "verification": os.environ.get("VERIFICATION_SERVICE_URL", "http://localhost:8004"),
    "documents": os.environ.get("DOCUMENTS_SERVICE_URL", "http://localhost:8005"),
    "payments": os.environ.get("PAYMENTS_SERVICE_URL", "http://localhost:8006"),
    "moderation": os.environ.get("MODERATION_SERVICE_URL", "http://localhost:8007"),
    "expenses": os.environ.get("EXPENSES_SERVICE_URL", "http://localhost:8008"),
    "notifications": os.environ.get("NOTIFICATIONS_SERVICE_URL", "http://localhost:8009"),
    "admin": os.environ.get("ADMIN_SERVICE_URL", "http://localhost:8010"),
}

ROUTES = [
    (re.compile(r"^/api/auth/"), "identity"),
    (re.compile(r"^/api/admin/users"), "identity"),
    (re.compile(r"^/api/admin/moderators"), "identity"),
    (re.compile(r"^/api/profile/"), "profile"),
    (re.compile(r"^/api/beneficiaries"), "profile"),
    (re.compile(r"^/api/representations"), "profile"),
    (re.compile(r"^/api/cards/\d+/donate/"), "payments"),
    (re.compile(r"^/api/cards/\d+/donations/"), "payments"),
    (re.compile(r"^/api/cards/\d+/documents/"), "documents"),
    (re.compile(r"^/api/cards/\d+/expenses/"), "expenses"),
    (re.compile(r"^/api/cards/\d+/invoices/"), "expenses"),
    (re.compile(r"^/api/catalog"), "cards"),
    (re.compile(r"^/api/cards/"), "cards"),
    (re.compile(r"^/api/moderation/documents/"), "documents"),
    (re.compile(r"^/api/moderation/expenses/"), "expenses"),
    (re.compile(r"^/api/moderation/invoices/"), "expenses"),
    (re.compile(r"^/api/moderation/"), "moderation"),
    (re.compile(r"^/api/documents/"), "documents"),
    (re.compile(r"^/api/expenses/"), "expenses"),
    (re.compile(r"^/api/invoices"), "expenses"),
    (re.compile(r"^/api/payouts"), "expenses"),
    (re.compile(r"^/api/medregistry/"), "verification"),
    (re.compile(r"^/api/antifraud/"), "verification"),
    (re.compile(r"^/api/donations/"), "payments"),
    (re.compile(r"^/api/redistribution"), "payments"),
    (re.compile(r"^/api/refunds/"), "payments"),
    (re.compile(r"^/api/stats/"), "payments"),
    (re.compile(r"^/api/admin/cards"), "cards"),
    (re.compile(r"^/api/admin/donations"), "payments"),
    (re.compile(r"^/api/admin/expenses"), "expenses"),
    (re.compile(r"^/api/admin/moderation-logs"), "moderation"),
    (re.compile(r"^/api/admin/"), "admin"),
    (re.compile(r"^/api/notifications"), "notifications"),
    (re.compile(r"^/api/beneficiaries"), "profile"),
    (re.compile(r"^/api/payments/"), "payments"),
]

RATE_LIMITED = [
    re.compile(r"^/api/auth/register"),
    re.compile(r"^/api/auth/login"),
    re.compile(r"^/api/auth/ecp/"),
    re.compile(r"^/api/cards/recipient"),
    re.compile(r"^/api/cards/\d+/donate/"),
    re.compile(r"^/api/payments/session"),
]

REQUEST_COUNT = Counter("gateway_http_requests_total", "Gateway requests", ["method", "service", "status"])
REQUEST_LATENCY = Histogram("gateway_http_request_latency_seconds", "Gateway latency", ["service"])

app = FastAPI(title="e-komek API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:15173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:15173",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)

MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/media")
if os.path.isdir(MEDIA_ROOT):
    app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = int(os.environ.get("GATEWAY_RATE_LIMIT", "30"))
RATE_WINDOW = int(os.environ.get("GATEWAY_RATE_WINDOW_SECONDS", "60"))


def redis_client():
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def match_service(path: str) -> Optional[str]:
    for pattern, service_name in ROUTES:
        if pattern.search(path):
            return service_name
    return None


def is_rate_limited_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in RATE_LIMITED)


@app.get("/health/")
@app.get("/health")
async def health():
    async def check(name, url):
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{url}/health/")
                return name, response.json() if response.status_code < 500 else {"status": "down"}
        except httpx.HTTPError:
            return name, {"status": "down"}

    pairs = await asyncio.gather(*(check(name, url) for name, url in SERVICE_URLS.items()))
    results = dict(pairs)
    overall = "ok" if all(item.get("status") == "ok" for item in results.values()) else "degraded"
    return {"status": overall, "service": "api-gateway", "dependencies": results}


@app.get("/metrics/")
@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    full_path = request.url.path
    if not full_path.startswith("/"):
        full_path = "/" + full_path
    service_name = match_service(full_path)
    if service_name is None:
        return JSONResponse({"detail": "Not found."}, status_code=404)

    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    correlation_id = request.headers.get("x-correlation-id") or request_id

    if is_rate_limited_path(full_path):
        try:
            key = f"rl:{request.client.host if request.client else 'unknown'}:{full_path}"
            current = redis_client().incr(key)
            if current == 1:
                redis_client().expire(key, RATE_WINDOW)
            if current > RATE_LIMIT:
                return JSONResponse({"detail": "Too many requests."}, status_code=429)
        except redis.RedisError:
            pass

    target = SERVICE_URLS[service_name]
    query = str(request.url.query)
    url = f"{target}{full_path}"
    if query:
        url = f"{url}?{query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    headers["x-request-id"] = request_id
    headers["x-correlation-id"] = correlation_id
    body = await request.body()
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                request.method,
                url,
                headers=headers,
                content=body,
            )
    except httpx.HTTPError as exc:
        REQUEST_COUNT.labels(request.method, service_name, "502").inc()
        return JSONResponse({"detail": "Upstream unavailable.", "error": str(exc)}, status_code=502)

    REQUEST_COUNT.labels(request.method, service_name, str(upstream.status_code)).inc()
    REQUEST_LATENCY.labels(service_name).observe(time.perf_counter() - started)
    excluded = {"content-encoding", "transfer-encoding", "connection"}
    response_headers = {
        key: value for key, value in upstream.headers.items() if key.lower() not in excluded
    }
    response_headers["X-Request-ID"] = request_id
    response_headers["X-Correlation-ID"] = correlation_id
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )

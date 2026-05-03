"""
GeniOS Gateway — thin proxy that routes to backend agent services.

Routes:
  - /daa/*   → DAA service at localhost:8001
  - /email/* → EmailAgent service at localhost:8002
  - /        → Gateway health check
"""
import logging
from fastapi import FastAPI, Request, Response
import httpx
import os
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GeniOS Gateway",
    description="Unified entry point for all GeniOS AI Agent services.",
)

SERVICE_MAP = {
    "daa": os.getenv("DAA_SERVICE_URL", "http://localhost:8001"),
    "email": os.getenv("EMAIL_SERVICE_URL", "http://localhost:8002"),
}

@app.get("/")
def read_root():
    return {
        "message": "GeniOS Gateway is running.",
        "services": list(SERVICE_MAP.keys()),
    }


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    """Forward requests to the appropriate backend service."""
    backend = SERVICE_MAP.get(service)
    if not backend:
        return Response(
            content=f'{{"error": "Unknown service: {service}. Available: {list(SERVICE_MAP.keys())}"}}',
            status_code=404,
            media_type="application/json",
        )

    async with httpx.AsyncClient() as client:
        url = f"{backend}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body(),
            params=request.query_params,
            timeout=60.0,
        )

    # Filter out hop-by-hop headers
    excluded_headers = {"transfer-encoding", "content-encoding", "content-length"}
    headers = {k: v for k, v in response.headers.items() if k.lower() not in excluded_headers}

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
        media_type=response.headers.get("content-type"),
    )

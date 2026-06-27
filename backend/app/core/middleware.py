from __future__ import annotations

from uuid import uuid4

import structlog
from opentelemetry import trace
from starlette.types import ASGIApp, Message, Receive, Scope, Send


tracer = trace.get_tracer(__name__)


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        request_id = headers.get("x-request-id") or str(uuid4())
        path = str(scope.get("path", ""))
        method = str(scope.get("method", ""))
        logger = structlog.get_logger("http")

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = raw_headers
                span.set_attribute("http.status_code", message["status"])
                logger.info(
                    "request_finished",
                    request_id=request_id,
                    path=path,
                    method=method,
                    status_code=message["status"],
                )
            await send(message)

        with tracer.start_as_current_span("http.request") as span:
            span.set_attribute("http.request_id", request_id)
            span.set_attribute("http.method", method)
            span.set_attribute("http.target", path)
            logger.info("request_started", request_id=request_id, path=path, method=method)
            await self.app(scope, receive, send_with_request_id)

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length header exceeds the configured limit.

    This is the fast-path guard: it reads only the Content-Length header before
    any body bytes are buffered, so oversized requests are rejected immediately
    without reading the payload into memory.

    Fallback: clients using chunked transfer encoding omit Content-Length.
    Those requests pass through here and are caught by the per-file size check
    in the upload route instead.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    {"detail": "Invalid Content-Length header"}, status_code=400
                )
            if length > self._max_bytes:
                limit_mb = self._max_bytes // (1024 * 1024)
                logger.warning(
                    "Rejected %s %s: Content-Length %d bytes exceeds %d MB limit",
                    request.method,
                    request.url.path,
                    length,
                    limit_mb,
                )
                return JSONResponse(
                    {"detail": f"Request body exceeds the {limit_mb} MB upload limit"},
                    status_code=413,
                )
        return await call_next(request)

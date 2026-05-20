import logging
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.request_context import set_request_id

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> None:

        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid4())[:8]

        set_request_id(request_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response

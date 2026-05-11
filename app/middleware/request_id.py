from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

from app.core.request_context import set_request_id
from uuid import uuid4

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid4())[:8]

        set_request_id(request_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response
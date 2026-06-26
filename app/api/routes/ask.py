"""
Ask endpoint — production-grade RAG Q&A API.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.deps import get_ask_service
from app.core.dependencies import get_current_role
from app.middleware.rate_limiter import limiter
from app.schemas.ask import AskRequest, AskResponse
from app.services.ask_service import AskService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
async def ask_question(
    request: Request,
    response: Response,
    ask_request: AskRequest,
    ask_service: Annotated[AskService, Depends(get_ask_service)],
    user_role: Annotated[str, Depends(get_current_role)],
) -> AskResponse:
    try:
        logger.info(
            "Question received | authenticated_role=%s | claimed_role=%s | query_length=%d",
            user_role,
            ask_request.role,
            len(ask_request.query),
        )

        result = await ask_service.answer_question(
            ask_request=ask_request,
            user_role=user_role,
        )

        cache_status = "MISS"
        if result.metadata is not None:
            cache_status = str(result.metadata.get("cache", "MISS"))

        response.headers["X-Cache"] = cache_status
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = "unknown"

        return result

    except Exception as exc:
        logger.exception("Ask endpoint failed")
        raise HTTPException(status_code=500, detail="Failed to process question") from exc

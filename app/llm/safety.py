"""Content moderation and safety filtering."""

from dataclasses import dataclass

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.request_context import get_request_id

logger = get_logger(__name__)

client = OpenAI(
    api_key=settings.openai_api_key,
    timeout=settings.openai_timeout_seconds,
    max_retries=settings.openai_max_retries,
)


@dataclass
class ModerationResult:
    safe: bool
    blocked: bool
    reason: str | None = None


def moderate_content(text: str) -> ModerationResult:
    """
    Moderate user content using OpenAI moderation API.
    """

    if not text.strip():
        return ModerationResult(
            safe=False,
            blocked=True,
            reason="empty_input",
        )

    try:

        response = client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )

        result = response.results[0]

        if result.flagged:

            logger.warning(
                "Unsafe content blocked | request_id=%s",
                get_request_id(),
            )

            return ModerationResult(
                safe=False,
                blocked=True,
                reason="moderation_flagged",
            )

        return ModerationResult(
            safe=True,
            blocked=False,
        )

    except OpenAIError:

        logger.exception(
            "Moderation API failed | request_id=%s",
            get_request_id(),
        )

        # configurable fail-open behavior
        if settings.fail_open_moderation:

            return ModerationResult(
                safe=True,
                blocked=False,
                reason="moderation_unavailable",
            )

        return ModerationResult(
            safe=False,
            blocked=True,
            reason="moderation_unavailable",
        )

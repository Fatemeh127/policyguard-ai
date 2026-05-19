"""Content safety and filtering using moderation API."""

import logging
from typing import Optional
import os
from openai import OpenAI

logger = logging.getLogger(__name__)


def get_client() -> OpenAI:
    """
    Create OpenAI client lazily (safe with .env/config systems).
    """
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def check_content_safety(text: str) -> bool:
    try:
        client = get_client()

        response = client.moderations.create(model="omni-moderation-latest", input=text)

        result = response.results[0]

        if result.flagged:
            logger.warning("Unsafe content detected: %s", text)
            return False

        return True

    except Exception as e:
        logger.error("Moderation check failed: %s", str(e))
        return True


def filter_harmful_content(query: str) -> Optional[str]:
    try:
        client = get_client()

        response = client.moderations.create(model="omni-moderation-latest", input=query)

        result = response.results[0]

        if result.flagged:
            logger.warning("Blocked unsafe query: %s", query)
            return None

        return query

    except Exception as e:
        logger.error("Filtering failed: %s", str(e))
        return query

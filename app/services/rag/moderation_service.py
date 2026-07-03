"""Moderation service for RAG input safety."""

from app.llm.safety import ModerationResult, moderate_content


class ModerationService:
    """Handles content moderation for user input."""

    def check(self, text: str) -> ModerationResult:
        return moderate_content(text)

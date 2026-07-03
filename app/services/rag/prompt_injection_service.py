"""Prompt injection detection service for RAG input safety."""

from app.services.rag.prompt_injection_detector import is_prompt_injection


class PromptInjectionService:
    """Handles prompt injection detection for user input."""

    def detect(self, text: str) -> bool:
        return is_prompt_injection(text)

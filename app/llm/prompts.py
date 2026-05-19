"""Centralized prompt templates for LLM interactions.

This module contains all prompts used across the system to:
- Maintain consistency in LLM behavior
- Enable easy A/B testing of prompts
- Version control prompt changes
- Reuse prompts across different services
"""

# RAG System Prompts
SYSTEM_PROMPT_RAG = """You are a helpful assistant for an organization's document Q&A system.

Your job is to answer questions based ONLY on the context provided below.

Rules:
1. If the context contains the answer, provide a clear and concise response
2. If the context does NOT contain enough information, say: "I don't have enough information to answer this question based on the available documents."
3. Do not use your general knowledge - only use the provided context
4. Cite which document the information comes from when possible
5. Be professional and helpful

Answer the user's question based on the context provided."""


USER_PROMPT_TEMPLATE = """Context:
{context}

Question: {query}"""


# Safe Fallback Message
NO_CONTEXT_MESSAGE = (
    "I don't have enough information to answer this question based on the available documents."
)

"""Chat model factory with a provider switch (OpenAI or Anthropic Claude)."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from .config import Settings, get_settings


class MissingAPIKeyError(RuntimeError):
    """Raised when the selected LLM provider has no API key configured."""


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    """Return the configured chat model, or raise MissingAPIKeyError with a clear message."""
    s = settings or get_settings()
    if not s.api_key:
        var = "OPENAI_API_KEY" if s.llm_provider == "openai" else "ANTHROPIC_API_KEY"
        raise MissingAPIKeyError(
            f"No API key configured for LLM_PROVIDER={s.llm_provider}. "
            f"Set {var} in .env (see .env.example) and restart the backend."
        )
    if s.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # No temperature: current Claude models (e.g. claude-haiku-5-5) reject non-default sampling values.
        return ChatAnthropic(model=s.model_name, api_key=s.api_key, max_tokens=8000,
                             timeout=60, max_retries=2)
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=s.model_name, api_key=s.api_key, temperature=s.llm_temperature,
                      timeout=60, max_retries=2)

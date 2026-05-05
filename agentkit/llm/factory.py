"""Factory for creating LLM clients with auto-detection from environment."""
import importlib
import os

from agentkit.llm.provider import LLMProvider

PROVIDER_CONFIG = {
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-5-20250929",
        "module": "agentkit.llm.claude",
        "class_name": "ClaudeClient",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "module": "agentkit.llm.openai",
        "class_name": "OpenAIClient",
    },
    "gemini": {
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "module": "agentkit.llm.gemini",
        "class_name": "GeminiClient",
    },
    "ollama": {
        "env_key": None,
        "default_model": "llama3.1",
        "module": "agentkit.llm.ollama",
        "class_name": "OllamaClient",
    },
}


def detect_provider() -> str:
    """Auto-detect LLM provider from environment variables."""
    explicit = os.environ.get("AGENTKIT_LLM_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "ollama"


def create_llm_client(
    provider: str | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
) -> LLMProvider:
    """Create an LLM client.

    Args:
        provider: One of 'claude', 'openai', 'gemini', 'ollama'. Auto-detected if omitted.
        model: Model name. Uses provider default if omitted.
        max_tokens: Maximum tokens per response.
    """
    provider = provider or detect_provider()
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: {list(PROVIDER_CONFIG.keys())}"
        )

    model = model or os.environ.get("AGENTKIT_LLM_MODEL") or config["default_model"]

    mod = importlib.import_module(config["module"])
    client_class = getattr(mod, config["class_name"])

    if config["env_key"]:
        api_key = os.environ.get(config["env_key"])
        if not api_key:
            raise ValueError(
                f"{config['env_key']} environment variable is required for provider '{provider}'"
            )
        return client_class(api_key=api_key, model=model, max_tokens=max_tokens)
    else:
        # Ollama doesn't need an API key
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return client_class(model=model, max_tokens=max_tokens, base_url=base_url)

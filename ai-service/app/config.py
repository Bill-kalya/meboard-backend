import os


class Settings:
    def __init__(self) -> None:
        self.ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.llm_model: str = os.getenv("MEBOARD_LLM_MODEL", "llama3")
        self.llm_enabled: bool = os.getenv("MEBOARD_LLM_ENABLED", "true").lower() in ("1", "true", "yes")
        self.semantic_mode: str = os.getenv("MEBOARD_SEMANTIC_MODE", "hybrid").lower()
        self.max_content: int = int(os.getenv("MEBOARD_MAX_CONTENT", "2000"))


settings = Settings()

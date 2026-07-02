from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str

    # LLM провайдеры
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemma-2-9b-it:free"

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.1-8b-instant"  # Быстрая и бесплатная

    LLM_PROVIDER: str = "groq"  # deepseek, gemini, openrouter, groq

    DATABASE_PATH: str = "data/organizer.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_CALENDAR_CREDENTIALS: str = ""
    GOOGLE_CALENDAR_ID: str = "primary"


settings = Settings()
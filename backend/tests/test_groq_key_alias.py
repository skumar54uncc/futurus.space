"""GROQ_API_KEY (singular) must populate groq_api_keys settings."""

from core.config import Settings


def test_groq_api_key_singular_alias(monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_clerk_secret_key_for_ci_only_xx")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_singular_key")
    s = Settings()
    assert s.groq_api_keys == "gsk_test_singular_key"


def test_groq_api_keys_plural_wins_when_both_set(monkeypatch):
    monkeypatch.setenv("CLERK_SECRET_KEY", "test_clerk_secret_key_for_ci_only_xx")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEYS", "gsk_plural_a,gsk_plural_b")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_singular")
    s = Settings()
    # AliasChoices prefers first listed alias: GROQ_API_KEYS
    assert "gsk_plural_a" in s.groq_api_keys

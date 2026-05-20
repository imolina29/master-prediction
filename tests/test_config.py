def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

    from backend.config import Settings

    settings = Settings()

    assert settings.supabase_url == "https://test.supabase.co"
    assert settings.supabase_key == "test-key"
    assert settings.supabase_service_key == "test-service-key"
    assert settings.database_url == "postgresql://localhost/test"
    assert settings.env == "development"
    assert settings.log_level == "INFO"


def test_config_defaults():
    from backend.config import Settings

    settings = Settings(
        supabase_url="https://x.supabase.co",
        supabase_key="k",
        supabase_service_key="sk",
        database_url="postgresql://localhost/test",
    )
    assert settings.env == "development"
    assert settings.log_level == "INFO"

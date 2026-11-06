from pathlib import Path

import pytest
from pydantic import ValidationError

from jersa.config import ConfigError, Settings, load_settings, resolve_base_url


@pytest.fixture
def clean_env(monkeypatch):
    """Usuwa zmienne konfiguracji, żeby system i lokalny .env nie wpływały na wynik."""
    for name in ("BASE_URL", "DATABASE_URL", "ADMIN_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def test_reads_values_from_env_file(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text(
        "BASE_URL=http://localhost:3100\nDATABASE_URL=postgresql://u:p@localhost:5432/db\n"
    )
    s = Settings(_env_file=env)
    assert s.base_url == "http://localhost:3100"
    assert s.database_url == "postgresql://u:p@localhost:5432/db"


def test_environment_variable_overrides_env_file(tmp_path, clean_env, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("BASE_URL=http://from-file:1\n")
    monkeypatch.setenv("BASE_URL", "http://from-env:2")
    assert Settings(_env_file=env).base_url == "http://from-env:2"


def test_missing_base_url_raises(clean_env):
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_base_url_raises(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "localhost:3100")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_trailing_slash_is_stripped(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://localhost:3100/")
    assert Settings(_env_file=None).base_url == "http://localhost:3100"


def test_empty_database_url_means_no_database(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://localhost:3100")
    monkeypatch.setenv("DATABASE_URL", "")
    assert Settings(_env_file=None).database_url is None


def test_ignores_unrelated_keys(tmp_path, clean_env):
    env = tmp_path / ".env"
    env.write_text(
        "STOREFRONT_PATH=../../Documents/Repos/jersa-storefront\n"
        "APP_PORT=3100\n"
        "BASE_URL=http://localhost:3100\n"
    )
    assert Settings(_env_file=env).base_url == "http://localhost:3100"


def test_env_file_points_to_project_root():
    env_file = Path(Settings.model_config["env_file"])
    assert env_file.is_absolute()
    assert env_file.name == ".env"
    assert (env_file.parent / "pyproject.toml").exists()


def test_framework_tests_do_not_need_settings(base_url):
    assert base_url == "http://framework-tests.invalid"


def test_validation_error_hides_other_secrets(clean_env, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "ADMINSECRET")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:topsecret@h:5432/db")
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "ADMINSECRET" not in str(exc.value)
    assert "topsecret" not in str(exc.value)


def test_load_settings_names_variable_and_template(clean_env, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "ADMINSECRET")
    with pytest.raises(ConfigError, match=r"BASE_URL.*\.env\.example") as exc:
        load_settings(_env_file=None)
    assert "ADMINSECRET" not in str(exc.value)


def test_cli_base_url_wins_without_reading_settings():
    def settings_factory():
        raise AssertionError("settings should not be read when --base-url is given")

    assert resolve_base_url("https://stg.example/", settings_factory) == "https://stg.example"


def test_base_url_falls_back_to_settings(clean_env, monkeypatch):
    monkeypatch.setenv("BASE_URL", "http://127.0.0.1:3100")
    assert resolve_base_url(None, lambda: Settings(_env_file=None)) == "http://127.0.0.1:3100"

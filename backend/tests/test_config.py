import pytest

from app.config import DEV_SECRET, Settings


def test_default_environment_is_development():
    s = Settings(_env_file=None)
    assert s.is_production is False
    s.check()  # dev default secret must not block local work


def test_production_refuses_the_default_secret():
    s = Settings(_env_file=None, environment="production", session_secret=DEV_SECRET)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        s.check()


def test_production_accepts_a_real_secret():
    s = Settings(_env_file=None, environment="production", session_secret="x" * 40)
    s.check()
    assert s.is_production is True


def test_environment_value_is_case_and_space_insensitive():
    assert Settings(_env_file=None, environment="  PRODUCTION ").is_production is True
    assert Settings(_env_file=None, environment="staging").is_production is False

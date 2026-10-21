"""Verify actual runner inputs reach the client and query configuration."""

from pathlib import Path

import pytest

from rhos_lightspeed_tests.config import load_config


def test_runner_environment_inputs(monkeypatch, tmp_path: Path):
    token = tmp_path / "token"
    token.write_text("a-test-token\n")
    monkeypatch.setenv("RHOS_LIGHTSPEED_TOKEN_FILE", str(token))
    monkeypatch.setenv("RHOS_LIGHTSPEED_TOKEN", "ignored-environment-token")
    monkeypatch.setenv("RHOS_LIGHTSPEED_URL", "https://example.invalid:8443")
    monkeypatch.setenv("RHOS_LIGHTSPEED_TIMEOUT", "60")
    monkeypatch.setenv("RHOS_LIGHTSPEED_QUESTION", "A test question")
    config = load_config()
    assert config["rhos_lightspeed"]["token"] == "a-test-token"  # noqa: S105 - synthetic fixture
    assert config["rhos_lightspeed"]["base_url"] == "https://example.invalid:8443"
    assert config["rhos_lightspeed"]["timeout"] == 60
    assert config["query"]["default_question"] == "A test question"


@pytest.mark.parametrize("timeout", ["0", "-1", "invalid"])
def test_invalid_timeout_rejected(monkeypatch, timeout):
    monkeypatch.delenv("RHOS_LIGHTSPEED_TOKEN_FILE", raising=False)
    monkeypatch.setenv("RHOS_LIGHTSPEED_TIMEOUT", timeout)
    with pytest.raises(ValueError):
        load_config()

"""Configuration management for RHOS Lightspeed tests."""

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"
)


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        config = yaml.safe_load(f)

    config["rhos_lightspeed"]["base_url"] = os.environ.get(
        "RHOS_LIGHTSPEED_URL",
        config["rhos_lightspeed"]["base_url"],
    )

    token_file = os.environ.get("RHOS_LIGHTSPEED_TOKEN_FILE")
    config["rhos_lightspeed"]["token"] = (
        Path(token_file).read_text().strip()
        if token_file
        else os.environ.get("RHOS_LIGHTSPEED_TOKEN", "")
    )

    timeout = int(
        os.environ.get("RHOS_LIGHTSPEED_TIMEOUT", config["rhos_lightspeed"]["timeout"])
    )
    if timeout <= 0:
        raise ValueError("Lightspeed request timeout must be positive")
    config["rhos_lightspeed"]["timeout"] = timeout
    config["query"]["default_question"] = os.environ.get(
        "RHOS_LIGHTSPEED_QUESTION", config["query"]["default_question"]
    )

    goose = config.setdefault("goose", {})
    goose["model"] = os.environ.get("RHOS_LIGHTSPEED_MODEL", goose.get("model", ""))

    return config

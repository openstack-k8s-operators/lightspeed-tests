"""Shared pytest fixtures."""

import pytest

from rhos_lightspeed_tests.client import RHOSLightspeedClient
from rhos_lightspeed_tests.config import load_config


@pytest.fixture
def config():
    return load_config()


@pytest.fixture
def base_url(config):
    return config["rhos_lightspeed"]["base_url"]


@pytest.fixture
def timeout(config):
    return config["rhos_lightspeed"]["timeout"]


@pytest.fixture
def client(base_url, timeout):
    return RHOSLightspeedClient(base_url, timeout=timeout)

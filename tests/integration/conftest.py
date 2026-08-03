import pytest

from rhos_lightspeed_tests.auth import auth_cleanup, auth_setup
from rhos_lightspeed_tests.config import load_config


@pytest.fixture(scope="session", autouse=True)
def auth():
    ls = load_config()["rhos_lightspeed"]
    if not ls["token"]:
        auth_setup()
        yield
        auth_cleanup()
    else:
        yield

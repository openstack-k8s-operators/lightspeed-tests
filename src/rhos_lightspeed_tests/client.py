"""HTTP client for RHOS Lightspeed API."""

import openshift_client as oc
import requests

from .config import LS_NAMESPACE, LS_SERVICE_ACCOUNT


class RHOSLightspeedClient:
    def __init__(
        self,
        base_url: str,
        api_prefix: str = "/v1",
        token: str = "",
        timeout: int = 30,
        verify_tls: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_prefix = api_prefix
        self.verify_tls = verify_tls
        self.session = requests.Session()
        self.session.verify = verify_tls
        if not token:
            token = self._create_token()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _create_token(self) -> str:
        with oc.tracking():
            return (
                oc.invoke("create", ["token", LS_SERVICE_ACCOUNT, "-n", LS_NAMESPACE])
                .out()
                .strip()
            )

    def query(self, question: str) -> requests.Response:
        return self.session.post(
            f"{self.base_url}{self.api_prefix}/query",
            json={"query": question},
            timeout=self.timeout,
        )

    def metrics(self) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/metrics",
            timeout=self.timeout,
        )

    def health(self) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/health",
            timeout=self.timeout,
        )

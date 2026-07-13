"""HTTP client for RHOS Lightspeed API."""

import requests


class RHOSLightspeedClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def query(self, question: str) -> requests.Response:
        return self.session.post(
            f"{self.base_url}/query",
            json={"query": question},
            timeout=self.timeout,
        )

    def health(self) -> requests.Response:
        return self.session.get(
            f"{self.base_url}/health",
            timeout=self.timeout,
        )

"""Tests for the /query endpoint."""

import requests


class TestQueryEndpoint:
    def test_query_returns_response(self, client, config):
        """Verify that asking a question returns a valid response."""
        question = config["query"]["default_question"]
        response = client.query(question)

        assert response.status_code == 200

        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_query_rejects_missing_authentication(self, client, config):
        """The public API must reject a query with no client bearer token."""
        response = requests.post(
            f"{client.base_url}{client.api_prefix}/query",
            json={"query": config["query"]["default_question"]},
            timeout=client.timeout,
            verify=client.verify_tls,
        )
        assert response.status_code == 401

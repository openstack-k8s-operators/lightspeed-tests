"""Verify that telemetry's Prometheus collects metrics from a Lightspeed query."""

import time

import pytest
import requests


def _get_llm_calls_total(prometheus: dict) -> float:
    """Read the total collected LLM calls from telemetry's Prometheus."""
    query_url = prometheus["url"].rstrip("/") + "/api/v1/query"

    with requests.get(
        query_url,
        params={"query": "sum(ls_llm_calls_total)"},
        verify=False,  # noqa: S501 - CI Prometheus uses an internal certificate.
        timeout=10,
    ) as response:
        response.raise_for_status()
        samples = response.json()["data"]["result"]

    if not samples:
        return 0

    _timestamp, value = samples[0]["value"]
    return float(value)


def test_query_metrics_collected_by_telemetry(client, config):
    """Send a query and check that telemetry has collected a positive LLM counter."""
    prometheus = config["prometheus"]
    if not prometheus["url"]:
        pytest.skip("Set RHOS_LIGHTSPEED_PROMETHEUS_URL to test telemetry collection")

    question = config["query"]["default_question"]
    with client.query(question) as response:
        response.raise_for_status()

    deadline = time.monotonic() + prometheus["scrape_timeout"]
    llm_calls_total = 0
    while time.monotonic() < deadline:
        llm_calls_total = _get_llm_calls_total(prometheus)
        if llm_calls_total > 0:
            break
        time.sleep(5)

    assert llm_calls_total > 0, (
        "Prometheus did not collect a positive ls_llm_calls_total"
    )

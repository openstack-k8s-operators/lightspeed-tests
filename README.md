# rhos-lightspeed-tests

Test suite for RHOS Lightspeed in RHOSO environments.

## Setup

```bash
uv venv
uv sync
```

## Configuration

Configure the service in `config/default.yaml`. For Goose API tests, set
`goose.model` to the value of the Goose container's `LIGHTSPEED_MODEL`:

```yaml
rhos_lightspeed:
  base_url: "http://localhost:8080"
  timeout: 30

query:
  default_question: "What is OpenStack?"

goose:
  model: "<same value as Goose LIGHTSPEED_MODEL>"
```

Supply the bearer token through the environment:

```bash
export RHOS_LIGHTSPEED_TOKEN="<Lightspeed bearer token>"
```

`RHOS_LIGHTSPEED_URL` and `RHOS_LIGHTSPEED_MODEL` can override the URL and model
from the config file. Use a service origin without `/v1`. With the test-operator
playbook, supply `lightspeed_model`.

If you run the tests outside of OpenShift, you need to have a running port forward
for the `lightspeed-app-server` service. For example:

```
oc port-forward -n openstack-lightspeed svc/lightspeed-app-server 8443:8443
```

## Running tests

```bash
# Run all tests
uv run pytest

# Run integration tests only
uv run pytest tests/integration/

# Run Goose API tests
uv run pytest tests/integration/test_goose_responses.py

# Skip Goose tests that require a real LLM's answer content
uv run pytest tests/integration/test_goose_responses.py -m "not llm_dependent"

# Generate JUnit XML (automatic via pyproject.toml config)
uv run pytest  # outputs test-results.xml
```

## Adding tests

1. Create test file in appropriate directory:
   - `tests/unit/` - Fast, isolated tests
   - `tests/integration/` - Tests requiring deployed service
   - `tests/e2e/` - Full end-to-end scenarios

2. Use the shared fixtures from `conftest.py`:
   ```python
   class TestMyFeature:
       def test_something(self, client, config):
           response = client.query("my question")
           assert response.status_code == 200
   ```

3. Run: `uv run pytest tests/integration/test_my_feature.py`

## Project structure

```
rhos-lightspeed-tests/
├── config/
│   └── default.yaml                 # Default test configuration
├── src/rhos_lightspeed_tests/       # Shared utilities
│   ├── __init__.py
│   ├── client.py                    # API client (query, health)
│   └── config.py                    # Reads default.yaml, env var overrides
├── tests/
│   ├── conftest.py                  # Shared fixtures (config, client)
│   ├── unit/
│   ├── integration/
│   │   └── test_query_endpoint.py   # First test: /query endpoint
│   └── e2e/
├── pyproject.toml
└── README.md
```

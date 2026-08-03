"""Configuration management for RHOS Lightspeed tests."""

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"
)

LS_NAMESPACE = "openstack-lightspeed"
LS_SERVICE_ACCOUNT = "lightspeed-test-sa"
LS_ROLE = "lightspeed-test-role"
LS_ROLE_BINDING = "lightspeed-test-role-binding"


AUTH_CONFIG = f"""\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {LS_SERVICE_ACCOUNT}
  namespace: {LS_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: {LS_ROLE}
rules:
- nonResourceURLs: ["/ls-access"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {LS_ROLE_BINDING}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: {LS_ROLE}
subjects:
- kind: ServiceAccount
  name: {LS_SERVICE_ACCOUNT}
  namespace: {LS_NAMESPACE}"""


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        config = yaml.safe_load(f)

    config["rhos_lightspeed"]["base_url"] = os.environ.get(
        "RHOS_LIGHTSPEED_URL",
        config["rhos_lightspeed"]["base_url"],
    )

    config["rhos_lightspeed"]["token"] = os.environ.get(
        "RHOS_LIGHTSPEED_TOKEN",
        "",
    )

    return config

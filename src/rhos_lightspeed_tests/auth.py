import textwrap

import openshift_client as oc

from .config import (
    AUTH_CONFIG,
    LS_NAMESPACE,
    LS_ROLE,
    LS_ROLE_BINDING,
    LS_SERVICE_ACCOUNT,
)


def auth_setup():
    oc.invoke("apply", ["-f", "-"], stdin_str=textwrap.dedent(AUTH_CONFIG))


def auth_cleanup():
    oc.invoke(
        "delete",
        [
            "serviceaccount",
            LS_SERVICE_ACCOUNT,
            "-n",
            LS_NAMESPACE,
            "--ignore-not-found",
        ],
    )
    oc.invoke("delete", ["clusterrole", LS_ROLE, "--ignore-not-found"])
    oc.invoke("delete", ["clusterrolebinding", LS_ROLE_BINDING, "--ignore-not-found"])

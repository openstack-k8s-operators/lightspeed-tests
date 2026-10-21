"""Check the document assertions independently of a running application."""

from types import SimpleNamespace

import pytest

from tests.integration.test_okp_virtualization_filter import (
    TestOKPVirtualizationFilter as OKPFilterAssertions,
)

OPENSTACK_URL = (
    "http://lightspeed-okp-server.openstack-lightspeed.svc:8080/en/documentation/"
    "red_hat_openstack_services_on_openshift/18.0/html-single/instance_management/index"
)
OPENSHIFT_URL = (
    "http://lightspeed-okp-server.openstack-lightspeed.svc:8080/en/documentation/"
    "openshift_container_platform/4.22/html-single/multiple_networks/index"
)


def run_assertions(data):
    response = SimpleNamespace(status_code=200, json=lambda: data)
    client = SimpleNamespace(query=lambda question: response)
    # Exercise the actual integration assertions with captured-shape responses.
    OKPFilterAssertions().test_query_excludes_openshift_virtualization_docs(
        client, "How do I manage virtual machines?"
    )


def test_document_references_support_tool_metadata_and_deduplication():
    run_assertions(
        {
            "rag_chunks": [{"attributes": {"source": "okp"}}, {"attributes": None}],
            "referenced_documents": [{"doc_url": OPENSTACK_URL}],
        }
    )


@pytest.mark.parametrize(
    "data, message",
    [
        (
            {"rag_chunks": [], "referenced_documents": [{"doc_url": OPENSTACK_URL}]},
            "no rag_chunks",
        ),
        (
            {"rag_chunks": [{"attributes": {"doc_url": OPENSTACK_URL}}]},
            "missing document-reference URLs",
        ),
        (
            {"rag_chunks": [{}], "referenced_documents": [{"doc_url": OPENSHIFT_URL}]},
            "no OpenStack-related document references",
        ),
        (
            {
                "rag_chunks": [{}],
                "referenced_documents": [{"doc_url": OPENSTACK_URL}, {}],
            },
            "missing document-reference URLs",
        ),
        (
            {
                "rag_chunks": [{}],
                "referenced_documents": [
                    {"doc_url": OPENSTACK_URL},
                    {"doc_url": "   "},
                ],
            },
            "missing document-reference URLs",
        ),
    ],
)
def test_invalid_document_evidence_is_rejected(data, message):
    with pytest.raises(AssertionError, match=message):
        run_assertions(data)


@pytest.mark.parametrize(
    "book_path",
    [
        "html-single/virtualization/",
        "html-single%2Fvirtualization%2F",
    ],
)
def test_virtualization_documents_remain_rejected(book_path):
    url = OPENSHIFT_URL.replace("html-single/multiple_networks/", book_path)
    with pytest.raises(AssertionError, match="retrieved OpenShift Virtualization docs"):
        run_assertions(
            {
                "rag_chunks": [{}],
                "referenced_documents": [
                    {"doc_url": OPENSTACK_URL},
                    {"doc_url": url},
                ],
            }
        )

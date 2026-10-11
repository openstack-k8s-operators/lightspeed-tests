"""Sanity check that OKP RAG grounding does not leak OpenShift Virtualization docs.

RHOS Lightspeed is scoped to RHOSO/OpenStack (and general OpenShift) content. The
OKP chunk_filter_query excludes the OpenShift Virtualization documentation book,
since it shares the same "openshift_container_platform" product as docs we want
to keep (e.g. Migration Toolkit for Containers) and can only be told apart by its
parent_id path (".../html-single/virtualization/index"). This is a simple
regression guard: if OKP's internal document structure ever changes, this test
should start failing so the leak is caught rather than silently reappearing.
"""

from urllib.parse import unquote, urlsplit

import pytest

# Path segment unique to the OpenShift Virtualization documentation book in the
# OKP index, e.g.:
# ".../openshift_container_platform/4.18/html-single/virtualization/index"
VIRTUALIZATION_BOOK_PATH = "html-single/virtualization/"

# Marker identifying an OpenStack-related doc, e.g.:
# ".../red_hat_openstack_services_on_openshift/18.0/html-single/..."
OPENSTACK_DOC_MARKER = "openstack"

VIRTUALIZATION_ADJACENT_QUESTIONS = [
    "What tools can I use to pause, resume, or stop a VM?",
    "How do I create and manage virtual machines?",
]


class TestOKPVirtualizationFilter:
    @pytest.mark.parametrize("question", VIRTUALIZATION_ADJACENT_QUESTIONS)
    def test_query_excludes_openshift_virtualization_docs(self, client, question):
        """Virtualization-adjacent questions must not be grounded in OpenShift
        Virtualization docs.
        """
        response = client.query(question)
        assert response.status_code == 200

        data = response.json()
        rag_chunks = data.get("rag_chunks") or []
        assert rag_chunks, (
            f"Query {question!r} returned no rag_chunks; OKP retrieval may be broken"
        )

        # Tool retrieval retains provider metadata on chunks; resolved URLs live
        # on document references, which may be deduplicated across chunks.
        references = data.get("referenced_documents") or []
        doc_urls = [reference.get("doc_url") for reference in references]
        assert references and all(
            isinstance(url, str) and url.strip() for url in doc_urls
        ), f"Query {question!r} returned missing document-reference URLs: {doc_urls}"

        # The offline service hostname contains 'openstack' for every product.
        doc_paths = [unquote(urlsplit(url).path).lower() for url in doc_urls]
        openstack_docs = [path for path in doc_paths if OPENSTACK_DOC_MARKER in path]
        assert openstack_docs, (
            f"Query {question!r} returned no OpenStack-related document references: {doc_urls}"
        )

        leaked = [path for path in doc_paths if VIRTUALIZATION_BOOK_PATH in path]
        assert not leaked, (
            f"Query {question!r} retrieved OpenShift Virtualization docs: {leaked}"
        )

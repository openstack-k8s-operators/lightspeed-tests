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
    def test_responses_excludes_openshift_virtualization_docs(self, client, question):
        """Check the configured OKP document filter through the Responses API."""
        response = client.responses(
            {
                "input": question,
                "store": False,
                "stream": False,
                "tool_choice": {"type": "file_search"},
                "include": ["file_search_call.results"],
            }
        )
        assert response.status_code == 200

        results = [
            result
            for item in response.json().get("output") or []
            if item.get("type") == "file_search_call"
            for result in item.get("results") or []
        ]
        assert results, (
            f"Question {question!r} returned no file search results; "
            "OKP retrieval may be broken"
        )

        # OKP uses source_path offline and reference_url for online documents.
        doc_paths = []
        for result in results:
            attributes = result.get("attributes") or {}
            reference = attributes.get("source_path") or attributes.get("reference_url")
            assert isinstance(reference, str) and reference.strip(), (
                f"Question {question!r} returned a result without a document path"
            )
            # The service hostname may contain 'openstack' for every product.
            doc_paths.append(unquote(urlsplit(reference).path).lower())

        assert all(doc_paths), f"Question {question!r} returned empty document paths"
        openstack_docs = [path for path in doc_paths if OPENSTACK_DOC_MARKER in path]
        assert openstack_docs, (
            f"Question {question!r} returned no OpenStack-related documents: {doc_paths}"
        )

        leaked = [path for path in doc_paths if VIRTUALIZATION_BOOK_PATH in path]
        assert not leaked, (
            f"Question {question!r} retrieved OpenShift Virtualization docs: {leaked}"
        )

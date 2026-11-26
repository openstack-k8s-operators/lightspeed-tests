"""Sanity check that OKP RAG grounding does not leak OpenShift Virtualization docs.

RHOS Lightspeed is scoped to RHOSO/OpenStack (and general OpenShift) content. The
OKP chunk_filter_query excludes the OpenShift Virtualization documentation book,
since it shares the same "openshift_container_platform" product as docs we want
to keep (e.g. Migration Toolkit for Containers) and can only be told apart by its
parent_id path (".../html-single/virtualization/index"). This is a simple
regression guard: if OKP's internal document structure ever changes, this test
should start failing so the leak is caught rather than silently reappearing.
"""

import json
import logging
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


@pytest.fixture
def stored_response(client, question):
    """Create a conversation for one question and delete it after the checks."""
    response = client.responses(
        {"input": question, "store": True, "stream": False},
        headers={"X-LCS-Merge-Server-Tools": "true"},
    )
    assert response.status_code == 200, (
        f"POST /v1/responses: HTTP {response.status_code}"
    )
    body = response.json()
    conversation_id = body.get("conversation")
    assert isinstance(conversation_id, str) and conversation_id.strip(), (
        "POST /v1/responses returned no conversation ID"
    )
    yield body
    deleted = client.delete_conversation(conversation_id)
    assert deleted.status_code == 200, (
        f"DELETE conversation: HTTP {deleted.status_code}"
    )
    assert deleted.json()["deleted"] is True, (
        f"Conversation {conversation_id} still exists"
    )


def _saved_search_hits(turn):
    """Read raw hits for the server-managed file searches in this question's turn."""
    calls = {
        call["id"]
        for call in turn["tool_calls"]
        if call["type"] == "file_search_call" and call["name"] == "file_search"
    }
    assert calls, "The question's saved turn has no server-side file_search call"

    searches = [r for r in turn["tool_results"] if r["type"] == "file_search_call"]
    assert {r["id"] for r in searches} == calls, (
        "Saved file_search result IDs do not match the calls in this turn"
    )
    hits = []
    for search in searches:
        assert search["status"] == "completed", (
            f"file_search status: {search['status']}"
        )
        assert search.get("content"), (
            f"No saved result content for file_search {search['id']}"
        )
        results = json.loads(search["content"]).get("results")
        assert isinstance(results, list), (
            "Saved file_search content has no results list"
        )
        hits.extend(results)
    assert hits, "The matched file_search calls returned zero document hits"
    return hits


class TestOKPVirtualizationFilter:
    @pytest.mark.parametrize("question", VIRTUALIZATION_ADJACENT_QUESTIONS)
    def test_responses_excludes_openshift_virtualization_docs(
        self, client, question, stored_response
    ):
        """Check the documents retrieved by file_search for this question."""
        assert stored_response["status"] == "completed", (
            f"Question {question!r} ended with status {stored_response['status']!r}"
        )
        conversation_id = stored_response["conversation"]
        response = client.get_conversation(conversation_id)
        assert response.status_code == 200, (
            f"GET conversation: HTTP {response.status_code}"
        )
        history = response.json()
        assert history["conversation_id"] == conversation_id, (
            "GET returned a different conversation"
        )
        turns = [
            turn
            for turn in history["chat_history"]
            if any(
                msg["type"] == "user" and msg["content"] == question
                for msg in turn["messages"]
            )
        ]
        assert len(turns) == 1, (
            f"Expected one saved turn for {question!r}, found {len(turns)}"
        )
        results = _saved_search_hits(turns[0])

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

        logging.getLogger(__name__).info(
            "Question %r retrieved paths %s", question, doc_paths
        )
        assert all(doc_paths), f"Question {question!r} returned empty document paths"
        openstack_docs = [path for path in doc_paths if OPENSTACK_DOC_MARKER in path]
        assert openstack_docs, (
            f"Question {question!r} returned no OpenStack-related documents: {doc_paths}"
        )

        leaked = [path for path in doc_paths if VIRTUALIZATION_BOOK_PATH in path]
        assert not leaked, (
            f"Question {question!r} retrieved OpenShift Virtualization docs: {leaked}"
        )

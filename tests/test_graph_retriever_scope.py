import unittest
from unittest.mock import patch

from app.graph_rag.retriever import retrieve_graph_evidence


class TestGraphRetrieverDocumentScope(unittest.TestCase):
    def test_only_uses_entities_and_edges_from_selected_document(
        self
    ):
        with (
            patch(
                "app.graph_rag.retriever.preprocess_query",
                side_effect=lambda query: query,
            ),
            patch(
                "app.graph_rag.retriever.extract_candidate_phrases",
                return_value=[],
            ),
            patch(
                "app.graph_rag.retriever.extract_keywords",
                return_value=["cloud"],
            ),
            patch(
                "app.graph_rag.retriever.match_entities_by_keywords",
                return_value=[
                    {"id": "entity-in-doc", "name": "Cloud", "type": "CONCEPT"},
                    {"id": "entity-outside-doc", "name": "Other", "type": "CONCEPT"},
                ],
            ),
            patch(
                "app.graph_rag.retriever._traverse_one_hop",
                return_value=([], ["entity-in-doc"]),
            ) as traverse_one_hop,
            patch(
                "app.graph_rag.retriever._traverse_multi_hop",
                return_value=([], []),
            ) as traverse_multi_hop,
            patch(
                "app.graph_rag.retriever._fetch_mentions",
                side_effect=[
                    [{"entity_id": "entity-in-doc"}],
                    [{"entity_id": "entity-in-doc"}],
                ],
            ) as fetch_mentions,
        ):
            result = retrieve_graph_evidence(
                "cloud", depth=2, document_id="selected-document"
            )

        self.assertEqual(
            [entity["id"] for entity in result["matched_entities"]],
            ["entity-in-doc"],
        )
        traverse_one_hop.assert_called_once_with(
            ["entity-in-doc"], "selected-document"
        )
        traverse_multi_hop.assert_called_once_with(
            ["entity-in-doc"],
            depth=2,
            document_id="selected-document",
        )
        self.assertEqual(
            fetch_mentions.call_args_list[0].args[1], "selected-document"
        )


if __name__ == "__main__":
    unittest.main()

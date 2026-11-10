import unittest
from unittest.mock import patch, MagicMock

from app.vector_rag.answer import generate_answer, RELEVANCE_THRESHOLD
from app.router.pipeline import route_query, _normalize_response
from app.router.fallback import execute_with_fallback


class TestGeneralFallback(unittest.TestCase):
    @patch("app.hybrid_rag.pipeline.run_hybrid")
    @patch("app.graph_rag.answer.generate_graph_answer")
    @patch("app.vector_rag.answer.generate_answer")
    def test_empty_engine_answer_uses_next_engine(
        self, mock_vector, mock_graph, mock_hybrid
    ):
        mock_vector.return_value = {"answer": None}
        mock_hybrid.return_value = {
            "answer": "General answer",
            "retrieval_method": "general_fallback",
        }

        result = execute_with_fallback(
            engine="vector",
            query="A question",
            document_id=None,
            vector_top_k=5,
            graph_depth=2,
        )

        self.assertEqual(result["engine_used"], "hybrid")
        self.assertTrue(result["fallback_applied"])
        self.assertEqual(result["result"]["answer"], "General answer")
        mock_graph.assert_not_called()

    @patch("app.hybrid_rag.pipeline.run_hybrid")
    @patch("app.graph_rag.answer.generate_graph_answer")
    @patch("app.vector_rag.answer.generate_answer")
    def test_empty_answers_from_all_engines_raise(
        self, mock_vector, mock_graph, mock_hybrid
    ):
        mock_vector.return_value = {"answer": None, "answer_error": "Model unavailable"}
        mock_hybrid.return_value = {"answer": ""}

        with self.assertRaisesRegex(RuntimeError, "Model unavailable"):
            execute_with_fallback(
                engine="vector",
                query="A question",
                document_id=None,
                vector_top_k=5,
                graph_depth=2,
            )
        mock_graph.assert_not_called()

    @patch("app.vector_rag.answer.retrieve_chunks")
    @patch("app.vector_rag.answer.Groq")
    def test_vector_answer_fallback_when_no_relevant_chunks(self, mock_groq_class, mock_retrieve):
        # Return chunks with similarity lower than threshold (0.45)
        mock_retrieve.return_value = [
            {
                "chunk_id": "c1",
                "text": "Some completely unrelated document text",
                "metadata": {"source": "test.pdf", "page_number": 1},
                "similarity": 0.21,
            }
        ]

        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Paris is the capital of France."))
        ]
        mock_completion.usage = MagicMock(prompt_tokens=20, completion_tokens=10, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_completion

        result = generate_answer("What is the capital of France?", top_k=3)

        self.assertEqual(result["retrieval_method"], "general_fallback")
        self.assertEqual(result["fallback_reason"], "no_relevant_chunks")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["answer"], "Paris is the capital of France.")
        self.assertEqual(result["usage"]["total_tokens"], 30)

    @patch("app.vector_rag.answer.retrieve_chunks")
    @patch("app.vector_rag.answer.Groq")
    def test_vector_answer_normal_when_relevant_chunks_exist(self, mock_groq_class, mock_retrieve):
        # Return chunks with similarity >= threshold
        mock_retrieve.return_value = [
            {
                "chunk_id": "c1",
                "text": "Cloud computing is the on-demand availability of computer system resources.",
                "metadata": {"source": "cloud.pdf", "page_number": 2, "document_id": "doc-123"},
                "similarity": 0.78,
            }
        ]

        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Cloud computing provides on-demand resources [S1]."))
        ]
        mock_completion.usage = MagicMock(prompt_tokens=50, completion_tokens=15, total_tokens=65)
        mock_client.chat.completions.create.return_value = mock_completion

        result = generate_answer("What is cloud computing?", top_k=3)

        self.assertEqual(result["retrieval_method"], "vector")
        self.assertNotIn("fallback_reason", result)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["source_id"], "S1")
        self.assertEqual(result["sources"][0]["similarity"], 0.78)

    @patch("app.vector_rag.answer.retrieve_chunks")
    @patch("app.vector_rag.answer.Groq")
    def test_vector_answer_rejects_empty_model_response(
        self, mock_groq_class, mock_retrieve
    ):
        mock_retrieve.return_value = [
            {
                "chunk_id": "c1",
                "text": "Cloud computing provides on-demand resources.",
                "metadata": {"source": "cloud.pdf", "page_number": 2},
                "similarity": 0.78,
            }
        ]
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="  "))
        ]

        with self.assertRaisesRegex(RuntimeError, "empty answer"):
            generate_answer("What is cloud computing?")

    @patch("app.router.pipeline.execute_with_fallback")
    @patch("app.router.pipeline.analyze_query")
    @patch("app.router.pipeline.classify_intent")
    @patch("app.router.pipeline.analyze_complexity")
    @patch("app.router.pipeline.decide_engine")
    def test_route_query_passes_general_fallback(
        self,
        mock_decide,
        mock_complexity,
        mock_intent,
        mock_analyze,
        mock_exec,
    ):
        mock_analyze.return_value = {
            "entity_count": 0,
            "entity_candidates": [],
            "relationship_hits": [],
            "semantic_hits": [],
            "multihop_hits": [],
            "comparison_hits": [],
            "summary_hits": [],
        }
        mock_intent.return_value = {
            "intent": "definition",
            "requires_graph": False,
            "requires_vector": True,
            "requires_multihop": False,
        }
        mock_complexity.return_value = {
            "entity_density": 0.0,
            "relationship_complexity": 0.0,
            "estimated_hops": 0,
            "overall_complexity": "low",
        }
        mock_decide.return_value = {
            "selected_engine": "vector",
            "confidence": 0.8,
            "reason": "Definition query matches vector search",
            "scores": {"vector": 0.8, "graph": 0.0, "hybrid": 0.1},
        }

        mock_exec.return_value = {
            "engine_used": "vector",
            "fallback_applied": False,
            "fallback_reason": None,
            "result": {
                "answer": "General knowledge answer here.",
                "sources": [],
                "retrieval_method": "general_fallback",
                "fallback_reason": "no_relevant_chunks",
                "model": "llama-3.3-70b-versatile",
                "usage": {"total_tokens": 40},
            },
        }

        res = route_query("Tell me about quantum gravity")

        self.assertEqual(res["retrieval_method"], "general_fallback")
        self.assertEqual(res["fallback_reason"], "no_relevant_chunks")
        self.assertTrue(res["routing"]["fallback_applied"])
        self.assertEqual(res["routing"]["fallback_reason"], "no_relevant_chunks")
        self.assertEqual(res["sources"], [])


if __name__ == "__main__":
    unittest.main()

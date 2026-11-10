import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from app.evaluation.service import (
    get_evaluation_run,
    list_evaluation_runs,
    run_evaluation,
    token_f1,
)


class TestEvaluationService(unittest.TestCase):
    def test_token_f1_uses_token_overlap(self):
        self.assertEqual(token_f1("OS manages computer hardware", "OS manages hardware"), 0.8571)
        self.assertEqual(token_f1("expected words", "unrelated answer"), 0.0)
        self.assertEqual(token_f1("expected words", ""), 0.0)

    def test_run_saves_case_results_and_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "evaluation.sqlite3"

            @contextmanager
            def open_test_database():
                connection = sqlite3.connect(database_path)
                connection.row_factory = sqlite3.Row
                try:
                    yield connection
                finally:
                    connection.close()

            with (
                patch(
                    "app.evaluation.service.get_connection",
                    side_effect=open_test_database,
                ),
                patch(
                    "app.evaluation.service.route_query",
                    side_effect=[
                        {
                            "answer": "An operating system manages hardware.",
                            "sources": [
                                {
                                    "document_id": "doc-1",
                                    "filename": "os.pdf",
                                }
                            ],
                            "retrieval_method": "vector",
                            "engine_used": "vector",
                            "model": "test-model",
                            "usage": {"total_tokens": 12},
                        },
                        RuntimeError("test provider failure"),
                    ],
                ),
            ):
                with open_test_database() as connection:
                    connection.execute(
                        """
                        CREATE TABLE evaluation_runs (
                            id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            case_count INTEGER NOT NULL,
                            summary_json TEXT NOT NULL,
                            results_json TEXT NOT NULL
                        )
                        """
                    )

                run = run_evaluation(
                    [
                        {
                            "query": "What does an operating system do?",
                            "expected_answer": "An operating system manages hardware.",
                            "document_id": "doc-1",
                        },
                        {"query": "A failing model query"},
                    ]
                )

                self.assertEqual(run["summary"]["total_cases"], 2)
                self.assertEqual(run["summary"]["answered_cases"], 1)
                self.assertEqual(run["summary"]["answer_rate"], 0.5)
                self.assertEqual(run["summary"]["mean_answer_f1"], 1.0)
                self.assertEqual(run["summary"]["evidence_rate"], 0.5)
                self.assertEqual(run["summary"]["document_hit_rate"], 1.0)
                self.assertEqual(run["summary"]["total_tokens"], 12)
                self.assertEqual(run["results"][1]["status"], "error")
                self.assertEqual(
                    run["results"][1]["error"], "test provider failure"
                )
                self.assertEqual(get_evaluation_run(run["id"]), run)
                self.assertEqual(list_evaluation_runs()[0]["id"], run["id"])


if __name__ == "__main__":
    unittest.main()

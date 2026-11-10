import unittest
from app.router.model_selector import assess_question_burden


class TestModelSelector(unittest.TestCase):
    def test_low_burden_selection(self):
        result = assess_question_burden("What is the capital of Japan?")
        self.assertEqual(result["burden"], "low")
        self.assertIn("20b", result["model"])

    def test_medium_burden_selection(self):
        result = assess_question_burden("Explain how DNS resolution works and its main steps.")
        self.assertEqual(result["burden"], "medium")
        self.assertIn("27b", result["model"])

    def test_high_burden_selection(self):
        result = assess_question_burden(
            "Compare and explain in detail the architecture differences between monolithic and microservices with pros and cons."
        )
        self.assertEqual(result["burden"], "high")
        self.assertIn("120b", result["model"])


if __name__ == "__main__":
    unittest.main()


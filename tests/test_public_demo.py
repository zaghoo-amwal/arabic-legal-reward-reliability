"""Offline tests; no network, credentials or private dataset required."""
import os
import unittest
from unittest.mock import patch
from legal_rlvr import grade, list_tasks, load_task
from legal_rlvr.normalize import normalize
from legal_rlvr.client import make_client


class PublicDemoTests(unittest.TestCase):
    def test_corpus_is_explicitly_synthetic(self):
        self.assertEqual(list_tasks(), ["synthetic_notice"])
        task, rubric, _ = load_task("synthetic_notice")
        self.assertEqual(task["prompt_provenance"]["status"], "synthetic")
        self.assertEqual(len(rubric["items"]), 7)

    def test_arabic_normalization(self):
        self.assertIn("الماده 173", normalize("المادة الثالثة والسبعون بعد المائة"))
        self.assertIn("36000", normalize("٣٦٬٠٠٠"))

    def test_negative_control_scores_lower(self):
        _, _, ref = load_task("synthetic_notice")
        self.assertGreater(grade("synthetic_notice", ref).reward,
                           grade("synthetic_notice", "Unrelated response").reward)

    def test_known_negation_failure_is_reproduced(self):
        _, _, ref = load_task("synthetic_notice")
        negated = grade("synthetic_notice", ref)
        asserted = grade("synthetic_notice", ref.replace("لا يطالب", "يطالب"))
        self.assertEqual(negated.reward, 0.375)
        self.assertEqual(negated.gate_factor, 0.5)
        self.assertEqual(negated.reward, asserted.reward)
        # Equal scores are the demonstrated defect, not a correctness assertion.

    def test_rules_only_omits_api_dependency(self):
        with patch.dict(os.environ, {}, clear=True):
            _, _, ref = load_task("synthetic_notice")
            self.assertIsInstance(grade("synthetic_notice", ref).reward, float)

    def test_missing_key_error_contains_no_key_or_local_path(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Set ANTHROPIC_API_KEY"):
                make_client()


if __name__ == "__main__":
    unittest.main()

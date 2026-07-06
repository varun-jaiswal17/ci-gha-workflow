#!/usr/bin/env python3

"""Unit and integration tests for :mod:`ci_intel.scheduler.labels`.

Runs on the standard library only::

    python3 -m unittest ci_intel.tests.test_labels -v
"""

import unittest
from pathlib import Path

from ci_intel.scheduler.labels import (
    LabelMatcher,
    PrioritizationResult,
    prioritize_workflows,
)

# A small, representative slice of the real .github/workflows/ names. Chosen so
# that several interesting edge cases are present:
#   * W10-ARM64    -> matches BOTH priority:windows and priority:ARM
#   * macOS-ARM64  -> matches BOTH priority:mac and priority:ARM
#   * loongarch64  -> must NOT match priority:ARM (LoongArch, not ARM)
#   * O22-CANN     -> a Linux build that is neither Ubuntu nor "Linux" in name
#   * iOS          -> grouped under priority:mac
#   * CodeQL       -> a platform-agnostic workflow that matches nothing
SAMPLE_WORKFLOWS = [
    "OCV-PR-5.x-W10.yaml",
    "OCV-PR-5.x-W10-Vulkan.yaml",
    "OCV-PR-5.x-W10-ARM64.yaml",
    "OCV-PR-5.x-U20-Cuda.yaml",
    "OCV-Contrib-PR-4.x-O22-CANN.yaml",
    "OCV-PR-5.x-macOS-ARM64.yaml",
    "OCV-PR-5.x-ARM64.yaml",
    "OCV-PR-5.x-iOS.yaml",
    "OCV-PR-4.x-loongnix-loongarch64.yaml",
    "OCV-CodeQL.yaml",
]


class ConfigLoadingTest(unittest.TestCase):
    def setUp(self):
        self.matcher = LabelMatcher.from_config()

    def test_expected_labels_present(self):
        self.assertEqual(
            set(self.matcher.labels),
            {"priority:windows", "priority:linux", "priority:ARM",
             "priority:mac", "priority:ALL"},
        )

    def test_keywords_are_loaded(self):
        self.assertIn("w10", self.matcher.keywords_for_label("priority:windows"))

    def test_all_label_is_wildcard(self):
        self.assertIsNone(self.matcher.keywords_for_label("priority:ALL"))


class LabelClassificationTest(unittest.TestCase):
    def setUp(self):
        self.matcher = LabelMatcher.from_config()

    def test_priority_prefix_detected(self):
        self.assertTrue(self.matcher.is_priority_label("priority:windows"))
        self.assertFalse(self.matcher.is_priority_label("category:dnn_timvx"))

    def test_known_label_lookup_is_case_insensitive(self):
        self.assertTrue(self.matcher.is_known_label("PRIORITY:Windows"))
        self.assertTrue(self.matcher.is_known_label("priority:arm"))  # config has ARM

    def test_unknown_priority_label_is_not_known(self):
        self.assertTrue(self.matcher.is_priority_label("priority:banana"))
        self.assertFalse(self.matcher.is_known_label("priority:banana"))


class MatchesTest(unittest.TestCase):
    def setUp(self):
        self.matcher = LabelMatcher.from_config()

    def test_substring_match(self):
        self.assertTrue(self.matcher.matches("priority:windows", "OCV-PR-5.x-W10.yaml"))
        self.assertFalse(self.matcher.matches("priority:windows", "OCV-PR-5.x-iOS.yaml"))

    def test_match_is_case_insensitive_both_ways(self):
        # Upper-cased label and lower-cased file name both still match.
        self.assertTrue(self.matcher.matches("PRIORITY:WINDOWS", "ocv-pr-5.x-w10.yaml"))

    def test_wildcard_matches_anything(self):
        self.assertTrue(self.matcher.matches("priority:ALL", "OCV-CodeQL.yaml"))

    def test_win_keyword_covers_winpack_and_windows_file(self):
        self.assertTrue(self.matcher.matches("priority:windows", "OCV-WinPack-5.x-W10.yaml"))
        self.assertTrue(self.matcher.matches("priority:windows", "OCV-PR-Windows.yaml"))


class PrioritizeTest(unittest.TestCase):
    def setUp(self):
        self.matcher = LabelMatcher.from_config()

    def test_no_priority_labels_keeps_everything_deprioritized(self):
        result = self.matcher.prioritize(["category:dnn"], SAMPLE_WORKFLOWS)
        self.assertEqual(result.requested, ())
        self.assertEqual(result.prioritized, ())
        self.assertEqual(list(result.deprioritized), SAMPLE_WORKFLOWS)
        self.assertEqual(result.ordered, SAMPLE_WORKFLOWS)
        self.assertFalse(result.match_all)

    def test_windows_prioritizes_w10_workflows_in_input_order(self):
        result = self.matcher.prioritize(["priority:windows"], SAMPLE_WORKFLOWS)
        self.assertEqual(
            list(result.prioritized),
            [
                "OCV-PR-5.x-W10.yaml",
                "OCV-PR-5.x-W10-Vulkan.yaml",
                "OCV-PR-5.x-W10-ARM64.yaml",
            ],
        )

    def test_prioritized_come_first_and_partition_is_total(self):
        result = self.matcher.prioritize(["priority:mac"], SAMPLE_WORKFLOWS)
        self.assertEqual(set(result.ordered), set(SAMPLE_WORKFLOWS))
        self.assertEqual(len(result.ordered), len(SAMPLE_WORKFLOWS))
        # The macOS + iOS files lead the order.
        self.assertEqual(
            result.ordered[:2],
            ["OCV-PR-5.x-macOS-ARM64.yaml", "OCV-PR-5.x-iOS.yaml"],
        )

    def test_mac_label_includes_ios(self):
        result = self.matcher.prioritize(["priority:mac"], SAMPLE_WORKFLOWS)
        self.assertIn("OCV-PR-5.x-iOS.yaml", result.prioritized)
        self.assertIn("OCV-PR-5.x-macOS-ARM64.yaml", result.prioritized)

    def test_linux_label_includes_openeuler_and_loongnix(self):
        # The keyword-list adjustment: O22 (openEuler) and loongnix are Linux.
        result = self.matcher.prioritize(["priority:linux"], SAMPLE_WORKFLOWS)
        self.assertIn("OCV-Contrib-PR-4.x-O22-CANN.yaml", result.prioritized)
        self.assertIn("OCV-PR-4.x-loongnix-loongarch64.yaml", result.prioritized)
        self.assertIn("OCV-PR-5.x-U20-Cuda.yaml", result.prioritized)

    def test_arm_matches_windows_arm_and_mac_arm_but_not_loongarch(self):
        result = self.matcher.prioritize(["priority:ARM"], SAMPLE_WORKFLOWS)
        self.assertIn("OCV-PR-5.x-W10-ARM64.yaml", result.prioritized)
        self.assertIn("OCV-PR-5.x-macOS-ARM64.yaml", result.prioritized)
        self.assertIn("OCV-PR-5.x-ARM64.yaml", result.prioritized)
        self.assertNotIn("OCV-PR-4.x-loongnix-loongarch64.yaml", result.prioritized)

    def test_all_label_prioritizes_everything(self):
        result = self.matcher.prioritize(["priority:ALL"], SAMPLE_WORKFLOWS)
        self.assertTrue(result.match_all)
        self.assertEqual(list(result.prioritized), SAMPLE_WORKFLOWS)
        self.assertEqual(result.deprioritized, ())

    def test_multiple_labels_take_the_union(self):
        result = self.matcher.prioritize(
            ["priority:windows", "priority:mac"], SAMPLE_WORKFLOWS
        )
        self.assertEqual(
            set(result.prioritized),
            {
                "OCV-PR-5.x-W10.yaml",
                "OCV-PR-5.x-W10-Vulkan.yaml",
                "OCV-PR-5.x-W10-ARM64.yaml",
                "OCV-PR-5.x-macOS-ARM64.yaml",
                "OCV-PR-5.x-iOS.yaml",
            },
        )

    def test_workflow_matching_two_labels_appears_once(self):
        # W10-ARM64 matches both windows and ARM but must not be duplicated.
        result = self.matcher.prioritize(
            ["priority:windows", "priority:ARM"], SAMPLE_WORKFLOWS
        )
        self.assertEqual(list(result.prioritized).count("OCV-PR-5.x-W10-ARM64.yaml"), 1)

    def test_requested_dedupes_and_preserves_order(self):
        result = self.matcher.prioritize(
            ["priority:ARM", "priority:windows", "priority:arm", "category:x"],
            SAMPLE_WORKFLOWS,
        )
        # 'priority:arm' is a case-insensitive duplicate of 'priority:ARM'.
        self.assertEqual(result.requested, ("priority:ARM", "priority:windows"))

    def test_unknown_priority_label_reported_but_inert(self):
        result = self.matcher.prioritize(["priority:banana"], SAMPLE_WORKFLOWS)
        self.assertEqual(result.unknown, ("priority:banana",))
        self.assertEqual(result.prioritized, ())

    def test_matched_by_breakdown(self):
        result = self.matcher.prioritize(
            ["priority:windows", "priority:ARM"], SAMPLE_WORKFLOWS
        )
        self.assertEqual(
            result.matched_by["priority:windows"],
            ("OCV-PR-5.x-W10.yaml", "OCV-PR-5.x-W10-Vulkan.yaml", "OCV-PR-5.x-W10-ARM64.yaml"),
        )
        self.assertEqual(
            result.matched_by["priority:ARM"],
            ("OCV-PR-5.x-W10-ARM64.yaml", "OCV-PR-5.x-macOS-ARM64.yaml", "OCV-PR-5.x-ARM64.yaml"),
        )

    def test_returns_result_type(self):
        self.assertIsInstance(self.matcher.prioritize([], SAMPLE_WORKFLOWS), PrioritizationResult)

    def test_one_shot_helper_matches_class_api(self):
        helper = prioritize_workflows(["priority:windows"], SAMPLE_WORKFLOWS)
        direct = self.matcher.prioritize(["priority:windows"], SAMPLE_WORKFLOWS)
        self.assertEqual(helper.ordered, direct.ordered)


def _real_workflows_dir():
    # ci_intel/tests/test_labels.py -> repo root is three parents up.
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / ".github" / "workflows"


@unittest.skipUnless(_real_workflows_dir().is_dir(), "real .github/workflows not present")
class RealWorkflowsIntegrationTest(unittest.TestCase):
    """Validate the bundled config.yaml against the actual workflow file set."""

    @classmethod
    def setUpClass(cls):
        cls.matcher = LabelMatcher.from_config()
        cls.workflows = sorted(
            p.name for p in _real_workflows_dir().iterdir()
            if p.suffix in (".yml", ".yaml")
        )

    def test_partition_is_complete_and_disjoint(self):
        result = self.matcher.prioritize(["priority:windows"], self.workflows)
        self.assertEqual(sorted(result.ordered), sorted(self.workflows))
        self.assertEqual(set(result.prioritized) & set(result.deprioritized), set())

    def test_windows_matches_exactly_the_substring_matches(self):
        result = self.matcher.prioritize(["priority:windows"], self.workflows)
        expected = {
            wf for wf in self.workflows
            if any(k in wf.lower() for k in ("w10", "win", "windows"))
        }
        self.assertEqual(set(result.prioritized), expected)
        self.assertTrue(expected, "sanity: there should be Windows workflows")

    def test_all_label_matches_every_real_workflow(self):
        result = self.matcher.prioritize(["priority:ALL"], self.workflows)
        self.assertEqual(set(result.prioritized), set(self.workflows))
        self.assertEqual(result.deprioritized, ())

    def test_every_non_wildcard_label_matches_at_least_one_real_workflow(self):
        # Guards against a config keyword drifting away from real file names.
        for label in self.matcher.labels:
            if self.matcher.keywords_for_label(label) is None:
                continue  # skip the wildcard
            result = self.matcher.prioritize([label], self.workflows)
            self.assertTrue(
                result.prioritized,
                f"{label} matched no real workflow -- stale keyword in config.yaml?",
            )


if __name__ == "__main__":
    unittest.main()

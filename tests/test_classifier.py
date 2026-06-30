"""
Tests for the classifier layer — pure Python, no network, no git.
Run with:  pytest tests/test_classifier.py -v
"""
from pathlib import Path

import pytest

from ci_intel.classifier.classify import classify
from ci_intel.classifier.signatures import normalize, signature

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------

class TestSignatures:
    def test_strips_hex_addresses(self):
        n = normalize("crash at 0x7fff1234abcd in libopencv")
        assert "0x" not in n
        assert "<addr>" in n

    def test_strips_bare_numbers(self):
        n = normalize("line 42: undefined reference")
        assert "42" not in n
        assert "<n>" in n

    def test_strips_unix_paths(self):
        n = normalize("/home/runner/work/opencv/modules/core/src/matrix.cpp:10")
        assert "/home" not in n
        assert "<path>" in n

    def test_same_line_same_hash(self):
        sig1 = signature("error: undefined reference to `cv::Mat::Mat()'")
        sig2 = signature("error: undefined reference to `cv::Mat::Mat()'")
        assert sig1 == sig2
        assert len(sig1) == 12

    def test_address_variation_collapses(self):
        # Two runs with different stack addresses → same signature
        assert signature("crash at 0x7fff0001") == signature("crash at 0x7fff9999")

    def test_different_errors_different_hashes(self):
        assert signature("error: undefined reference") != signature("out of memory")


# ---------------------------------------------------------------------------
# Classifier — category detection
# ---------------------------------------------------------------------------

class TestClassifyCategory:
    def test_infra_oom_keyword(self):
        log = (FIXTURES / "log_oom.txt").read_text()
        v = classify("failure", None, log, None)
        assert v["category"] == "INFRA"

    def test_infra_exit137(self):
        v = classify("failure", None, "process terminated\nexit code 137", None)
        assert v["category"] == "INFRA"

    def test_build_from_log(self):
        log = (FIXTURES / "log_build_fail.txt").read_text()
        v = classify("failure", None, log, None)
        assert v["category"] == "BUILD"

    def test_test_from_log(self):
        log = (FIXTURES / "log_test_fail.txt").read_text()
        v = classify("failure", None, log, None)
        assert v["category"] == "TEST"

    def test_cancelled(self):
        v = classify("cancelled", None, "", None)
        assert v["category"] == "CANCELLED"

    def test_unknown_on_no_match(self):
        v = classify("failure", None, "job runner exited unexpectedly", None)
        assert v["category"] == "UNKNOWN"

    def test_config_keyerror(self):
        v = classify("failure", None, "KeyError in runner.py: 'suite'", None)
        assert v["category"] == "CONFIG"


# ---------------------------------------------------------------------------
# Classifier — note/warning lines are not used as match targets
# ---------------------------------------------------------------------------

class TestNoiseSuppression:
    def test_note_prefix_skipped(self):
        # An ASan note that looks scary should not cause a BUILD classification
        # if there is a real error line after it
        log = (
            "note: variable tracking size limit exceeded with -fvar-tracking-assignments\n"
            "error: actual build error here"
        )
        v = classify("failure", None, log, None)
        assert v["matched_line"] != "note: variable tracking size limit exceeded with -fvar-tracking-assignments"
        assert v["category"] == "BUILD"

    def test_note_only_log_is_unknown(self):
        log = "note: something informational\nwarning: another note"
        v = classify("failure", None, log, None)
        assert v["category"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# Classifier — structured results JSON takes priority over log scanning
# ---------------------------------------------------------------------------

class TestStructuredResults:
    RESULTS = {
        "plan": "test-plan.json",
        "overall_pass": False,
        "binaries": [
            {"binary": "opencv_test_core", "module": "core",
             "passed": False, "log_file": "out_opencv_test_core.txt"},
            {"binary": "opencv_test_imgproc", "module": "imgproc",
             "passed": True, "log_file": "out_opencv_test_imgproc.txt"},
        ],
    }

    def test_detects_test_from_structured_json(self):
        v = classify("failure", "Run tests", "", self.RESULTS)
        assert v["category"] == "TEST"
        assert v["module"] == "core"
        assert "opencv_test_core" in v["failing_tests"]
        assert "opencv_test_imgproc" not in v["failing_tests"]

    def test_structured_json_overrides_build_log(self):
        # Even if the log looks like a BUILD failure, the structured JSON result
        # (which says a test binary failed) takes precedence.
        build_log = "error: undefined reference to `foo'"
        v = classify("failure", None, build_log, self.RESULTS)
        assert v["category"] == "TEST"

    def test_all_passing_structured_json_falls_back_to_log(self):
        all_pass = {
            "plan": "test-plan.json",
            "overall_pass": True,
            "binaries": [
                {"binary": "opencv_test_core", "module": "core",
                 "passed": True, "log_file": "out_opencv_test_core.txt"},
            ],
        }
        build_log = "error: undefined reference"
        v = classify("failure", None, build_log, all_pass)
        # No failed binary → structured results don't fire → falls through to log rules
        assert v["category"] == "BUILD"


# ---------------------------------------------------------------------------
# Classifier — return-value structure
# ---------------------------------------------------------------------------

class TestReturnStructure:
    def test_all_keys_present(self):
        v = classify("failure", None, "error: something went wrong", None)
        for key in ("category", "module", "error_signature", "failing_tests", "matched_line"):
            assert key in v

    def test_error_signature_is_12_chars(self):
        v = classify("failure", None, "error: undefined reference", None)
        assert v["error_signature"] is not None
        assert len(v["error_signature"]) == 12

    def test_unknown_has_none_signature(self):
        v = classify("failure", None, "some obscure unmatched output", None)
        assert v["category"] == "UNKNOWN"
        assert v["error_signature"] is None

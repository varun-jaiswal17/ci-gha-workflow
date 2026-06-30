"""
Orchestrator: walks the rule cascade and returns a structured fact dict.

Return value keys:
  category        — INFRA / CONFIG / TEST / BUILD / UNKNOWN / CANCELLED
  module          — opencv module name (e.g. "core", "imgproc") or None
  error_signature — 12-char stable hash of the matched line, or None
  failing_tests   — list of binary names that failed (from structured results)
  matched_line    — the raw log line that triggered the rule, or None
"""
# Higher number = more severe / higher priority for run-level reporting
CATEGORY_PRIORITY = {
    "INFRA": 5,
    "BUILD": 4,
    "CONFIG": 3,
    "TEST": 2,
    "UNKNOWN": 1,
    "CANCELLED": 0,
    None: -1,
}

from ci_intel.classifier.rules import COMPILED_RULES, IGNORE_PREFIXES
from ci_intel.classifier.signatures import signature


def classify(conclusion, failing_step, log_text, results_json=None):
    if conclusion == "cancelled":
        return _fact("CANCELLED", None, None, [], None)

    # Structured results JSON is the most reliable signal for TEST failures.
    # Check it before scanning raw logs so we don't misclassify a failed binary
    # as BUILD because its error line matched a build rule.
    failing_tests = []
    module = None
    if isinstance(results_json, dict):
        failed_bins = [b for b in results_json.get("binaries", []) if not b.get("passed")]
        if failed_bins:
            failing_tests = [b["binary"] for b in failed_bins]
            module = failed_bins[0].get("module")
            sig = signature(failing_tests[0])
            return _fact("TEST", module, sig, failing_tests, failing_tests[0])

    # Fall back to scanning raw log lines through the rule cascade.
    for line in log_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in IGNORE_PREFIXES):
            continue
        for category, patterns in COMPILED_RULES:
            for pat in patterns:
                if pat.search(line):
                    return _fact(category, module, signature(line), failing_tests, line)

    return _fact("UNKNOWN", None, None, [], None)


def _fact(category, module, error_sig, failing_tests, matched_line):
    return {
        "category": category,
        "module": module,
        "error_signature": error_sig,
        "failing_tests": failing_tests,
        "matched_line": matched_line,
    }

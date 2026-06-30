"""
Ordered rule cascade for classifying CI failure log lines.
Rules are checked in order; first match on a non-noise line wins.
"""
import re

RULES = [
    # 1. INFRA — runner or environment died before tests could run
    ("INFRA", [
        r"out of memory",
        r"\bKilled\b",
        r"exit( code)? 137",
        r"docker pull (failed|error)",
        r"DNS (resolution )?fail",
        r"Connection timed out",
        r"runner has received a shutdown signal",
        r"The runner has stopped",
        r"No space left on device",
        r"OOMKilled",
    ]),
    # 2. CONFIG — pipeline misconfiguration, not a code failure
    ("CONFIG", [
        r"KeyError.*runner\.py",
        r"YAML parse error",
        r"SyntaxError.*runner\.py",
        r"required input .* not provided",
        r"Input required and not supplied",
        r"Environment variable .* is not set",
        r"secrets\.\w+ .* not set",
    ]),
    # 3. TEST — real test regression detected in structured results or gtest output
    ("TEST", [
        r"\[  FAILED  \]",
        r"opencv_(?:test|perf)_\w+ FAILED",
        r"FAILED \d+ tests?",
    ]),
    # 4. BUILD — compile or link failure
    ("BUILD", [
        r"\berror:",
        r"undefined reference",
        r"CMake Error",
        r"FAILED:.*\.(?:o|obj)\b",
        r"ninja: build stopped",
        r"make.*\bError\b",
        r"cannot find -l\w+",
        r"ld returned \d+ exit status",
    ]),
]

# Lines starting with these prefixes are noise — ASan/compiler notes that look
# like errors but accompany successful builds.
IGNORE_PREFIXES = (
    "note:",
    "warning:",
    "  note:",
    "  warning:",
    "\tnote:",
    "\twarning:",
)


def compile_rules():
    return [
        (cat, [re.compile(p, re.IGNORECASE) for p in patterns])
        for cat, patterns in RULES
    ]


COMPILED_RULES = compile_rules()

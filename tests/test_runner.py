"""
Tests for scripts/runner.py — specifically the --results-json output.
Runs the real runner.py as a subprocess with a fake binary.
Run with:  pytest tests/test_runner.py -v
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

# Fake test binaries — these mimic gtest stdout format

PASSING_BINARY = textwrap.dedent("""\
    #!/usr/bin/env python3
    print("[ RUN      ] Suite.test1")
    print("[       OK ] Suite.test1 (1 ms)")
    print("[----------] Global test environment tear-down")
""")

FAILING_BINARY = textwrap.dedent("""\
    #!/usr/bin/env python3
    print("[ RUN      ] Suite.test1")
    print("[  FAILED  ] Suite.test1 (1 ms)")
    print("[----------] Global test environment tear-down")
    raise SystemExit(1)
""")

TEST_PLAN = json.dumps({
    "suites": {"default": ["opencv_test_core"]},
    "options": {"default": {}},
    "filters": {},
})


@pytest.fixture()
def workdir(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "test-plan.json").write_text(TEST_PLAN)
    return tmp_path


def write_binary(workdir, src):
    b = workdir / "bin" / "opencv_test_core"
    b.write_text(src)
    b.chmod(0o755)


def run_runner(workdir, extra=(), expect_pass=None):
    result_json = workdir / "logs" / "results.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "runner.py"),
        f"--plan={workdir}/scripts/test-plan.json",
        "--suite=default",
        f"--workdir={workdir}",
        "--bindir=bin",
        f"--logdir={workdir}/logs",
        f"--results-json={result_json}",
    ] + list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if expect_pass is not None:
        assert (proc.returncode == 0) == expect_pass, \
            f"Unexpected exit code {proc.returncode}.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    return proc, result_json


class TestResultsJson:
    def test_passing_binary_writes_json(self, workdir):
        write_binary(workdir, PASSING_BINARY)
        _, rj = run_runner(workdir, expect_pass=True)
        assert rj.exists(), "results.json was not created"
        data = json.loads(rj.read_text())
        assert data["overall_pass"] is True
        assert len(data["binaries"]) == 1
        assert data["binaries"][0]["passed"] is True

    def test_failing_binary_writes_json(self, workdir):
        write_binary(workdir, FAILING_BINARY)
        _, rj = run_runner(workdir, expect_pass=False)
        assert rj.exists(), "results.json was not created even on failure"
        data = json.loads(rj.read_text())
        assert data["overall_pass"] is False
        assert data["binaries"][0]["passed"] is False

    def test_module_extraction(self, workdir):
        write_binary(workdir, PASSING_BINARY)
        _, rj = run_runner(workdir, expect_pass=True)
        data = json.loads(rj.read_text())
        b = data["binaries"][0]
        assert b["binary"] == "opencv_test_core"
        assert b["module"] == "core"   # "opencv_test_" prefix stripped

    def test_log_file_field(self, workdir):
        write_binary(workdir, PASSING_BINARY)
        _, rj = run_runner(workdir, expect_pass=True)
        data = json.loads(rj.read_text())
        assert data["binaries"][0]["log_file"] == "out_opencv_test_core.txt"

    def test_plan_field_present(self, workdir):
        write_binary(workdir, PASSING_BINARY)
        _, rj = run_runner(workdir, expect_pass=True)
        data = json.loads(rj.read_text())
        assert "plan" in data
        assert "test-plan.json" in data["plan"]

    def test_no_flag_no_json(self, workdir):
        """Without --results-json the file must not be created (backwards compat)."""
        write_binary(workdir, PASSING_BINARY)
        result_json = workdir / "logs" / "results.json"
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "runner.py"),
            f"--plan={workdir}/scripts/test-plan.json",
            "--suite=default",
            f"--workdir={workdir}",
            "--bindir=bin",
            f"--logdir={workdir}/logs",
        ]
        subprocess.run(cmd, capture_output=True)
        assert not result_json.exists(), "--results-json not passed but file was created"

    def test_missing_binary_is_not_passed(self, workdir):
        """A missing binary (res = -3) must appear as passed=False, not True."""
        # Do NOT write the binary — let runner find it missing
        _, rj = run_runner(workdir)   # will exit non-zero
        assert rj.exists()
        data = json.loads(rj.read_text())
        assert data["binaries"][0]["passed"] is False

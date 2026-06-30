import io
import os
import zipfile

import requests

API = "https://api.github.com"


class GitHubClient:
    def __init__(self, repo, token=None):
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.s = requests.Session()
        self.s.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _get(self, path, **kw):
        r = self.s.get(f"{API}/repos/{self.repo}{path}", timeout=30, **kw)
        r.raise_for_status()
        return r

    def get_run(self, run_id):
        return self._get(f"/actions/runs/{run_id}").json()

    def list_jobs(self, run_id):
        return self._get(f"/actions/runs/{run_id}/jobs").json().get("jobs", [])

    def get_logs_zip(self, run_id):
        r = self._get(f"/actions/runs/{run_id}/logs")
        return zipfile.ZipFile(io.BytesIO(r.content))

    def list_artifacts(self, run_id):
        return self._get(f"/actions/runs/{run_id}/artifacts").json().get("artifacts", [])

    def download_artifact_zip(self, artifact_id):
        r = self._get(f"/actions/artifacts/{artifact_id}/zip")
        return zipfile.ZipFile(io.BytesIO(r.content))

    def list_workflows(self):
        return self._get("/actions/workflows").json().get("workflows", [])

    def find_workflow_id(self, name):
        """Return numeric workflow ID for a display name, or None if not found."""
        for wf in self.list_workflows():
            if wf.get("name") == name:
                return wf["id"]
        return None

    def list_workflow_runs(self, workflow_id, days=90, status="completed"):
        """
        Yield all completed runs for a workflow within the last N days.
        Handles pagination automatically.
        """
        from datetime import datetime, timezone, timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        page = 1
        per_page = 100
        while True:
            data = self._get(
                f"/actions/workflows/{workflow_id}/runs",
                params={
                    "status": status,
                    "created": f">{since}",
                    "per_page": per_page,
                    "page": page,
                },
            ).json()
            runs = data.get("workflow_runs", [])
            yield from runs
            if len(runs) < per_page:
                break
            page += 1

    def workflow_dispatch(self, workflow_id, ref, inputs=None):
        """Fire a workflow_dispatch event. Requires a token with workflow scope."""
        r = self.s.post(
            f"{API}/repos/{self.repo}/actions/workflows/{workflow_id}/dispatches",
            json={"ref": ref, "inputs": inputs or {}},
            timeout=30,
        )
        r.raise_for_status()

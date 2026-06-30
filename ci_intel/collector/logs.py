"""Shared log extraction from GitHub run-level log ZIPs."""


def fetch_job_logs(logs_zip, job):
    """
    Extract the log text for one job from a GitHub run-level log ZIP.

    GitHub ZIPs contain two formats simultaneously:
      - Flat root file:  "1_BuildAndTest.txt"   ← complete job log, preferred
      - Folder entries:  "BuildAndTest/1_step.txt", "BuildAndTest/2_step.txt", ...

    Strategy (first non-empty result wins):
      1. Flat root file ending with  _{job_name}.txt
      2. Folder prefix               JobName/
      3. Underscore-escaped folder   Job_Name/
      4. Case-insensitive substring  (last resort)

    Prints a warning with actual ZIP entries if nothing matched,
    so the matching logic can be corrected.
    """
    job_name = job.get("name", "")

    texts = _extract_flat_root(logs_zip, job_name)
    if not texts:
        texts = _extract_prefix(logs_zip, job_name + "/")
    if not texts:
        texts = _extract_prefix(logs_zip, job_name.replace(" ", "_") + "/")
    if not texts:
        texts = _extract_substring(logs_zip, job_name)
    if not texts:
        top_level = sorted({e.split("/")[0] for e in logs_zip.namelist()})
        print(
            f"    warn: no log text found for job={job_name!r}. "
            f"ZIP top-level entries: {top_level[:10]}"
        )
    return "\n".join(texts)


def _extract_flat_root(logs_zip, job_name):
    """Match flat root files like '1_BuildAndTest.txt' or '0_BuildContrib.txt'."""
    suffix = f"_{job_name}.txt"
    texts = []
    for entry in logs_zip.namelist():
        if "/" not in entry and entry.endswith(suffix):
            with logs_zip.open(entry) as f:
                texts.append(f.read().decode("utf-8", errors="replace"))
    return texts


def _extract_prefix(logs_zip, prefix):
    """Match folder-based step logs like 'BuildAndTest/1_Run tests.txt'."""
    texts = []
    for entry in logs_zip.namelist():
        if entry.startswith(prefix) and entry.endswith(".txt"):
            with logs_zip.open(entry) as f:
                texts.append(f.read().decode("utf-8", errors="replace"))
    return texts


def _extract_substring(logs_zip, job_name):
    """Last-resort: any .txt entry whose path contains the job name."""
    name_lower = job_name.lower()
    texts = []
    for entry in logs_zip.namelist():
        if entry.endswith(".txt") and name_lower in entry.lower():
            with logs_zip.open(entry) as f:
                texts.append(f.read().decode("utf-8", errors="replace"))
    return texts

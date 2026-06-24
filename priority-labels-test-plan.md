# Priority-Label Dispatcher — Test Plan

Manual test checklist for `.github/workflows/OCV-Priority-Dispatcher.yaml`.

## 1. Workflows enabled for dispatch (initial test set)

Only **3** workflows currently have `workflow_dispatch:` added to their `on:`
block — one per platform group, all from the **5.x** generation, chosen as the
shortest/simplest in each group:

| platform | workflow file | label that dispatches it |
|----------|---------------|--------------------------|
| Windows | `.github/workflows/OCV-PR-5.x-W10.yaml` | `priority:windows`, `priority:ALL` |
| Linux | `.github/workflows/OCV-PR-5.x-U20-OpenVINO.yaml` | `priority:linux`, `priority:ALL` |
| ARM | `.github/workflows/OCV-PR-5.x-ARM64.yaml` | `priority:ARM`, `priority:ALL` |

Every other workflow named in the dispatcher will be *attempted* but logs a
warning (`Could not dispatch ...`) until it too is dispatch-enabled.

## 2. Prerequisites — read this first (it's why the test works)

GitHub imposes three rules that shape the test:

1. **`workflow_dispatch` must be on the repo's DEFAULT branch.** A workflow is
   only dispatchable through the API / `gh workflow run` once the version of its
   file *on the default branch* contains `workflow_dispatch:`. Adding it only on
   a feature branch is **not** enough.
2. **`pull_request` workflows run from the BASE branch.** The dispatcher will
   only run for a PR if `OCV-Priority-Dispatcher.yaml` exists on the base
   (target) branch of that PR.
3. **`GITHUB_TOKEN` is read-only for PRs from a *forked* repo.** `gh workflow
   run` needs `actions: write`. Test with a **same-repo** PR (a branch in your
   fork → `main` of your fork), where the token can be granted write access.

➡️ **Therefore: land these changes on your fork's `main` first**, then open the
test PR from a second branch.

### One-time setup on your fork

```bash
# 'origin' should be your fork (github.com/<you>/ci-gha-workflow)
git push origin feature/priority-labels

# Merge the dispatcher + the 3 enabled workflows into your fork's main so they
# are on the DEFAULT branch (rules 1 & 2 above). E.g. via a PR you self-merge,
# or directly for a personal fork:
git checkout main
git merge feature/priority-labels
git push origin main
```

Confirm in the fork's **Settings → Actions → General**: "Workflow permissions"
= **Read and write permissions** (so `GITHUB_TOKEN` can dispatch).

## 3. Step-by-step test

1. **Create a test PR.** Branch off the fork's `main`, make a trivial change
   (e.g. touch a README line), push, and open a PR **against `main` of your
   fork**. Leave it open — no labels yet. Expect: dispatcher does **not** run
   (it only triggers on `labeled`).

2. **Add `priority:windows`.** On the PR, add the label `priority:windows`.
   - Expect: an **OCV Priority Dispatcher** run appears in the Actions tab.
   - In its log, the *Windows* step runs and dispatches the Windows group.
   - ✅ **Pass:** `OCV-PR-5.x-W10.yaml` (`OCV PR:5.x W10`) starts a new run.
   - The other Windows files log `::warning:: Could not dispatch ...` (expected
     — not enabled yet). The Linux/ARM/Mac steps are **skipped**.

3. **Add `priority:ALL`.** Add the label `priority:ALL` to the same PR.
   - Expect: a new dispatcher run; the Windows, Linux, ARM **and** Mac/iOS steps
     all run (each `if` includes `|| priority:ALL`), plus the "ALL (remaining)"
     step.
   - ✅ **Pass:** all **3** enabled workflows start runs:
     `OCV-PR-5.x-W10.yaml`, `OCV-PR-5.x-U20-OpenVINO.yaml`, `OCV-PR-5.x-ARM64.yaml`.

4. **Remove the labels.** Remove `priority:windows` and `priority:ALL`.
   - ✅ **Pass:** **no new dispatcher run** appears. The dispatcher only triggers
     on `types: [labeled]`, so label *removal* is a no-op by design — nothing
     extra is dispatched.

## 4. What to check in the Actions tab

- **"OCV Priority Dispatcher"** appears in the workflow list (left sidebar) and
  has a run for each label you added.
- Open a run → the relevant platform step(s) are green; non-selected platform
  steps show as **skipped** (grey).
- Expand a dispatch step's log: each enabled workflow prints `-> dispatching
  <file>` with no error; not-yet-enabled ones print a yellow `::warning::`.
- The run's **Summary** page shows the "Priority dispatch summary" table with
  `detected = true/false` per label.
- The dispatched target workflows (`OCV PR:5.x W10` / `U20 OpenVINO` / `ARM64`)
  appear as their own new runs, triggered by `workflow_dispatch`.

## 5. Known limitations

- **Only 3 workflows are dispatch-enabled.** Every other file the dispatcher
  references will log a warning until `workflow_dispatch:` is added to it (one
  line per file, on the default branch). Expand group-by-group from
  `priority-label-mapping.md` (60 of 72 workflows still need the line).
- **Same-repo only.** PRs from external forks get a read-only `GITHUB_TOKEN`;
  the dispatch step will 403. The upstream rollout needs a different mechanism
  (e.g. a PAT/app token, or a `pull_request_target` design) to support external
  contributor PRs — out of scope for this test.
- **Triggers on `labeled` only.** Adding a label after new commits won't
  re-dispatch on push; add `synchronize` (and `reopened`) to `on.pull_request.
  types` later if re-dispatch on new commits is wanted.
- **No duplicate dispatch under `priority:ALL`.** The "ALL (remaining)" step
  deliberately lists only Android/RISC-V/other workflows, since the four
  platform steps already fire on `|| priority:ALL`. Net effect: every workflow
  is dispatched exactly once.
- **Dispatched runner availability.** Some targets (CUDA, ARM, macOS, RISC-V)
  use self-hosted runners; a dispatched run may queue until a runner is free.
  For this test we only verify the run is *dispatched*, not that it completes.

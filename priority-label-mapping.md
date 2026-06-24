# Priority-Label → Workflow Mapping (OpenCV CI)

_Generated 2026-06-23 from `.github/workflows/` (72 workflow files)._

This report groups every CI workflow by platform so we can wire up `priority:*` PR labels (pure GitHub Actions YAML, following the existing `contains(github.event.pull_request.labels.*.name, '...')` pattern). It is descriptive only — no workflows were modified.

**Method.** Grouping is a *case-insensitive substring* match against the **filename** using these keyword lists:

- **Windows**: `W10`, `Win`
- **Linux**: `U20`, `U22`, `U24`
- **ARM**: `ARM`
- **Mac/iOS**: `macOS`, `iOS`, `Mac`, `Darwin`
- **CUDA**: `Cuda`
- **Android**: `Android`
- **RISC-V**: `RISCV`
- **Other**: matches none of the above

A workflow may belong to several groups (e.g. `OCV-PR-5.x-U20-Cuda.yaml` is both **Linux** and **CUDA**). The `dispatch` column shows whether the file already has `workflow_dispatch:` in its `on:` block (✓ present / ✗ must be added to support label-driven dispatch).

## 1. Workflows by platform group

### Windows (14 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-3.4-W10.yaml` | OCV Contrib PR:3.4 W10 |
| ✗ | `OCV-Contrib-PR-4.x-W10.yaml` | OCV Contrib PR:4.x W10 |
| ✗ | `OCV-Contrib-PR-5.x-W10.yaml` | OCV Contrib PR:5.x W10 |
| ✓ | `OCV-Contrib-WinPack-4.x-W10.yaml` | OCV Contrib WinPack:4.x W10 |
| ✗ | `OCV-PR-3.4-W10.yaml` | OCV PR:3.4 W10 |
| ✗ | `OCV-PR-4.x-W10-Vulkan.yaml` | OCV PR:4.x W10 Vulkan |
| ✗ | `OCV-PR-4.x-W10.yaml` | OCV PR:4.x W10 |
| ✗ | `OCV-PR-5.x-W10-ARM64.yaml` | OCV PR:5.x W10-ARM64 |
| ✗ | `OCV-PR-5.x-W10-UWP.yaml` | OCV PR:5.x W10 UWP |
| ✗ | `OCV-PR-5.x-W10-Vulkan.yaml` | OCV PR:5.x W10 Vulkan |
| ✗ | `OCV-PR-5.x-W10.yaml` | OCV PR:5.x W10 |
| ✗ | `OCV-PR-Windows.yaml` | OCV PR Windows |
| ✓ | `OCV-WinPack-4.x-W10.yaml` | OCV WinPack:4.x W10 |
| ✓ | `OCV-WinPack-5.x-W10.yaml` | OCV WinPack:5.x W10 |

### Linux (9 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-3.4-U20.yaml` | OCV Contrib PR:3.4 U20 |
| ✗ | `OCV-Contrib-PR-4.x-U20-Cuda.yaml` | OCV Contrib PR:4.x U20 CUDA |
| ✗ | `OCV-Contrib-PR-5.x-U20-Cuda.yaml` | OCV Contrib PR:5.x U20 CUDA |
| ✓ | `OCV-Coverage-4.x-U20.yaml` | OCV Coverage:4.x U20 |
| ✗ | `OCV-PR-3.4-U20.yaml` | OCV PR:3.4 U20 |
| ✗ | `OCV-PR-4.x-U20-Cuda.yaml` | OCV PR:4.x U20 CUDA |
| ✗ | `OCV-PR-4.x-U20-OpenVINO.yaml` | OCV PR:4.x U20 OpenVINO |
| ✗ | `OCV-PR-5.x-U20-Cuda.yaml` | OCV PR:5.x U20 CUDA |
| ✗ | `OCV-PR-5.x-U20-OpenVINO.yaml` | OCV PR:5.x U20 OpenVINO |

### ARM (19 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-3.4-ARM64.yaml` | OCV Contrib PR:3.4 ARM64 |
| ✗ | `OCV-Contrib-PR-3.4-macOS-ARM64.yaml` | OCV Contrib PR:3.4 macOS ARM64 |
| ✗ | `OCV-Contrib-PR-4.x-ARM64-FastCV.yaml` | OCV Contrib PR:4.x ARM64 FastCV |
| ✗ | `OCV-Contrib-PR-4.x-ARM64.yaml` | OCV Contrib PR:4.x ARM64 |
| ✗ | `OCV-Contrib-PR-4.x-macOS-ARM64.yaml` | OCV Contrib PR:4.x macOS ARM64 |
| ✗ | `OCV-Contrib-PR-5.x-ARM64-FastCV.yaml` | OCV Contrib PR:5.x ARM64 FastCV |
| ✗ | `OCV-Contrib-PR-5.x-ARM64.yaml` | OCV Contrib PR:5.x ARM64 |
| ✗ | `OCV-Contrib-PR-5.x-macOS-ARM64.yaml` | OCV Contrib PR:5.x macOS ARM64 |
| ✗ | `OCV-PR-3.4-ARM64.yaml` | OCV PR:3.4 ARM64 |
| ✗ | `OCV-PR-3.4-macOS-ARM64.yaml` | OCV PR:3.4 macOS ARM64 |
| ✗ | `OCV-PR-4.x-ARM64-Debug.yaml` | OCV PR:4.x ARM64 debug |
| ✗ | `OCV-PR-4.x-ARM64.yaml` | OCV PR:4.x ARM64 |
| ✗ | `OCV-PR-4.x-macOS-ARM64-Vulkan.yaml` | OCV PR:4.x macOS ARM64 Vulkan |
| ✗ | `OCV-PR-4.x-macOS-ARM64.yaml` | OCV PR:4.x macOS ARM64 |
| ✗ | `OCV-PR-5.x-ARM64-Debug.yaml` | OCV PR:5.x ARM64 debug |
| ✗ | `OCV-PR-5.x-ARM64.yaml` | OCV PR:5.x ARM64 |
| ✗ | `OCV-PR-5.x-W10-ARM64.yaml` | OCV PR:5.x W10-ARM64 |
| ✗ | `OCV-PR-5.x-macOS-ARM64-Vulkan.yaml` | OCV PR:5.x macOS ARM64 Vulkan |
| ✗ | `OCV-PR-5.x-macOS-ARM64.yaml` | OCV PR:5.x macOS ARM64 |

### Mac/iOS (17 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-3.4-macOS-ARM64.yaml` | OCV Contrib PR:3.4 macOS ARM64 |
| ✗ | `OCV-Contrib-PR-3.4-macOS-x86_64.yaml` | OCV Contrib PR:3.4 macOS x86_64 |
| ✗ | `OCV-Contrib-PR-4.x-macOS-ARM64.yaml` | OCV Contrib PR:4.x macOS ARM64 |
| ✗ | `OCV-Contrib-PR-4.x-macOS-x86_64.yaml` | OCV Contrib PR:4.x macOS x86_64 |
| ✗ | `OCV-Contrib-PR-5.x-macOS-ARM64.yaml` | OCV Contrib PR:5.x macOS ARM64 |
| ✗ | `OCV-Contrib-PR-5.x-macOS-x86_64.yaml` | OCV Contrib PR:5.x macOS x86_64 |
| ✓ | `OCV-PR-3.4-iOS.yaml` | OCV PR:3.4 iOS |
| ✗ | `OCV-PR-3.4-macOS-ARM64.yaml` | OCV PR:3.4 macOS ARM64 |
| ✗ | `OCV-PR-3.4-macOS-x86_64.yaml` | OCV PR:3.4 macOS x86_64 |
| ✓ | `OCV-PR-4.x-iOS.yaml` | OCV PR:4.x iOS |
| ✗ | `OCV-PR-4.x-macOS-ARM64-Vulkan.yaml` | OCV PR:4.x macOS ARM64 Vulkan |
| ✗ | `OCV-PR-4.x-macOS-ARM64.yaml` | OCV PR:4.x macOS ARM64 |
| ✗ | `OCV-PR-4.x-macOS-x86_64.yaml` | OCV PR:4.x macOS x86_64 |
| ✓ | `OCV-PR-5.x-iOS.yaml` | OCV PR:5.x iOS |
| ✗ | `OCV-PR-5.x-macOS-ARM64-Vulkan.yaml` | OCV PR:5.x macOS ARM64 Vulkan |
| ✗ | `OCV-PR-5.x-macOS-ARM64.yaml` | OCV PR:5.x macOS ARM64 |
| ✗ | `OCV-PR-5.x-macOS-x86_64.yaml` | OCV PR:5.x macOS x86_64 |

### CUDA (4 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-4.x-U20-Cuda.yaml` | OCV Contrib PR:4.x U20 CUDA |
| ✗ | `OCV-Contrib-PR-5.x-U20-Cuda.yaml` | OCV Contrib PR:5.x U20 CUDA |
| ✗ | `OCV-PR-4.x-U20-Cuda.yaml` | OCV PR:4.x U20 CUDA |
| ✗ | `OCV-PR-5.x-U20-Cuda.yaml` | OCV PR:5.x U20 CUDA |

### Android (4 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✓ | `OCV-4.x-Android-SDK.yaml` | OCV PR:4.x AndroidSDK |
| ✓ | `OCV-PR-3.4-Android.yaml` | OCV PR:3.4 AndroidSDK |
| ✗ | `OCV-PR-4.x-Android-Test.yaml` | OCV PR:4.x Android aarch64 build |
| ✓ | `OCV-PR-5.x-Android.yaml` | OCV PR:5.x AndroidSDK |

### RISC-V (5 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-Contrib-PR-4.x-RISCV.yaml` | OCV Contrib PR:4.x RISC-V |
| ✗ | `OCV-Contrib-PR-5.x-RISCV.yaml` | OCV Contrib PR:5.x RISC-V |
| ✓ | `OCV-Nightly-RISCV.yaml` | OCV Nightly RISC-V |
| ✗ | `OCV-PR-4.x-RISCV.yaml` | OCV PR:4.x RISC-V |
| ✗ | `OCV-PR-5.x-RISCV.yaml` | OCV PR:5.x RISC-V |

### Other (13 workflows)

| dispatch | filename | `name:` |
|:--------:|----------|---------|
| ✗ | `OCV-CodeQL.yaml` | OCV CodeQL |
| ✗ | `OCV-Contrib-PR-4.x-O22-CANN.yaml` | OCV Contrib PR:4.x O22 CANN |
| ✗ | `OCV-DNN-models-update.yaml` | OCV DNN Models Update |
| ✗ | `OCV-Git-Cache.yaml` | OCV Git cache |
| ✗ | `OCV-PR-3.4-docs.yaml` | OCV PR:3.4 docs |
| ✗ | `OCV-PR-4.x-docs.yaml` | OCV PR:4.x docs |
| ✗ | `OCV-PR-4.x-loongnix-loongarch64.yaml` | OCV PR:4.x Loongnix LoongArch64 |
| ✗ | `OCV-PR-5.x-docs.yaml` | OCV PR:5.x docs |
| ✗ | `OCV-PR-Linux-Alpine.yaml` | OCV PR Alpine Musl-C |
| ✗ | `OCV-PR-Linux-NoHAL.yaml` | OCV PR Linux NoHAL |
| ✗ | `OCV-PR-Linux.yaml` | OCV PR Linux |
| ✗ | `OCV-timvx-backend-tests-4.x.yml` | OCV TIM-VX Backend |
| ✓ | `build_docs_schedule.yaml` | build docs schedule |

## 2. Summary

| metric | count |
|--------|------:|
| Total workflows | 72 |
| Already have `workflow_dispatch` | 12 |
| Need `workflow_dispatch` added | 60 |

Per-group counts (groups overlap, so these do not sum to the total):

| group | workflows | with dispatch | need dispatch |
|-------|----------:|--------------:|--------------:|
| Windows | 14 | 3 | 11 |
| Linux | 9 | 1 | 8 |
| ARM | 19 | 0 | 19 |
| Mac/iOS | 17 | 3 | 14 |
| CUDA | 4 | 0 | 4 |
| Android | 4 | 3 | 1 |
| RISC-V | 5 | 1 | 4 |
| Other | 13 | 1 | 12 |

## 3. Priority-label dispatch sets

What each supported label would dispatch (exact filenames). ✓/✗ again marks existing `workflow_dispatch`.

### `priority:windows` — 14 workflows (the **Windows** group)

_3 already dispatch-enabled, 11 would need it added._

- ✗ `OCV-Contrib-PR-3.4-W10.yaml`
- ✗ `OCV-Contrib-PR-4.x-W10.yaml`
- ✗ `OCV-Contrib-PR-5.x-W10.yaml`
- ✓ `OCV-Contrib-WinPack-4.x-W10.yaml`
- ✗ `OCV-PR-3.4-W10.yaml`
- ✗ `OCV-PR-4.x-W10-Vulkan.yaml`
- ✗ `OCV-PR-4.x-W10.yaml`
- ✗ `OCV-PR-5.x-W10-ARM64.yaml`
- ✗ `OCV-PR-5.x-W10-UWP.yaml`
- ✗ `OCV-PR-5.x-W10-Vulkan.yaml`
- ✗ `OCV-PR-5.x-W10.yaml`
- ✗ `OCV-PR-Windows.yaml`
- ✓ `OCV-WinPack-4.x-W10.yaml`
- ✓ `OCV-WinPack-5.x-W10.yaml`

### `priority:linux` — 9 workflows (the **Linux** group)

_1 already dispatch-enabled, 8 would need it added._

- ✗ `OCV-Contrib-PR-3.4-U20.yaml`
- ✗ `OCV-Contrib-PR-4.x-U20-Cuda.yaml`
- ✗ `OCV-Contrib-PR-5.x-U20-Cuda.yaml`
- ✓ `OCV-Coverage-4.x-U20.yaml`
- ✗ `OCV-PR-3.4-U20.yaml`
- ✗ `OCV-PR-4.x-U20-Cuda.yaml`
- ✗ `OCV-PR-4.x-U20-OpenVINO.yaml`
- ✗ `OCV-PR-5.x-U20-Cuda.yaml`
- ✗ `OCV-PR-5.x-U20-OpenVINO.yaml`

### `priority:ARM` — 19 workflows (the **ARM** group)

_0 already dispatch-enabled, 19 would need it added._

- ✗ `OCV-Contrib-PR-3.4-ARM64.yaml`
- ✗ `OCV-Contrib-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-4.x-ARM64-FastCV.yaml`
- ✗ `OCV-Contrib-PR-4.x-ARM64.yaml`
- ✗ `OCV-Contrib-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-5.x-ARM64-FastCV.yaml`
- ✗ `OCV-Contrib-PR-5.x-ARM64.yaml`
- ✗ `OCV-Contrib-PR-5.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-3.4-ARM64.yaml`
- ✗ `OCV-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-PR-4.x-ARM64-Debug.yaml`
- ✗ `OCV-PR-4.x-ARM64.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-5.x-ARM64-Debug.yaml`
- ✗ `OCV-PR-5.x-ARM64.yaml`
- ✗ `OCV-PR-5.x-W10-ARM64.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64.yaml`

### `priority:mac` — 17 workflows (the **Mac/iOS** group)

_3 already dispatch-enabled, 14 would need it added._

- ✗ `OCV-Contrib-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-3.4-macOS-x86_64.yaml`
- ✗ `OCV-Contrib-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-4.x-macOS-x86_64.yaml`
- ✗ `OCV-Contrib-PR-5.x-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-5.x-macOS-x86_64.yaml`
- ✓ `OCV-PR-3.4-iOS.yaml`
- ✗ `OCV-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-PR-3.4-macOS-x86_64.yaml`
- ✓ `OCV-PR-4.x-iOS.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-4.x-macOS-x86_64.yaml`
- ✓ `OCV-PR-5.x-iOS.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-5.x-macOS-x86_64.yaml`

### `priority:ALL` — 72 workflows (every workflow)

_12 already dispatch-enabled, 60 would need it added._

- ✓ `OCV-4.x-Android-SDK.yaml`
- ✗ `OCV-CodeQL.yaml`
- ✗ `OCV-Contrib-PR-3.4-ARM64.yaml`
- ✗ `OCV-Contrib-PR-3.4-U20.yaml`
- ✗ `OCV-Contrib-PR-3.4-W10.yaml`
- ✗ `OCV-Contrib-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-3.4-macOS-x86_64.yaml`
- ✗ `OCV-Contrib-PR-4.x-ARM64-FastCV.yaml`
- ✗ `OCV-Contrib-PR-4.x-ARM64.yaml`
- ✗ `OCV-Contrib-PR-4.x-O22-CANN.yaml`
- ✗ `OCV-Contrib-PR-4.x-RISCV.yaml`
- ✗ `OCV-Contrib-PR-4.x-U20-Cuda.yaml`
- ✗ `OCV-Contrib-PR-4.x-W10.yaml`
- ✗ `OCV-Contrib-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-4.x-macOS-x86_64.yaml`
- ✗ `OCV-Contrib-PR-5.x-ARM64-FastCV.yaml`
- ✗ `OCV-Contrib-PR-5.x-ARM64.yaml`
- ✗ `OCV-Contrib-PR-5.x-RISCV.yaml`
- ✗ `OCV-Contrib-PR-5.x-U20-Cuda.yaml`
- ✗ `OCV-Contrib-PR-5.x-W10.yaml`
- ✗ `OCV-Contrib-PR-5.x-macOS-ARM64.yaml`
- ✗ `OCV-Contrib-PR-5.x-macOS-x86_64.yaml`
- ✓ `OCV-Contrib-WinPack-4.x-W10.yaml`
- ✓ `OCV-Coverage-4.x-U20.yaml`
- ✗ `OCV-DNN-models-update.yaml`
- ✗ `OCV-Git-Cache.yaml`
- ✓ `OCV-Nightly-RISCV.yaml`
- ✗ `OCV-PR-3.4-ARM64.yaml`
- ✓ `OCV-PR-3.4-Android.yaml`
- ✗ `OCV-PR-3.4-U20.yaml`
- ✗ `OCV-PR-3.4-W10.yaml`
- ✗ `OCV-PR-3.4-docs.yaml`
- ✓ `OCV-PR-3.4-iOS.yaml`
- ✗ `OCV-PR-3.4-macOS-ARM64.yaml`
- ✗ `OCV-PR-3.4-macOS-x86_64.yaml`
- ✗ `OCV-PR-4.x-ARM64-Debug.yaml`
- ✗ `OCV-PR-4.x-ARM64.yaml`
- ✗ `OCV-PR-4.x-Android-Test.yaml`
- ✗ `OCV-PR-4.x-RISCV.yaml`
- ✗ `OCV-PR-4.x-U20-Cuda.yaml`
- ✗ `OCV-PR-4.x-U20-OpenVINO.yaml`
- ✗ `OCV-PR-4.x-W10-Vulkan.yaml`
- ✗ `OCV-PR-4.x-W10.yaml`
- ✗ `OCV-PR-4.x-docs.yaml`
- ✓ `OCV-PR-4.x-iOS.yaml`
- ✗ `OCV-PR-4.x-loongnix-loongarch64.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-4.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-4.x-macOS-x86_64.yaml`
- ✗ `OCV-PR-5.x-ARM64-Debug.yaml`
- ✗ `OCV-PR-5.x-ARM64.yaml`
- ✓ `OCV-PR-5.x-Android.yaml`
- ✗ `OCV-PR-5.x-RISCV.yaml`
- ✗ `OCV-PR-5.x-U20-Cuda.yaml`
- ✗ `OCV-PR-5.x-U20-OpenVINO.yaml`
- ✗ `OCV-PR-5.x-W10-ARM64.yaml`
- ✗ `OCV-PR-5.x-W10-UWP.yaml`
- ✗ `OCV-PR-5.x-W10-Vulkan.yaml`
- ✗ `OCV-PR-5.x-W10.yaml`
- ✗ `OCV-PR-5.x-docs.yaml`
- ✓ `OCV-PR-5.x-iOS.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64-Vulkan.yaml`
- ✗ `OCV-PR-5.x-macOS-ARM64.yaml`
- ✗ `OCV-PR-5.x-macOS-x86_64.yaml`
- ✗ `OCV-PR-Linux-Alpine.yaml`
- ✗ `OCV-PR-Linux-NoHAL.yaml`
- ✗ `OCV-PR-Linux.yaml`
- ✗ `OCV-PR-Windows.yaml`
- ✓ `OCV-WinPack-4.x-W10.yaml`
- ✓ `OCV-WinPack-5.x-W10.yaml`
- ✗ `OCV-timvx-backend-tests-4.x.yml`
- ✓ `build_docs_schedule.yaml`

## 4. Notes & observations

- **60 of 72** workflows lack `workflow_dispatch` and would need it added before they can be triggered on-demand by the label feature.
- Heads-up: the Linux keyword list (`U20`/`U22`/`U24`) does **not** match 3 file(s) that have `Linux` in the name (`OCV-PR-Linux-Alpine.yaml`, `OCV-PR-Linux-NoHAL.yaml`, `OCV-PR-Linux.yaml`); they land in **Other**. Add `Linux` (and possibly `O22`/`loongnix`/`Alpine`) to the Linux keywords if you want those included in `priority:linux`.
- `ARM` matches `ARM64` filenames and correctly skips `loongarch64` (LoongArch is not ARM).
- The `Mac/iOS` group intentionally folds iOS in with macOS (Apple targets).
- One file uses the `.yml` extension (`OCV-timvx-backend-tests-4.x.yml`); it is included in the scan.

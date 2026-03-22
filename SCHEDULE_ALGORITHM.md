# Schedule Algorithm

This document describes the scheduling algorithm used by Task Tracker, its invariants, and its validation strategy.

## Overview

The algorithm schedules work backwards from each task's deadline. It is a **greedy, single-pass** scheduler: tasks are sorted by deadline and allocated hours day-by-day, filling normal hours first, then overtime.

---

## Key Design Decisions

### 1. Work Backwards from Deadline

For each task, the algorithm starts at the deadline and walks backwards toward today, allocating hours on each available day. This ensures the most urgent (nearest-deadline) work gets priority when multiple tasks compete for the same days.

### 2. Greedy Fill (Normal → Overtime)

On each day, the algorithm:
1. **Normal hours first** — fills up to `normal_work_hours_per_day` (default 8h) before touching overtime.
2. **Overtime only when needed** — if a task still needs hours after normal hours are exhausted, it allocates overtime up to `overtime_max_hours_per_day` (default 2h).

This respects labor norms: normal capacity is the primary assumption, overtime is a last resort.

### 3. Allocated Hours are "Committed" Per-Task, Per-Day

When Task A is scheduled, its allocated hours on each day are recorded. When Task B is later scheduled and shares a day with Task A, the algorithm accounts for the already-allocated hours on that day (both normal and overtime). This prevents double-booking.

### 4. Tasks are Sorted by Deadline

Before scheduling, tasks are sorted ascending by deadline. This means:
- Near-deadline tasks get first claim on shared days.
- Far-deadline tasks are scheduled after, and their allocations are reduced if days are already claimed.

### 5. Impossible Tasks are Tracked Separately

If, after exhausting all available days (today through deadline), a task still has unmet hours, it is marked **impossible** with the deficit (`hours_short`). The algorithm does not partially schedule impossible tasks.

---

## Algorithm Invariants

These properties are always true for any schedule produced by `generate_schedule`, and they are enforced by the invariant test suite (`test_scheduler.py`):

| # | Invariant | Description |
|---|-----------|-------------|
| 1 | **Total hours allocated** | For every possible (non-impossible) task, the sum of all its scheduled blocks' hours equals `task.estimated_hours`. |
| 2 | **No negative hours** | Every scheduled block has `hours > 0`. |
| 3 | **All days in the future** | Every date in `day_schedules` is `>= date.today()`. |
| 4 | **No duplicate blocks** | No two blocks exist for the same task on the same day with the same overtime flag. |
| 5 | **Overtime only when needed** | No overtime block exists on a day unless normal hours for that day were fully exhausted by prior allocations. |
| 6 | **Impossible only when truly short** | A task is marked impossible only when the total available hours (today → deadline) is strictly less than `estimated_hours`. |

---

## What Requires Mac to Validate vs. What Can Be Validated on Linux

### ✅ Can Be Validated on Linux (Ubuntu)

All of the following are fully testable without a Mac:

- **Python scheduling algorithm** — `scheduler.py` and `test_scheduler.py`
  - Run: `python3 -m pytest test_scheduler.py -v`
  - Run invariant summary: `python3 ci_algorithm_tests.py`
- **Swift static analysis** (grep-based scan)
  - Basic syntax and pattern checks
  - No compilation required
  - Runs in `.github/workflows/ci.yml` → `swift-quality` job
- **Swift code structure checks** (line count, basic conventions)
- **GitHub Actions CI pipeline** (Linux jobs: `test-python`, `swift-quality`)

### ❌ Requires macOS

The following require an Apple toolchain and cannot run on Ubuntu:

- **Swift compilation** — requires Xcode/swiftc to compile `Sources/*.swift`
- **Xcode project generation** — requires `xcodegen`
- **iOS Simulator build** — requires `xcodebuild` with iOS SDK
- **SwiftUI preview rendering**
- **Full Swift unit tests** (`.swift` test files in `Tests/TaskTrackerTests/`)
  - These are run via `xcodebuild` on the macOS `build` job

### CI Strategy

| Job | Runs on | What it does |
|-----|---------|-------------|
| `build` | macOS | Full Swift Xcode build |
| `test-python` | Ubuntu | Python scheduling algorithm tests + invariant summary |
| `swift-quality` | Ubuntu | Lightweight Swift file scan (no compilation) |

> **On PRs:** Swift changes should be verified to compile on a Mac before merge. The `swift-quality` job provides a fast Linux-side check only.

---

## Files

| File | Purpose |
|------|---------|
| `scheduler.py` | Core scheduling algorithm (Python port) |
| `test_scheduler.py` | Unit + invariant tests |
| `pytest.ini` | pytest configuration |
| `ci_algorithm_tests.py` | Programmatic invariant runner for CI |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |

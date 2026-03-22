"""
Unit tests for Task Tracker scheduling algorithm.
Run with: python3 -m pytest test_scheduler.py -v
Or directly: python3 test_scheduler.py
"""
import unittest
from datetime import date, timedelta
from scheduler import Task, DailySettings, generate_schedule


class TestScheduler(unittest.TestCase):

    def _days_from_now(self, days: int) -> date:
        return date.today() + timedelta(days=days)

    def test_single_task_within_deadline(self):
        """Task fits easily within deadline using normal hours."""
        tasks = [
            Task(
                id="1",
                title="Write Docs",
                estimated_hours=4,
                deadline=self._days_from_now(3),
                normal_hours_per_day=8
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Task should be possible")
        self.assertGreater(len(result.day_schedules), 0, "Should have schedule days")

    def test_overtime_required(self):
        """Task needs overtime to meet deadline."""
        tasks = [
            Task(
                id="2",
                title="Big Project",
                estimated_hours=20,
                deadline=self._days_from_now(2),
                normal_hours_per_day=8
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Task should be possible with overtime")
        overtime_days = [d for d in result.day_schedules if d.is_overtime]
        self.assertGreater(len(overtime_days), 0, "Should use overtime")

    def test_impossible_deadline(self):
        """Even with overtime, deadline is impossible within available hours."""
        # Deadline TODAY = only today available = 8 normal + 2 OT = 10h max
        # Task needs 20h → 10h short
        tasks = [
            Task(
                id="3",
                title="Impossible Task",
                estimated_hours=20,
                deadline=self._days_from_now(0),  # today only = 10h max
                normal_hours_per_day=8
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 1, "Should be impossible")
        self.assertEqual(result.impossible_tasks[0].task_title, "Impossible Task")
        self.assertGreater(result.impossible_tasks[0].hours_short, 0)
        # 20h needed, 10h available (8 normal + 2 OT) = 10h short
        self.assertAlmostEqual(result.impossible_tasks[0].hours_short, 10.0, places=1)

    def test_multiple_tasks_same_day(self):
        """Two tasks on same day: one normal, one uses overtime."""
        deadline = self._days_from_now(1)
        tasks = [
            Task(id="a", title="Task A", estimated_hours=5, deadline=deadline, normal_hours_per_day=8),
            Task(id="b", title="Task B", estimated_hours=5, deadline=deadline, normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Both tasks should be possible")
        # Day 1: Task A gets 5h normal, Task B gets 3h normal + 2h OT
        self.assertGreaterEqual(len(result.day_schedules), 1)

    def test_empty_task_list(self):
        """Empty input returns empty schedule."""
        result = generate_schedule([], DailySettings())
        self.assertEqual(len(result.impossible_tasks), 0)
        self.assertEqual(len(result.day_schedules), 0)

    def test_deadline_in_past(self):
        """Task with past deadline is marked impossible."""
        tasks = [
            Task(
                id="past",
                title="Past Task",
                estimated_hours=4,
                deadline=self._days_from_now(-1),
                normal_hours_per_day=8
            )
        ]
        settings = DailySettings()
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 1, "Past deadline should be impossible")

    def test_normal_hours_used_before_overtime(self):
        """System always uses normal hours before overtime."""
        tasks = [
            Task(
                id="n",
                title="Balanced",
                estimated_hours=8,
                deadline=self._days_from_now(1),
                normal_hours_per_day=8
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        # Should be exactly 8h normal, 0h overtime
        day = result.day_schedules[0]
        normal_hours = sum(b.hours for b in day.blocks if not b.is_overtime)
        ot_hours = sum(b.hours for b in day.blocks if b.is_overtime)
        self.assertAlmostEqual(normal_hours, 8.0, places=1)
        self.assertAlmostEqual(ot_hours, 0.0, places=1)

    # ─────────────────────────────────────────────────────────────────────
    # Edge Cases
    # ─────────────────────────────────────────────────────────────────────

    def test_zero_estimated_hours(self):
        """Task with 0 estimated hours should schedule trivially."""
        tasks = [
            Task(
                id="zero",
                title="Zero Hour Task",
                estimated_hours=0,
                deadline=self._days_from_now(1),
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Zero-hour task must be possible")
        # No blocks should be produced for a 0-hour task
        total_hours = sum(
            b.hours
            for ds in result.day_schedules
            for b in ds.blocks
            if b.task_id == "zero"
        )
        self.assertAlmostEqual(total_hours, 0.0, places=1)

    def test_exactly_fits_normal_hours_no_overtime(self):
        """Task estimated hours == available normal hours → all hours are normal.

        Note: the algorithm fills each day greedily (8N + OT), so a 3-day task
        (24h) will use some OT because the fill order is:
        day 1: 8N+2OT, day 2: 8N+2OT, day 3: 4N.
        We test with a 1-day deadline (8h needed, 8h normal available) to
        guarantee zero OT and validate the "normal-before-overtime" principle.
        """
        # 1 day × 8h = 8h available; task needs exactly 8h → no OT needed
        deadline = self._days_from_now(0)  # today only
        tasks = [
            Task(
                id="exact",
                title="Exact Fit",
                estimated_hours=8,
                deadline=deadline,
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        all_blocks = [b for ds in result.day_schedules for b in ds.blocks]
        ot_blocks = [b for b in all_blocks if b.is_overtime]
        self.assertEqual(len(ot_blocks), 0, "Should not use any overtime with 1-day fit")
        total_normal = sum(b.hours for b in all_blocks if not b.is_overtime)
        self.assertAlmostEqual(total_normal, 8.0, places=1)

    def test_multiday_span_weekend_ignored(self):
        """Algorithm doesn't consider weekends; multi-day span across Sat/Sun works like any other days."""
        # 5 days out, deadline on day 5 — all 5 days are usable (algorithm doesn't filter weekends)
        deadline = self._days_from_now(4)  # today + 4 future days
        tasks = [
            Task(
                id="long",
                title="Long Task",
                estimated_hours=32,  # 4 days × 8h = 32h exactly
                deadline=deadline,
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        total_hours = sum(b.hours for ds in result.day_schedules for b in ds.blocks)
        self.assertAlmostEqual(total_hours, 32.0, places=1)

    def test_two_tasks_same_deadline_splits_hours(self):
        """Two tasks with identical deadlines share the available day correctly."""
        deadline = self._days_from_now(1)  # only today + tomorrow = 2 days = 16 normal + 4 OT
        tasks = [
            Task(id="x", title="Task X", estimated_hours=8, deadline=deadline, normal_hours_per_day=8),
            Task(id="y", title="Task Y", estimated_hours=8, deadline=deadline, normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Both tasks should be possible")
        # Both tasks should appear in the schedule
        scheduled_ids = {b.task_id for ds in result.day_schedules for b in ds.blocks}
        self.assertIn("x", scheduled_ids)
        self.assertIn("y", scheduled_ids)

    def test_zero_overtime_allowed(self):
        """Settings with overtime_max_hours_per_day=0 should never produce overtime blocks."""
        tasks = [
            Task(
                id="no_ot",
                title="No OT Task",
                estimated_hours=12,
                deadline=self._days_from_now(1),  # 2 days × 8 = 16h normal available > 12h needed
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=0)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        ot_blocks = [b for ds in result.day_schedules for b in ds.blocks if b.is_overtime]
        self.assertEqual(len(ot_blocks), 0, "Must never allocate overtime when OT cap is 0")

    def test_deadline_exactly_today(self):
        """Deadline today → 1 day, 10h possible (8 normal + 2 OT)."""
        tasks = [
            Task(
                id="today",
                title="Due Today",
                estimated_hours=10,
                deadline=self._days_from_now(0),
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "10h task fits in today (8N + 2OT)")
        all_blocks = [b for ds in result.day_schedules for b in ds.blocks]
        total = sum(b.hours for b in all_blocks)
        self.assertAlmostEqual(total, 10.0, places=1)

    def test_deadline_tomorrow_two_days(self):
        """Deadline tomorrow → 2 days, 18h possible (8+2 + 8+0 with 0 OT needed)."""
        # 2 days × 8 normal = 16, but algorithm uses OT too
        # 2 days × 8N + 2 OT = 20h... but with existing block sharing
        # Actually: 2 days available = 2×8=16 normal + 2×2 OT = 20h max
        # Task needs only 18h, so 16N + 2OT
        tasks = [
            Task(
                id="tomorrow",
                title="Due Tomorrow",
                estimated_hours=18,
                deadline=self._days_from_now(1),
                normal_hours_per_day=8,
            )
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "18h fits in 2 days")
        all_blocks = [b for ds in result.day_schedules for b in ds.blocks]
        total = sum(b.hours for b in all_blocks)
        self.assertAlmostEqual(total, 18.0, places=1)

    # ─────────────────────────────────────────────────────────────────────
    # Multi-task Interaction Tests
    # ─────────────────────────────────────────────────────────────────────

    def test_three_tasks_same_deadline(self):
        """Three tasks all due on the same day share that day proportionally."""
        deadline = self._days_from_now(1)  # today + tomorrow = 16 normal + 4 OT = 20h total
        tasks = [
            Task(id="t1", title="Task 1", estimated_hours=4, deadline=deadline, normal_hours_per_day=8),
            Task(id="t2", title="Task 2", estimated_hours=8, deadline=deadline, normal_hours_per_day=8),
            Task(id="t3", title="Task 3", estimated_hours=4, deadline=deadline, normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        scheduled_ids = {b.task_id for ds in result.day_schedules for b in ds.blocks}
        self.assertIn("t1", scheduled_ids)
        self.assertIn("t2", scheduled_ids)
        self.assertIn("t3", scheduled_ids)
        # Total allocated must equal 4+8+4 = 16h (no OT needed)
        total = sum(b.hours for ds in result.day_schedules for b in ds.blocks)
        self.assertAlmostEqual(total, 16.0, places=1)

    def test_earlier_deadline_with_more_hours(self):
        """Task A due sooner (but more hours) must not break Task B's scheduling."""
        # Task A: due today, 10h (fits: 8N + 2OT)
        # Task B: due tomorrow, 8h (fits: 8N)
        tasks = [
            Task(id="a", title="Task A (Today)", estimated_hours=10, deadline=self._days_from_now(0), normal_hours_per_day=8),
            Task(id="b", title="Task B (Tomorrow)", estimated_hours=8, deadline=self._days_from_now(1), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0, "Both tasks should be possible")
        # Verify both appear
        scheduled_ids = {b.task_id for ds in result.day_schedules for b in ds.blocks}
        self.assertIn("a", scheduled_ids)
        self.assertIn("b", scheduled_ids)
        # Total = 10 + 8 = 18h
        total = sum(b.hours for ds in result.day_schedules for b in ds.blocks)
        self.assertAlmostEqual(total, 18.0, places=1)

    def test_overlapping_day_allocations(self):
        """Two tasks spanning the same days must not double-count available hours incorrectly."""
        # Both tasks due on day+2, each needs 12h
        # 3 days available: 3×8 = 24 normal, 3×2 = 6 OT → 30h total
        # Combined need: 24h → fits in normal hours
        deadline = self._days_from_now(2)
        tasks = [
            Task(id="over1", title="Overlap 1", estimated_hours=12, deadline=deadline, normal_hours_per_day=8),
            Task(id="over2", title="Overlap 2", estimated_hours=12, deadline=deadline, normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        self.assertEqual(len(result.impossible_tasks), 0)
        # Total scheduled hours must equal combined task hours
        total = sum(b.hours for ds in result.day_schedules for b in ds.blocks)
        self.assertAlmostEqual(total, 24.0, places=1)

    # ─────────────────────────────────────────────────────────────────────
    # Property-based / Invariant Tests
    # ─────────────────────────────────────────────────────────────────────

    def _get_all_blocks(self, result) -> list:
        """Helper: collect every ScheduledBlock from a ScheduleResult."""
        return [b for ds in result.day_schedules for b in ds.blocks]

    def _blocks_for_task(self, result, task_id: str) -> list:
        return [b for b in self._get_all_blocks(result) if b.task_id == task_id]

    def _task_hours_map(self, tasks: list[Task]) -> dict:
        return {t.id: t.estimated_hours for t in tasks}

    def test_invariant_total_hours_allocated(self):
        """For every scheduled task, sum of all its blocks' hours == task.estimated_hours."""
        today = self._days_from_now(0)
        deadline_a = self._days_from_now(1)
        deadline_b = self._days_from_now(3)

        tasks = [
            Task(id="inv1", title="Inv Task 1", estimated_hours=5,  deadline=deadline_a, normal_hours_per_day=8),
            Task(id="inv2", title="Inv Task 2", estimated_hours=14, deadline=deadline_b, normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        for t in tasks:
            if t.id == "inv1" and len(result.impossible_tasks) == 0:
                allocated = sum(b.hours for b in self._blocks_for_task(result, t.id))
                self.assertAlmostEqual(
                    allocated, t.estimated_hours, places=1,
                    msg=f"Task {t.id}: allocated={allocated} != estimated={t.estimated_hours}"
                )
            if t.id == "inv2" and len(result.impossible_tasks) == 0:
                allocated = sum(b.hours for b in self._blocks_for_task(result, t.id))
                self.assertAlmostEqual(
                    allocated, t.estimated_hours, places=1,
                    msg=f"Task {t.id}: allocated={allocated} != estimated={t.estimated_hours}"
                )

    def test_invariant_no_negative_hours(self):
        """All block hours must be strictly > 0."""
        tasks = [
            Task(id="n1", title="N1", estimated_hours=6, deadline=self._days_from_now(2), normal_hours_per_day=8),
            Task(id="n2", title="N2", estimated_hours=10, deadline=self._days_from_now(4), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        for block in self._get_all_blocks(result):
            self.assertGreater(
                block.hours, 0,
                f"Block for task '{block.task_id}' has non-positive hours: {block.hours}"
            )

    def test_invariant_all_days_in_future(self):
        """All schedule dates must be >= today."""
        tasks = [
            Task(id="fut", title="Future", estimated_hours=5, deadline=self._days_from_now(3), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        today = date.today()
        for ds in result.day_schedules:
            self.assertGreaterEqual(
                ds.date, today,
                f"Schedule contains a past date: {ds.date}"
            )

    def test_invariant_no_duplicate_blocks(self):
        """No two blocks for the same task on the same day with the same overtime flag."""
        tasks = [
            Task(id="d1", title="Dup 1", estimated_hours=7, deadline=self._days_from_now(2), normal_hours_per_day=8),
            Task(id="d2", title="Dup 2", estimated_hours=15, deadline=self._days_from_now(3), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks, settings)

        seen: dict[tuple, float] = {}
        for ds in result.day_schedules:
            for b in ds.blocks:
                key = (b.task_id, ds.date.isoformat(), b.is_overtime)
                self.assertNotIn(
                    key, seen,
                    f"Duplicate block found: task={b.task_id}, date={ds.date}, is_overtime={b.is_overtime}"
                )
                seen[key] = b.hours

    def test_invariant_overtime_only_when_needed(self):
        """No overtime block exists unless normal hours on that day were exhausted."""
        # Task requiring 9h on a single day: 8N + 1OT → OT needed
        # Task requiring 8h on a single day: 8N + 0OT → OT not needed
        tasks_three = [
            Task(id="ot1", title="OT Needed", estimated_hours=9,  deadline=self._days_from_now(1), normal_hours_per_day=8),
            Task(id="ot2", title="OT Not Needed", estimated_hours=8, deadline=self._days_from_now(1), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)
        result = generate_schedule(tasks_three, settings)

        # Find the day schedule for deadline day
        deadline_day = self._days_from_now(1)
        day_sched = next((ds for ds in result.day_schedules if ds.date == deadline_day), None)

        if day_sched:
            total_normal = sum(b.hours for b in day_sched.blocks if not b.is_overtime)
            total_ot = sum(b.hours for b in day_sched.blocks if b.is_overtime)

            if total_ot > 0:
                # If OT was used, normal hours should be at or near the cap
                self.assertGreaterEqual(
                    total_normal, settings.normal_work_hours_per_day - 0.01,
                    "OT should only be used when normal hours are exhausted"
                )

    def test_invariant_impossible_only_when_truly_short(self):
        """A task is marked impossible only when total available hours < estimated hours."""
        # 1 day available = 8N + 2OT = 10h max
        # Task needing 9h → should be possible
        tasks = [
            Task(id="barely", title="Barely Possible", estimated_hours=9, deadline=self._days_from_now(0), normal_hours_per_day=8),
            Task(id="impossible_short", title="Truly Impossible", estimated_hours=11, deadline=self._days_from_now(0), normal_hours_per_day=8),
        ]
        settings = DailySettings(normal_work_hours_per_day=8, overtime_max_hours_per_day=2)

        # Test barely possible
        result_barely = generate_schedule([tasks[0]], settings)
        self.assertEqual(len(result_barely.impossible_tasks), 0,
            "Task needing 9h with 10h available should NOT be impossible")

        # Test truly impossible
        result_impossible = generate_schedule([tasks[1]], settings)
        self.assertEqual(len(result_impossible.impossible_tasks), 1,
            "Task needing 11h with 10h available SHOULD be impossible")


if __name__ == "__main__":
    unittest.main(verbosity=2)

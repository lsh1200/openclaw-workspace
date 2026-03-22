#!/usr/bin/env python3
"""
ci_algorithm_tests.py
Runs the scheduling algorithm test suite programmatically and reports
invariant test results. Designed for GitHub Actions (ubuntu-latest).

Exit codes:
  0 — all invariant tests passed
  1 — one or more invariant tests failed
"""
import sys
import unittest

from test_scheduler import TestScheduler


class _InvariantTestResult(unittest.TestResult):
    """TestResult subclass that tracks passed test names."""

    def __init__(self):
        super().__init__()
        self.passed_names: list[str] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_names.append(test._testMethodName)


def _build_invariant_suite():
    """Build a test suite containing only the invariant tests."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    loaded = loader.loadTestsFromTestCase(TestScheduler)
    for test in loaded:
        if test._testMethodName.startswith("test_invariant_"):
            suite.addTest(test)
    return suite


def main():
    print("Running invariant tests from test_scheduler.py …\n")

    suite = _build_invariant_suite()
    if suite.countTestCases() == 0:
        print("No invariant tests found in test_scheduler.py")
        return 0

    # Capture test names before running (suite is consumed by run())
    test_names = [t._testMethodName for t in suite]

    result = _InvariantTestResult()
    suite.run(result)

    # Print per-test results
    for name in test_names:
        if name in result.passed_names:
            print(f"  ✅ {name}")
        elif any(name in str(f[0]) for f in result.failures):
            print(f"  ❌ {name}")
        elif any(name in str(e[0]) for e in result.errors):
            print(f"  💥 {name}")

    failed = [str(f[0]) for f in result.failures]
    errors = [str(e[0]) for e in result.errors]

    print()
    print("=" * 60)
    print("INVARIANT TEST SUMMARY")
    print("=" * 60)
    print(f"  Passed : {len(result.passed_names)}")
    print(f"  Failed : {len(failed)}")
    print(f"  Errors : {len(errors)}")
    if result.passed_names:
        print("\n  Passed invariant tests:")
        for name in result.passed_names:
            print(f"    ✅ {name}")
    if failed:
        print("\n  Failed invariant tests:")
        for name in failed:
            print(f"    ❌ {name}")
    if errors:
        print("\n  Errored invariant tests:")
        for name in errors:
            print(f"    💥 {name}")
    print("=" * 60)

    if result.wasSuccessful():
        print("\n✅ All invariant tests passed.")
        return 0
    else:
        print("\n❌ One or more invariant tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
MESH Test Suite Runner

This script runs all performance and security tests and generates
comprehensive HTML reports.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --performance      # Run only performance tests
    python run_tests.py --security         # Run only security tests
    python run_tests.py --quick            # Run quick smoke tests
    python run_tests.py --report           # Generate HTML report
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def create_results_dir() -> Path:
    """Create and return the results directory."""
    results_dir = get_project_root() / "results"
    results_dir.mkdir(exist_ok=True)
    return results_dir


def run_pytest(test_path: str, report_name: str, extra_args: list = None) -> int:
    """Run pytest with HTML report generation."""
    results_dir = create_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = results_dir / f"{report_name}_{timestamp}.html"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_path,
        f"--html={html_report}",
        "--self-contained-html",
        "-v",
        "-s",
    ]

    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"Report: {html_report}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=get_project_root())

    return result.returncode


def run_security_tests() -> int:
    """Run all security tests."""
    print("\n" + "=" * 60)
    print("🔒 SECURITY TESTS")
    print("=" * 60)

    return run_pytest("security/", "security_test_report")


def run_performance_tests() -> int:
    """Run performance benchmark tests."""
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE TESTS")
    print("=" * 60)

    return run_pytest(
        "performance/",
        "performance_test_report",
        extra_args=["--ignore=performance/locustfile.py", "-m", "not slow"],
    )


def run_stress_tests() -> int:
    """Run stress tests."""
    print("\n" + "=" * 60)
    print("💪 STRESS TESTS")
    print("=" * 60)

    return run_pytest("performance/test_stress.py", "stress_test_report")


def run_quick_tests() -> int:
    """Run quick smoke tests."""
    print("\n" + "=" * 60)
    print("⚡ QUICK SMOKE TESTS")
    print("=" * 60)

    # Run a subset of critical tests
    quick_tests = [
        "security/test_authentication.py::TestAuthenticationSecurity::test_tc20_forged_oauth_token_rejected",
        "security/test_authentication.py::TestAuthenticationSecurity::test_tc21_expired_token_rejected",
        "security/test_input_validation.py::TestInputValidationSecurity::test_tc25_sql_injection_in_search",
        "security/test_input_validation.py::TestInputValidationSecurity::test_tc26_xss_in_message_content",
    ]

    results_dir = create_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = results_dir / f"quick_test_report_{timestamp}.html"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *quick_tests,
        f"--html={html_report}",
        "--self-contained-html",
        "-v",
    ]

    result = subprocess.run(cmd, cwd=get_project_root())
    return result.returncode


def run_load_test(users: int = 100, duration: str = "2m") -> int:
    """Run a short load test with Locust."""
    print("\n" + "=" * 60)
    print(f"🚀 LOAD TEST ({users} users, {duration})")
    print("=" * 60)

    results_dir = create_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = results_dir / f"load_test_report_{timestamp}.html"

    host = os.getenv("TEST_URL", "http://localhost:8000")

    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "performance/locustfile.py",
        f"--host={host}",
        "--headless",
        f"--users={users}",
        f"--spawn-rate={max(1, users // 10)}",
        f"--run-time={duration}",
        f"--html={html_report}",
    ]

    print(f"Command: {' '.join(cmd)}")
    print(f"Report: {html_report}\n")

    result = subprocess.run(cmd, cwd=get_project_root())
    return result.returncode


def run_all_tests() -> int:
    """Run all tests."""
    results = []

    print("\n" + "=" * 60)
    print("🧪 RUNNING COMPLETE TEST SUITE")
    print("=" * 60)

    # Security tests
    results.append(("Security Tests", run_security_tests()))

    # Performance benchmarks
    results.append(("Performance Benchmarks", run_performance_tests()))

    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, code in results:
        status = "✅ PASSED" if code == 0 else "❌ FAILED"
        print(f"  {name}: {status}")
        if code != 0:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed!\n")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check reports for details.\n")
        return 1


def print_usage():
    """Print usage information."""
    print("""
MESH Test Suite Runner
======================

Usage:
    python run_tests.py [OPTIONS]

Options:
    --all           Run all tests (default)
    --security      Run security tests only
    --performance   Run performance benchmark tests
    --stress        Run stress tests
    --load          Run Locust load test (short)
    --quick         Run quick smoke tests
    --help          Show this help message

Environment Variables:
    TEST_URL        Base URL for tests (default: http://localhost:8000)

Examples:
    python run_tests.py --security
    TEST_URL=http://staging:8000 python run_tests.py --all
    """)


def main():
    parser = argparse.ArgumentParser(
        description="MESH Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument("--stress", action="store_true", help="Run stress tests")
    parser.add_argument("--load", action="store_true", help="Run load test")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests")
    parser.add_argument("--users", type=int, default=100, help="Users for load test")
    parser.add_argument("--duration", default="2m", help="Duration for load test")

    args = parser.parse_args()

    # Change to tests directory
    os.chdir(get_project_root())

    # Determine what to run
    if args.security:
        return run_security_tests()
    elif args.performance:
        return run_performance_tests()
    elif args.stress:
        return run_stress_tests()
    elif args.load:
        return run_load_test(args.users, args.duration)
    elif args.quick:
        return run_quick_tests()
    else:
        # Default: run all
        return run_all_tests()


if __name__ == "__main__":
    sys.exit(main())

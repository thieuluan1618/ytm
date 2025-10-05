"""Test runner script for YTM CLI tests"""

import subprocess
import sys
from pathlib import Path


def run_tests(test_type="all", coverage=True, verbose=True):
    """
    Run tests with various options

    Args:
        test_type: "all", "unit", "integration", or specific test file
        coverage: Whether to run with coverage reporting
        verbose: Whether to run in verbose mode
    """

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=ytm_cli", "--cov-report=html", "--cov-report=term-missing"])

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add test selection
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "network":
        cmd.extend(["-m", "network"])
    elif test_type != "all":
        # Assume it's a specific test file or pattern
        cmd.append(test_type)

    # Run the command
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def run_quick_tests():
    """Run quick tests without coverage for development"""
    return run_tests(test_type="all", coverage=False, verbose=False)


def run_full_tests():
    """Run full test suite with coverage"""
    return run_tests(test_type="all", coverage=True, verbose=True)


def run_unit_tests():
    """Run only unit tests"""
    return run_tests(test_type="unit", coverage=True, verbose=True)


def run_integration_tests():
    """Run only integration tests"""
    return run_tests(test_type="integration", coverage=True, verbose=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "quick":
            exit_code = run_quick_tests()
        elif test_type == "full":
            exit_code = run_full_tests()
        elif test_type == "unit":
            exit_code = run_unit_tests()
        elif test_type == "integration":
            exit_code = run_integration_tests()
        else:
            exit_code = run_tests(test_type)
    else:
        exit_code = run_full_tests()

    sys.exit(exit_code)

#!/usr/bin/env python
import argparse
import subprocess
import sys
from typing import List, Optional


def run_tests(
    category: Optional[str] = None,
    file_pattern: Optional[str] = None,
    verbose: bool = False,
    collect_only: bool = False,
    xvs: bool = False,
) -> int:
    cmd: List[str] = ["poetry", "run", "pytest"]

    # Add verbosity flag if requested
    if verbose:
        cmd.append("-v")

    # Add collect-only flag if requested
    if collect_only:
        cmd.append("--collect-only")

    # Add extra verbosity summary if requested
    if xvs:
        cmd.append("-xvs")

    # Add category marker if specified
    if category:
        cmd.extend(["-m", category])

    # Add file pattern if specified
    if file_pattern:
        cmd.append(file_pattern)

    # Run the tests
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    """Parse command-line arguments and run the tests."""
    parser = argparse.ArgumentParser(
        description="Run tests for the Aquarius project.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--category",
        "-c",
        choices=["unit", "slow", "llm", "selenium", "skip_ci"],
        help="Test category to run (based on pytest markers)",
    )

    parser.add_argument(
        "--file",
        "-f",
        dest="file_pattern",
        help="Pattern to match specific test files (e.g., 'tests/unit/agent/test_facade.py')",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Collect tests without running them",
    )

    parser.add_argument(
        "--xvs",
        action="store_true",
        help="Show extra test summary info",
    )

    args = parser.parse_args()

    # Run tests with command-line options
    return run_tests(
        category=args.category,
        file_pattern=args.file_pattern,
        verbose=args.verbose,
        collect_only=args.collect_only,
        xvs=args.xvs,
    )


if __name__ == "__main__":
    sys.exit(main())

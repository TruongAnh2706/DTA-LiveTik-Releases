"""One-line Quality Gate verification script for DTA AutoLive."""

import subprocess
import sys


def run_command(cmd: str) -> None:
    """Run shell command and check status."""
    print(f"--> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"[FAIL] Quality Gate Failed at command: {cmd}")
        sys.exit(res.returncode)


def main() -> None:
    """Run full Quality Gate checks."""
    print("=== DTA AUTOLIVE QUALITY GATE CHECK ===")
    run_command("ruff check .")
    run_command("mypy src/")
    run_command("pytest tests/")
    print("[SUCCESS] ALL QUALITY GATE CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()

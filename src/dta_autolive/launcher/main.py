"""Headless CLI Entry Point for DTA AutoLive Backend Service Daemon."""

import asyncio
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

from dta_autolive.launcher.backend_service import DTABackendService


def main() -> None:
    """Run DTA AutoLive Headless Backend Service."""
    service = DTABackendService(host="127.0.0.1", port=8765)
    try:
        asyncio.run(service.start())
    except (KeyboardInterrupt, SystemExit):
        print("\n[DTA AutoLive] Backend Service Stopped.")


if __name__ == "__main__":
    main()

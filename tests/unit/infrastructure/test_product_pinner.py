"""Unit tests for ProductPinnerManager."""

from typing import Any

from dta_autolive.infrastructure.product_pinner import ProductPinnerManager


def test_product_pinner_initialization() -> None:
    """Test default initialization values of ProductPinnerManager."""
    pinner = ProductPinnerManager()
    assert pinner.is_running is False
    assert pinner.mode == "ping_pong"
    assert pinner.cdp_port == 9222
    assert pinner.interval_seconds == 10


def test_product_pinner_callbacks() -> None:
    """Test log and event callbacks dispatch properly."""
    logs: list[tuple[str, str]] = []
    statuses: list[tuple[str, str]] = []
    events: list[dict[str, Any]] = []

    def on_log(tag: str, text: str) -> None:
        logs.append((tag, text))

    def on_status(text: str, color: str) -> None:
        statuses.append((text, color))

    def on_event(data: dict[str, Any]) -> None:
        events.append(data)

    pinner = ProductPinnerManager(log_callback=on_log, status_callback=on_status, event_callback=on_event)

    pinner.log("INFO", "Test message")
    assert len(logs) == 1
    assert logs[0] == ("INFO", "Test message")

    pinner.set_status("Active", "#00FF00")
    assert len(statuses) == 1
    assert statuses[0] == ("Active", "#00FF00")


def test_product_pinner_start_stop() -> None:
    """Test start_pinning and stop_pinning state transitions."""
    pinner = ProductPinnerManager()
    pinner.start_pinning(product_ids_str="1, 2, 3", interval_sec=5, mode="random")

    assert pinner.is_running is True
    assert pinner.product_list == ["1", "2", "3"]
    assert pinner.interval_seconds == 5
    assert pinner.mode == "random"

    pinner.stop_pinning()
    assert pinner.is_running is False

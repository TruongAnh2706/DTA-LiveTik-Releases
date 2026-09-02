"""Unit tests for DTA Audio Driver Installer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dta_autolive.infrastructure.dta_audio_driver import (
    check_virtual_audio_installed,
    register_dta_audio_friendly_name,
)


def test_check_virtual_audio_installed_mock() -> None:
    """Test checking virtual audio device with mock subprocess."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="CABLE Input (VB-Audio Virtual Cable)\nCABLE Output"
        )
        assert check_virtual_audio_installed() is True

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Realtek Audio\nMicrophone")
        assert check_virtual_audio_installed() is False


def test_register_dta_audio_friendly_name() -> None:
    """Test registry write function handles gracefully."""
    register_dta_audio_friendly_name()

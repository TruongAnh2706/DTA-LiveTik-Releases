"""Unit tests for repository foundation and packages structure."""

import dta_autolive


def test_package_metadata() -> None:
    """Verify package version and metadata."""
    assert dta_autolive.__version__ == "2.4.0"
    assert "DTA Studio" in dta_autolive.__author__


def test_conftest_fixture(sample_fixture: str) -> None:
    """Verify pytest fixture setup."""
    assert sample_fixture == "DTA AutoLive Ready"

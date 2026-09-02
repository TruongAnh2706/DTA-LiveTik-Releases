"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_fixture() -> str:
    """Sample fixture for foundation testing."""
    return "DTA AutoLive Ready"

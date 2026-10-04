"""Shared Home Assistant test configuration."""

import pytest


@pytest.fixture(autouse=True)
def enable_custom_integrations_for_tests(enable_custom_integrations):
    """Allow Home Assistant to load integrations from custom_components."""
    yield

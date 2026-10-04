"""Shared Home Assistant test configuration."""

from pathlib import Path

import pytest

import custom_components

PROJECT_CUSTOM_COMPONENTS = str(Path(__file__).parents[1] / "custom_components")

if PROJECT_CUSTOM_COMPONENTS not in custom_components.__path__:
    custom_components.__path__.append(PROJECT_CUSTOM_COMPONENTS)


@pytest.fixture(autouse=True)
def enable_custom_integrations_for_tests(enable_custom_integrations):
    """Allow Home Assistant to load integrations from custom_components."""
    yield

import sys
from unittest.mock import MagicMock

import pytest


def pytest_configure(config):
    """
    Global mock for mistralai to ensure tests run even if package is missing
    or has version conflicts in the environment.
    """
    if "mistralai" not in sys.modules:
        mock_mistral = MagicMock()
        sys.modules["mistralai"] = mock_mistral
        sys.modules["mistralai.client"] = mock_mistral
        sys.modules["mistralai.models"] = mock_mistral

import sys
from unittest.mock import MagicMock

# Mock mistralai for all tests to avoid ModuleNotFoundError
sys.modules["mistralai"] = MagicMock()

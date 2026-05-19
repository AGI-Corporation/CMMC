import sys
from unittest.mock import MagicMock

# Mock mistralai before any imports happen
sys.modules["mistralai"] = MagicMock()

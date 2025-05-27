"""Common initialization for E2E tests."""

import os
import sys

# Add the e2e directory to the path so imports work correctly
e2e_dir = os.path.dirname(os.path.abspath(__file__))
if e2e_dir not in sys.path:
    sys.path.insert(0, e2e_dir)
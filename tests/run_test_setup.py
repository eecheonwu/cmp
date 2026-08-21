"""Wrapper to run test_setup.py with proper error handling."""
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from tests.test_setup import main
    sys.exit(main())
except Exception as e:
    print(f"Error running tests: {e}")
    traceback.print_exc()
    sys.exit(1)
"""
Pytest configuration for test suite.

This file automatically configures the Python path to include the src/ directory,
allowing tests to import source modules without modification.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / 'src'
sys.path.insert(0, str(src_dir))

print(f"Test suite initialized. Source directory: {src_dir}")

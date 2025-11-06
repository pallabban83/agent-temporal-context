#!/bin/bash

# Test runner script for Temporal Context RAG Agent
# Convenience wrapper around pytest

cd "$(dirname "$0")"

echo "========================================================================"
echo "Temporal Context RAG Agent - Test Suite"
echo "========================================================================"

# Check if pytest is installed
if ! python3 -m pytest --version > /dev/null 2>&1; then
    echo "❌ ERROR: pytest not found!"
    echo ""
    echo "Please install pytest:"
    echo "    pip install pytest pytest-cov"
    echo ""
    echo "Or install all dependencies:"
    echo "    pip install -r requirements.txt"
    exit 1
fi

# Run pytest with all arguments passed to this script
python3 -m pytest test/ "$@"

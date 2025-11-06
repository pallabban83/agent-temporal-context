#!/bin/bash

# Launcher script for Temporal Context RAG Agent backend

cd "$(dirname "$0")"

echo "========================================================================"
echo "Starting Temporal Context RAG Agent - Backend Server"
echo "========================================================================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if required packages are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ ERROR: Required packages not found!"
    echo ""
    echo "Please install dependencies first:"
    echo "    pip install -r requirements.txt"
    exit 1
fi

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run the FastAPI application
echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo "========================================================================"
echo ""

cd src
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

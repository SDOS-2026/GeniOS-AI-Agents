#!/bin/bash
# Start script for the EmailAgent Service

# Get the script's directory (EmailAgent)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Root directory is one level up
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Ensure we are in the root directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Add both root and EmailAgent to PYTHONPATH so mixed imports work
export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/EmailAgent"

# Start the service
echo "Starting EmailAgent on port 8002..."
cd "$SCRIPT_DIR"
uvicorn main:app --port 8002 --reload

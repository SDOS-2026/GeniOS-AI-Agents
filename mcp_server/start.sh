#!/bin/bash
# Force the Python path to the absolute root of the Render project
export PYTHONPATH=/opt/render/project/src

# Run uvicorn using the full package path
exec uvicorn mcp_server.main:app --host 0.0.0.0 --port 9000
#!/bin/bash
# 1. Stay in the project root
# 2. Tell Python where the root is
export PYTHONPATH=$PYTHONPATH:.

# 3. Use the dot-notation to start the app
exec uvicorn mcp_server.main:app --host 0.0.0.0 --port 9000
#!/bin/bash
# 1. Standard paths
export PYTHONPATH=/opt/render/project/src
export GOOGLE_CREDENTIALS_PATH=/etc/secrets/credentials.json

# 2. Copy the read-only secret token to a writable location
# This ensures the app has a token to start with, but can also overwrite it.
if [ -f /etc/secrets/token.json ]; then
    cp /etc/secrets/token.json /opt/render/project/src/token.json
fi

# 3. Tell the Python app to use the writable copy
export GOOGLE_TOKEN_PATH=/opt/render/project/src/token.json

# exec uvicorn mcp_server.main:app --host 0.0.0.0 --port 9000

exec uvicorn mcp_server.main:app --host 0.0.0.0 --port 9000 --timeout-keep-alive 120 --workers 1
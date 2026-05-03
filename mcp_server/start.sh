#!/bin/bash
# Remove 'mcp_server.' from the path because we are already in that directory
exec uvicorn main:app --host 0.0.0.0 --port 9000
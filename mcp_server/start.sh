#!/bin/bash
exec uvicorn mcp_server.main:app --host 0.0.0.0 --port 9000
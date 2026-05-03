#!/bin/bash

# If the venv exists locally, activate it
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
elif [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
fi

# Run uvicorn. 
# Added --host 0.0.0.0 which is REQUIRED for Render/Docker to see the service.
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8001
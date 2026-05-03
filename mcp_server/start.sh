#!/bin/bash
# We use the full dot-notation path because the script starts from the project root
exec uvicorn main:app --host 0.0.0.0 --port 9000
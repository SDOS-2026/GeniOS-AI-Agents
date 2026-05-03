#!/bin/bash
# Added --host 0.0.0.0 to make it accessible to Render
uvicorn gateway.main:app --host 0.0.0.0 --port 8000
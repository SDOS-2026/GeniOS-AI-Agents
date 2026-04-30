#!/bin/bash
source ./venv/bin/activate && uvicorn app.api.main:app --reload --port 8001

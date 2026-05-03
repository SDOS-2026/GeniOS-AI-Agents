#!/bin/bash

# Ensure we are in the root directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# Activate virtual environment
source venv/bin/activate
# Start the service
RUN_DAA_INTEGRATION=1 MCP_SERVER_URL=http://localhost:9000 pytest -q

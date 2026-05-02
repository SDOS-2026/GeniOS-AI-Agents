#!/bin/bash
# Start script for the Streamlit Frontend

# Ensure we are in the frontend directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# Activate virtual environment
source venv/bin/activate

# Start Streamlit
echo "Starting GeniOS DAA Frontend on port 8501..."
streamlit run app.py --server.port 8501

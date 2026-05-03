#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# Only source if venv exists (prevents crash on Render)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "Starting GeniOS DAA Frontend on port 8501..."
# Added --server.address 0.0.0.0
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
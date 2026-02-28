#!/bin/bash

# Navigate to the directory containing this script
cd "$(dirname "$0")"

# Check for virtual environment directory (.venv or venv)
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
else
    echo "Error: Virtual environment not found."
    echo "Please create it using: python -m venv .venv"
    echo "And install dependencies: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "Starting OSC Server using environment in $VENV_DIR..."
echo "Note: Asking for sudo password because Hardware PWM requires root privileges."

# Run the server using the python executable from the virtual environment
"./$VENV_DIR/bin/python" osc_server.py

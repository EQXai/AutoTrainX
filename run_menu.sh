#!/bin/bash
# Run AutoTrainX interactive menu with virtual environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "Virtual environment activated: $(which python)"
else
    echo "No virtual environment found. Running with system Python..."
fi

# Run the interactive menu
echo "Starting AutoTrainX Interactive Menu..."
python src/menu/interactive_menu.py
#!/bin/bash

# If installer exists, delete it seamlessly
[ -f install.sh ] && rm -f install.sh

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run install.sh first."
    exit 1
fi

# Execute an interactive bash shell that inherits the active environment
exec bash -c 'source venv/bin/activate && clear && mc-dl --help && exec bash'

#!/bin/bash
echo "=============================================="
echo "Installing EnderPull..."
echo "=============================================="

echo "Creating Python virtual environment..."
python3 -m venv venv || python -m venv venv
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment. Ensure Python 3 is installed."
    exit 1
fi

echo "Activating environment and installing EnderPull..."
source venv/bin/activate
pip install -e .

echo "Cleaning up unnecessary installation files..."
rm -f install.bat
rm -f requirements.txt

echo "=============================================="
echo "Success! EnderPull has been installed."
echo "You can now use the 'mc-dl' command in this environment."
echo "=============================================="

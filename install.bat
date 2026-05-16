@echo off
setlocal

echo ==============================================
echo Installing EnderPull...
echo ==============================================

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python and try again.
    pause
    exit /b 1
)

echo [ 🛠️ ] Initializing isolated environment...
python -m venv venv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [ 📥 ] Installing dependencies and registering EnderPull...
call venv\Scripts\activate >nul 2>&1
pip install -e . >nul 2>&1

echo [ 🪄 ] Generating launch script...
echo @echo off > launch.bat
echo venv\Scripts\python.exe -m enderpull %%* >> launch.bat

echo [ 🧹 ] Performing deep cleanup...
if exist requirements.txt del requirements.txt
if exist README.md del README.md
if exist .gitignore del .gitignore
if exist install.sh del install.sh

echo ==============================================
echo [ ✔️ ] Installation Complete!
echo ==============================================
timeout /t 2 /nobreak >nul

call launch.bat --help

del "%~f0"

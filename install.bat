@echo off
echo ==============================================
echo Installing EnderPull...
echo ==============================================

echo Creating Python virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment. Ensure Python is installed.
    pause
    exit /b %errorlevel%
)

echo Activating environment and installing EnderPull...
call venv\Scripts\activate
pip install -e .

echo Cleaning up unnecessary installation files...
if exist install.sh del install.sh
if exist requirements.txt del requirements.txt

echo ==============================================
echo Success! EnderPull has been installed.
echo You can now use the 'mc-dl' command in this environment.
echo ==============================================
pause

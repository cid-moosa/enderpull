@echo off
setlocal EnableDelayedExpansion

:: Define ANSI Colors
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "CYAN=%ESC%[36m"
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "RESET=%ESC%[0m"
set "BOLD=%ESC%[1m"

cls
echo %CYAN%%BOLD%==============================================%RESET%
echo %CYAN%%BOLD%          [ ENDERPULL MOD MANAGER ]           %RESET%
echo %CYAN%%BOLD%==============================================%RESET%
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[ERROR] Python is not installed or not in PATH. Please install Python and try again.%RESET%
    pause
    exit /b 1
)

echo [ %CYAN%WORKING%RESET% ] 🛠️  Creating isolated virtual environment...
python -m venv venv >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[ERROR] Failed to create virtual environment.%RESET%
    pause
    exit /b 1
)

echo [ %CYAN%WORKING%RESET% ] 📥  Downloading dependencies and caching files...
call venv\Scripts\activate >nul 2>&1
pip install -e . >nul 2>&1

echo [ %CYAN%WORKING%RESET% ] 🪄  Generating launch script and cleaning up...
echo @echo off > launch.bat
echo venv\Scripts\python.exe -m enderpull %%* >> launch.bat

if exist requirements.txt del requirements.txt
if exist README.md del README.md
if exist .gitignore del .gitignore
if exist install.sh del install.sh

:: Transition
cls

echo %GREEN%%BOLD%[ SUCCESS ]%RESET% 🎉 EnderPull Installed Successfully!
echo %CYAN%==============================================%RESET%
echo.

call launch.bat --help

echo.
echo %YELLOW%Press any key to exit...%RESET%
pause >nul

(goto) 2>nul ^& del "%~f0"

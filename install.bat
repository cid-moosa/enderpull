@echo off
setlocal EnableDelayedExpansion

:: Force UTF-8 Mode so emojis and colors don't break
chcp 65001 >nul
cls

:: Define ANSI Colors
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "CYAN=%ESC%[36m"
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "RESET=%ESC%[0m"
set "BOLD=%ESC%[1m"

echo %CYAN%%BOLD%==============================================%RESET%
echo %CYAN%%BOLD%          [ ENDERPULL MOD MANAGER ]           %RESET%
echo %CYAN%%BOLD%==============================================%RESET%
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[ERROR] Python is not installed or not in PATH.%RESET%
    pause
    exit /b 1
)

echo %CYAN%[ WORKING ] 🛠️  Initializing EnderPull Setup Wizard...%RESET%

:: Simple Animation
<nul set /p =.
timeout /t 1 >nul
<nul set /p =.
timeout /t 1 >nul
<nul set /p =.
echo.

echo %CYAN%[ WORKING ] 🛠️  Creating isolated virtual environment...%RESET%
python -m venv venv >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[ERROR] Failed to create virtual environment.%RESET%
    pause
    exit /b 1
)

echo %CYAN%[ WORKING ] 📥  Downloading dependencies and caching files...%RESET%
call venv\Scripts\activate >nul 2>&1
pip install -e . >nul 2>&1

:: Cleanup phase
if exist requirements.txt del requirements.txt >nul 2>&1
if exist install.sh del install.sh >nul 2>&1
if exist launch.sh del launch.sh >nul 2>&1
if exist .gitignore del .gitignore >nul 2>&1
if exist README.md del README.md >nul 2>&1

cls
echo %GREEN%[ SUCCESS ] 🎉 EnderPull Installed Successfully!%RESET%
echo --------------------------------------------------
echo %YELLOW%Transitioning to your interactive modding terminal...%RESET%
timeout /t 3 >nul

:: Handoff execution permanently to the standalone launcher (this naturally terminates install.bat)
launch.bat

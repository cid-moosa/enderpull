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

:: Generate the upgraded launch.bat file
echo @echo off > launch.bat
echo chcp 65001 ^^>nul >> launch.bat
echo :: This opens a new CMD window, activates the venv, clears the screen, and stays OPEN >> launch.bat
echo start cmd /k "call venv\Scripts\activate ^&^& cls ^&^& mc-dl --help" >> launch.bat

:: Cleanup phase
del requirements.txt >nul 2>&1
del install.sh >nul 2>&1
del .gitignore >nul 2>&1
del README.md >nul 2>&1

cls
echo %GREEN%[ SUCCESS ] 🎉 EnderPull Installed Successfully!%RESET%
echo --------------------------------------------------
echo %YELLOW%Launching your automated modding terminal now...%RESET%
timeout /t 3 >nul

:: Automatically trigger the new launcher
call launch.bat

:: Self-destruct the installer
(goto) 2>nul ^& del "%~f0"

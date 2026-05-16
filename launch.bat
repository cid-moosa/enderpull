@echo off
chcp 65001 >nul

:: If the installer still exists, delete it seamlessly
if exist install.bat del install.bat >nul 2>&1

if not exist venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

:: Keep the current window open, activate venv, and show help menu
cmd /k "call venv\Scripts\activate && cls && mc-dl --help"

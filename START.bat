@echo off
chcp 65001 >nul
title AI SMM Manager
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run bootstrap_sprint1.ps1
    pause
    exit /b 1
)

echo Starting AI SMM Manager...
venv\Scripts\python.exe AI_SMM_Work_Architecture_A75\app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Exit code: %errorlevel%
    pause
)
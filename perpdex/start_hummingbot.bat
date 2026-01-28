@echo off
REM Hummingbot Start Script
REM This script activates the conda environment and starts Hummingbot

echo ========================================
echo Starting Hummingbot with Python 3.12
echo ========================================
echo.

REM Change to hummingbot directory
cd /d "C:\Users\crypto quant\perpdex\hummingbot"

REM Activate conda environment and run hummingbot
call "C:\Users\crypto quant\anaconda3\Scripts\activate.bat" hummingbot
python bin\hummingbot.py

pause

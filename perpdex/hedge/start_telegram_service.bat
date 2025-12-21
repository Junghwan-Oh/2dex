@echo off
REM Telegram Service Starter for Hedge Bot
REM This service runs independently and handles menu/help/balance/position commands
REM even when the trading bot is not running.

echo =============================================
echo   Telegram Service for Hedge Bot
echo =============================================
echo.
echo This service provides:
echo   - /menu, /help : Always available
echo   - balance, position, status : Always available
echo   - stop, kill : Only when bot is running
echo.
echo Press Ctrl+C to stop the service.
echo =============================================
echo.

cd /d %~dp0
python telegram_service.py

pause

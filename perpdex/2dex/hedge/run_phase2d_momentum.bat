@echo off
echo Starting Phase 2D Momentum Strategy - 100 iterations
echo ========================================================
echo.
echo PRIMARY: GRVT (maker)
echo HEDGE: Backpack (taker)
echo TICKER: XRP
echo SIZE: 0.1
echo ITERATIONS: 100
echo.
echo This will take 1-2 hours to complete.
echo Output will be logged to logs/2dex_grvt_backpack_XRP_log.txt
echo.
f:\Dropbox\dexbot\perpdex\venv\Scripts\python.exe hedge_mode_2dex.py --primary grvt --hedge backpack --ticker XRP --size 0.1 --iter 100
echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

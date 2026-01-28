@echo off
echo ========================================================
echo Phase 2B Mean Reversion - 100 iterations FULL TEST
echo ========================================================
echo.
echo PRIMARY: GRVT (maker)
echo HEDGE: Backpack (taker)
echo TICKER: XRP
echo SIZE: 0.1
echo ITERATIONS: 100
echo.
echo This will take 2-4 hours to complete (no timeout).
echo Output will be logged to logs/2dex_grvt_backpack_XRP_log.txt
echo CSV trades: logs/2dex_grvt_backpack_XRP_trades.csv
echo.
f:\Dropbox\dexbot\perpdex\venv\Scripts\python.exe hedge_mode_2dex.py --primary grvt --hedge backpack --ticker XRP --size 0.1 --iter 100
echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
echo.
pause

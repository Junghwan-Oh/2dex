@echo off
echo ========================================================
echo DN Alternate Backpack-GRVT Strategy - 200 Cycles
echo ========================================================
echo PRIMARY: Backpack (maker)
echo HEDGE: GRVT (taker)
echo STRATEGY: Alternate
echo TICKER: ETH
echo SIZE: 0.033 (approx $100)
echo ITERATIONS: 200
echo.
echo Estimated time: ~2 hours
echo Output will be logged to logs/DN_alternate_backpack_grvt_*_log.txt
echo.

cd /d "%~dp0"
python DN_alternate_backpack_grvt.py --ticker ETH --size 0.033 --iter 200 --primary backpack --hedge grvt --primary-mode bbo_minus_1 --hedge-mode market

echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

@echo off
echo ========================================================
echo DN Alternate Backpack-GRVT Test - 0.01 ETH, 5 Cycles
echo ========================================================
echo PRIMARY: Backpack (maker)
echo HEDGE: GRVT (taker)
echo TICKER: ETH
echo SIZE: 0.01
echo ITERATIONS: 5
echo.
echo Estimated time: ~5-10 minutes
echo Output will be logged to logs/DN_alternate_backpack_grvt_*_log.txt
echo.

cd /d "%~dp0"
python DN_alternate_backpack_grvt.py --ticker ETH --size 0.01 --iter 5 --primary backpack --hedge grvt --primary-mode bbo_minus_1 --hedge-mode market

echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

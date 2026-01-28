@echo off
echo ========================================================
echo DN Alternate Backpack-GRVT Test - 0.5 ETH, 10 Cycles
echo ========================================================
echo PRIMARY: Backpack (maker)
echo HEDGE: GRVT (taker)
echo TICKER: ETH
echo SIZE: 0.5
echo ITERATIONS: 10
echo.
echo Estimated time: ~15-20 minutes
echo Output will be logged to logs/DN_alternate_backpack_grvt_*_log.txt
echo.

cd /d "%~dp0"
python DN_alternate_backpack_grvt.py --ticker ETH --size 0.5 --iter 10 --primary backpack --hedge grvt --primary-mode bbo_minus_1 --hedge-mode market

echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

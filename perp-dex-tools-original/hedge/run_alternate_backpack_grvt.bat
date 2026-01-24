@echo off
echo ========================================================
echo DN Alternate Backpack-GRVT Strategy
echo ========================================================
echo PRIMARY: Backpack (maker)
echo HEDGE: GRVT (taker)
echo STRATEGY: Alternate
echo TICKER: SOL
echo SIZE: 0.01
echo ITERATIONS: 1
echo.
echo This will take 2-5 minutes to complete.
echo Output will be logged to logs/DN_alternate_backpack_grvt_*_log.txt
echo.
echo Improvements included:
echo - TradeMetrics dataclass for detailed execution tracking
echo - Repricing limit increased to 5 attempts
echo - Maker timeout optimized to 8s
echo - Position reconciliation with >0.001 discrepancy detection
echo - Auto-recovery threshold at 0.01 net delta
echo - Duplicate fill confirmation loop removed
echo.

cd /d "%~dp0"
python DN_alternate_backpack_grvt.py --ticker SOL --size 0.01 --iter 1 --primary backpack --hedge grvt --primary-mode bbo_minus_1 --hedge-mode market

echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

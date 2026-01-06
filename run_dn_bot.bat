@echo off
REM DN Hedge Bot Runner (Paradex + GRVT)
REM Usage: run_dn_bot.bat [iterations]

set ITER=%1
if "%ITER%"=="" set ITER=10

echo ========================================
echo DN Hedge Bot: Paradex + GRVT
echo Ticker: SOL, Size: 0.1, Iterations: %ITER%
echo ========================================

conda run -n quant python hedge_mode.py --exchange paradex --ticker SOL --size 0.1 --iter %ITER%

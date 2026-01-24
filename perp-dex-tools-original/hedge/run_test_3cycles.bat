@echo off
echo ========================================================
echo QUICK TEST - 3 Cycles (Phase 1-3 Improvements)
echo ========================================================
echo.
echo PRIMARY: Paradex (maker)
echo HEDGE: GRVT (taker)
echo TICKER: ETH
echo SIZE: 0.01
echo ITERATIONS: 3
echo.
echo This will take 2-5 minutes to complete.
echo Output will be logged to logs/DN_alternate_grvt_paradex_ETH_log.txt
echo.
echo Improvements tested:
echo - Phase 1: Duplicate loop removed, timeout 20s->8s
echo - Phase 2: Auto-recovery 0.06->0.01, reconcile improved, sync 5->3
echo - Phase 3: Repricing 3->5, force close wait 5s->3s
echo.
f:\Dropbox\dexbot\perpdex\venv\Scripts\python.exe f:\Dropbox\dexbot\perp-dex-tools-original\hedge\DN_alternate_grvt_paradex.py --iter 3
echo.
echo ========================================================
echo Execution completed. Check logs directory for results.
pause

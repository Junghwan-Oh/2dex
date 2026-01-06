@echo off
REM Test Paradex + GRVT connections
echo Testing connections...
conda run -n quant python test_dn_paradex_grvt.py
pause

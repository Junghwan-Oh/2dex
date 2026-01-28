# Phase 2D Momentum Strategy - 100 iterations runner
# This script runs the trading bot in background and saves output

$pythonExe = "f:\Dropbox\dexbot\perpdex\venv\Scripts\python.exe"
$script = "hedge_mode_2dex.py"
$args = "--primary grvt --hedge backpack --ticker XRP --size 0.1 --iter 100"
$outputFile = "phase2d_execution_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Phase 2D Momentum Strategy - 100 Iterations" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  PRIMARY: GRVT (maker orders)" -ForegroundColor White
Write-Host "  HEDGE: Backpack (taker orders)" -ForegroundColor White
Write-Host "  TICKER: XRP" -ForegroundColor White
Write-Host "  SIZE: 0.1" -ForegroundColor White
Write-Host "  ITERATIONS: 100" -ForegroundColor White
Write-Host ""
Write-Host "Output file: $outputFile" -ForegroundColor Magenta
Write-Host "Expected runtime: 1-2 hours" -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting execution..." -ForegroundColor Green
Write-Host ""

# Run the Python script and capture output
& $pythonExe $script $args.Split(' ') 2>&1 | Tee-Object -FilePath $outputFile

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Execution completed!" -ForegroundColor Green
Write-Host "Check logs/2dex_grvt_backpack_XRP_log.txt for details" -ForegroundColor White
Write-Host "Check logs/2dex_grvt_backpack_XRP_trades.csv for trades" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan

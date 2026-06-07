# Launch GeoViewer in Google Chrome
$port = 8501
$url  = "http://localhost:$port"

# Activate venv and start Streamlit (headless = no auto browser)
$streamlit = Join-Path $PSScriptRoot ".venv\Scripts\streamlit.exe"
$job = Start-Job -ScriptBlock {
    param($exe, $app)
    & $exe run $app --server.headless true --server.port 8501
} -ArgumentList $streamlit, (Join-Path $PSScriptRoot "app.py")

Write-Host "Starting GeoViewer..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Open in Chrome (try both common install paths)
$chrome = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chrome) {
    Start-Process $chrome $url
    Write-Host "Opened $url in Chrome." -ForegroundColor Green
} else {
    Write-Host "Chrome not found. Open manually: $url" -ForegroundColor Yellow
    Start-Process $url
}

Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Cyan
Wait-Job $job | Receive-Job

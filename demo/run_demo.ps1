<#
Quick demo run-through for Locator Finder Agent (Windows PowerShell)

Run from the repository root (where requirements.txt lives):
  PowerShell> .\demo\run_demo.ps1

The script will:
 - create and activate a venv (if needed)
 - install Python deps and Playwright browsers (if not already installed)
 - launch the FastAPI server in a new PowerShell window
 - create and activate a browser session
 - open a URL you provide (you can log in manually in the opened browser)
 - call describe for a sample element description and show the results
 - highlight the best locator

This script tries to be helpful but you may prefer to run steps manually.
#>

Set-StrictMode -Version Latest

function Ensure-Venv {
    if (-not (Test-Path -Path .venv)) {
        python -m venv .venv
    }
    $activate = Join-Path -Path '.venv' -ChildPath 'Scripts\Activate.ps1'
    . $activate
}

Write-Host "=== Locator Finder Agent demo script ==="
Write-Host "Ensure you're in the project root: $(Get-Location)"

# Ensure venv and deps
Ensure-Venv
Write-Host "Installing Python dependencies (may take a minute)..."
pip install -r requirements.txt
Write-Host "Installing Playwright browsers (chromium)..."
python -m playwright install chromium

# Launch server in new window
Write-Host "Starting FastAPI server in a new PowerShell window..."
$uvicornCmd = 'python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000'
Start-Process powershell -ArgumentList "-NoExit","-Command","$uvicornCmd"

Write-Host "Waiting for server to become available (http://127.0.0.1:8000)..."
for ($i=0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/ -TimeoutSec 2
        if ($r.StatusCode -eq 200) { break }
    } catch { Start-Sleep -Seconds 1 }
}

Write-Host "Creating a demo session..."
$sess = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/sessions -Body (@{name='demo'} | ConvertTo-Json) -ContentType 'application/json'
Write-Host "Session created: $($sess.id)"

Write-Host "Activating session (allocates browser context/page)..."
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/sessions/$($sess.id)/activate" -ContentType 'application/json' -Body '{}'

$url = Read-Host "Enter the URL to open (e.g. https://example.com)
The browser window will open; if the page requires login, log in manually then press Enter to continue"
if ($url) {
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/open -Body (@{url=$url; session=$sess.id} | ConvertTo-Json) -ContentType 'application/json'
}

Read-Host "If you needed to log in, do it now in the opened browser, then press Enter to continue"

$desc = Read-Host "Enter a short description to search for (e.g. 'login', 'email', 'submit')"
$res = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/describe -Body (@{description=$desc; session=$sess.id} | ConvertTo-Json) -ContentType 'application/json'

Write-Host "Describe results (raw JSON):"
$res | ConvertTo-Json -Depth 5

if ($res.matches -and $res.matches.Count -gt 0) {
    $first = $res.matches[0].ranked.chosen_best ?: $res.matches[0].ranked.best
    Write-Host "Highlighting best locator: $($first.type) $($first.value)"
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/highlight -Body (@{type=$first.type; value=$first.value; session=$sess.id} | ConvertTo-Json) -ContentType 'application/json'
    Write-Host "Highlighted. Press Enter to remove highlight..."
    Read-Host
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/unhighlight -Body (@{session=$sess.id} | ConvertTo-Json) -ContentType 'application/json'
}

Write-Host "Demo complete. You can close the browser window and stop the uvicorn server when finished."
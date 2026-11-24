# One-time setup on Windows (PowerShell). Needs Node 18+, Python 3.9+ and ffmpeg already installed.
Set-Location $PSScriptRoot
npm install
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python tools/check_env.py
Write-Host "Next: add the Kenney props (public/bridge/kenney/README.md) and choose a voice engine in .env"

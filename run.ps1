Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$py312 = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $py312) {
    & py -3.12 main.py
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $python) {
    & python main.py
    exit $LASTEXITCODE
}

Write-Host 'Python launcher not found. Install Python 3 and ensure py or python is on PATH.' -ForegroundColor Red
exit 1

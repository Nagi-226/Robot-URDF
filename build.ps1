Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $pyLauncher) {
    $pyLauncher = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $pyLauncher) {
    throw 'Python launcher not found. Install Python 3 and ensure py or python is on PATH.'
}

& py -3.12 -m pip install --upgrade pip
& py -3.12 -m pip install -r requirements.txt pyinstaller
& py -3.12 -m PyInstaller --noconfirm --onefile --windowed --name 'RobotURDFStudio' main.py

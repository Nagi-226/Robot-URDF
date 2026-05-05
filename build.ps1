param(
    [ValidateSet('onefile', 'onedir')]
    [string]$Mode = 'onefile',
    [switch]$SkipInstall,
    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$pythonCandidates = @(
    ".\.venv\Scripts\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "E:\Miniconda3\python.exe",
    "python"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        $python = $cmd.Source
        break
    }
}
if ($null -eq $python) {
    throw 'Python 3.12 not found. Install the standard Windows Python 3.12 runtime or update build.ps1.'
}

if (-not $SkipInstall) {
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed with exit code $LASTEXITCODE" }
    & $python -m pip install -r requirements.txt -r requirements-dev.txt pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Default package index failed. Retrying PyInstaller from official PyPI."
        & $python -m pip install -r requirements.txt -r requirements-dev.txt --index-url https://pypi.org/simple
        if ($LASTEXITCODE -ne 0) { throw "Dependency install failed with exit code $LASTEXITCODE" }
    }
}

$pyinstallerArgs = @('--noconfirm')
if ($Mode -eq 'onedir') {
    $pyinstallerArgs += @('--onedir', '--windowed', '--name', 'RobotURDFStudio', '--specpath', 'build')
    $pyinstallerArgs += @('--icon', 'assets/icon.ico')
    $pyinstallerArgs += @('--add-data', 'assets;assets')
    $pyinstallerArgs += @('--add-data', 'models;models')
    $pyinstallerArgs += @('main.py')
} else {
    $pyinstallerArgs += @('RobotURDFStudio.spec')
}

& $python -m PyInstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

if ($SmokeTest) {
    $exePath = if ($Mode -eq 'onedir') {
        'dist\RobotURDFStudio\RobotURDFStudio.exe'
    } else {
        'dist\RobotURDFStudio.exe'
    }
    & $python scripts/package_self_test.py $exePath
    if ($LASTEXITCODE -ne 0) { throw "Package smoke test failed with exit code $LASTEXITCODE" }
}

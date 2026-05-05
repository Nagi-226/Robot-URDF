param(
    [string]$ExePath = "dist\RobotURDFStudio.exe",
    [string]$Subject = "CN=Robot URDF Studio Dev",
    [switch]$CreateCertificate,
    [switch]$AllowUntrustedDev
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Executable not found: $ExePath"
}

$cert = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Subject -eq $Subject -and $_.HasPrivateKey } |
    Select-Object -First 1

if ($null -eq $cert -and $CreateCertificate) {
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $Subject `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyUsage DigitalSignature `
        -FriendlyName "Robot URDF Studio Dev Code Signing"
}

if ($null -eq $cert) {
    throw "No code-signing certificate found for $Subject. Re-run with -CreateCertificate for dev signing."
}

$signature = Set-AuthenticodeSignature -FilePath $ExePath -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
if ($signature.Status -ne "Valid" -and -not ($CreateCertificate -or $AllowUntrustedDev)) {
    throw "Signing failed: $($signature.Status) $($signature.StatusMessage)"
}

if ($signature.Status -ne "Valid") {
    Write-Warning "Dev signature was applied but is not trusted yet: $($signature.Status) $($signature.StatusMessage)"
    Write-Warning "For local trust, import the dev certificate into Trusted Root Certification Authorities, or use a release code-signing certificate."
} else {
    Write-Host "Signed $ExePath with $($cert.Subject)"
}

#Requires -Version 5.1
<#
.SYNOPSIS
    Builds the Windows installer for ToolForge and optionally signs it.

.DESCRIPTION
    Requires Inno Setup 6 (ISCC.exe). The frontend must already be built
    (frontend\dist\index.html); if it is missing and npm is available, the
    script runs `npm run build` once.

    Signing is optional. Set TOOLFORGE_SIGN_CERT to either a certificate
    thumbprint in the Windows certificate store or the path to a .pfx file.
    For a .pfx file, TOOLFORGE_SIGN_PASSWORD may contain its password.
    A timestamp is requested from $TimestampUrl.

.EXAMPLE
    .\build_installer.ps1

.EXAMPLE
    $env:TOOLFORGE_SIGN_CERT = 'C:\certs\toolforge.pfx'
    $env:TOOLFORGE_SIGN_PASSWORD = '...'
    .\build_installer.ps1 -Version 1.3
#>
[CmdletBinding()]
param(
    [string]$Version = '1.3',
    [string]$Certificate = $env:TOOLFORGE_SIGN_CERT,
    [string]$CertificatePassword = $env:TOOLFORGE_SIGN_PASSWORD,
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [switch]$SkipFrontend,
    [switch]$SkipSign
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Iss = Join-Path $PSScriptRoot 'ToolForge.iss'
$Index = Join-Path $Root 'frontend\dist\index.html'
$Output = Join-Path $Root 'dist\installer'

function Find-Executable {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string[]]$Candidates = @()
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    return $null
}

function Find-SignTool {
    $direct = Find-Executable 'signtool.exe'
    if ($direct) { return $direct }
    $bases = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'),
        (Join-Path $env:ProgramFiles 'Windows Kits\10\bin')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    foreach ($base in $bases) {
        $versions = Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        foreach ($version in $versions) {
            foreach ($arch in @('x64', 'x86')) {
                $path = Join-Path $version.FullName "$arch\signtool.exe"
                if (Test-Path -LiteralPath $path) { return $path }
            }
        }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $Iss)) {
    throw "Inno-Setup-Definition fehlt: $Iss"
}

$Iscc = Find-Executable 'iscc.exe' @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)
if (-not $Iscc) {
    throw 'Inno Setup 6 fehlt. Installation: https://jrsoftware.org/isinfo.php'
}

if (-not (Test-Path -LiteralPath $Index) -and -not $SkipFrontend) {
    $npm = Find-Executable 'npm.cmd'
    if (-not $npm) { $npm = Find-Executable 'npm' }
    if (-not $npm) {
        throw "Frontend-Build fehlt ($Index) und npm wurde nicht gefunden. Im Ordner frontend: npm ci; npm run build"
    }
    Push-Location (Join-Path $Root 'frontend')
    try {
        & $npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build ist mit Code $LASTEXITCODE fehlgeschlagen." }
    }
    finally {
        Pop-Location
    }
}
if (-not (Test-Path -LiteralPath $Index)) {
    throw "Frontend-Build fehlt: $Index"
}

New-Item -ItemType Directory -Force -Path $Output | Out-Null
Write-Host "Baue ToolForge-Setup-$Version mit $Iscc ..."
& $Iscc "/DMyAppVersion=$Version" "/O$Output" $Iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup ist mit Code $LASTEXITCODE fehlgeschlagen."
}

$Installer = Join-Path $Output "ToolForge-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $Installer)) {
    $found = Get-ChildItem -LiteralPath $Output -Filter 'ToolForge-Setup-*.exe' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $found) { throw "Installer wurde nicht erzeugt: $Installer" }
    $Installer = $found.FullName
}

$Hash = (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash
$Checksum = Join-Path $Output 'SHA256SUMS.txt'
Set-Content -LiteralPath $Checksum -Value "$Hash *$(Split-Path -Leaf $Installer)" -Encoding ASCII
Write-Host "SHA256: $Hash"
Write-Host "Pruefsumme: $Checksum"

if ($SkipSign -or -not $Certificate) {
    Write-Warning 'Kein Signaturzertifikat gesetzt (TOOLFORGE_SIGN_CERT). Der Installer bleibt unsigniert.'
    Write-Host "Installer: $Installer"
    return
}

$SignTool = Find-SignTool
if (-not $SignTool) {
    throw 'signtool.exe fehlt. Windows SDK installieren oder Pfad zu signtool in PATH aufnehmen.'
}

$SignArgs = @('sign', '/fd', 'SHA256', '/td', 'SHA256', '/tr', $TimestampUrl)
if ($Certificate -match '\.pfx$') {
    $pfx = (Resolve-Path -LiteralPath $Certificate).Path
    $SignArgs += @('/f', $pfx)
    if ($CertificatePassword) { $SignArgs += @('/p', $CertificatePassword) }
}
else {
    $SignArgs += @('/sha1', $Certificate)
}
$SignArgs += $Installer

Write-Host "Signiere Installer mit $SignTool ..."
& $SignTool @SignArgs
if ($LASTEXITCODE -ne 0) { throw "Signatur fehlgeschlagen (Code $LASTEXITCODE)." }
& $SignTool verify /pa /v $Installer
if ($LASTEXITCODE -ne 0) { throw "Signaturpruefung fehlgeschlagen (Code $LASTEXITCODE)." }
Write-Host "Signierter Installer: $Installer"

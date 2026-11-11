#Requires -Version 5.1
<#
    Build a portable Windows release of PS4 Profile Studio.

    Usage:
        .\build.ps1                 # version from ps4_avatar_qt\__init__.py
        .\build.ps1 -Version 1.0.0  # override the release version

    Output:
        release\PS4-Profile-Studio-<version>-win64.zip
        release\PS4-Profile-Studio-<version>-win64.zip.sha256
#>
[CmdletBinding()]
param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $Version) {
    $init = Get-Content "ps4_avatar_qt\__init__.py" -Raw
    if ($init -match '__version__\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    } else {
        throw "Could not read __version__ from ps4_avatar_qt\__init__.py"
    }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv (uses the global Python packages) ..."
    python -m venv .venv --system-site-packages
    & $venvPython -m pip install --quiet --upgrade pip
    & $venvPython -m pip install --quiet pyinstaller
}

& $venvPython -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller into .venv ..."
    & $venvPython -m pip install --quiet pyinstaller
}

Write-Host "Building PS4 Profile Studio $Version ..."
Remove-Item -Recurse -Force "build", "dist" -ErrorAction SilentlyContinue
Remove-Item -Force "PS4 Profile Studio.spec" -ErrorAction SilentlyContinue

& $venvPython -m PyInstaller --noconfirm --clean --windowed `
    --name "PS4 Profile Studio" `
    --add-data "ps4_avatar_qt/assets;ps4_avatar_qt/assets" `
    --exclude-module numpy `
    --exclude-module psutil `
    --exclude-module yaml `
    --exclude-module charset_normalizer `
    "profile_studio.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

$release = Join-Path $PSScriptRoot "release"
$stage = Join-Path $release "PS4 Profile Studio"
Remove-Item -Recurse -Force $release -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage -Force | Out-Null

Copy-Item "dist\PS4 Profile Studio\*" $stage -Recurse -Force
Copy-Item "LICENSE" (Join-Path $stage "LICENSE")
Copy-Item "packaging\THIRD-PARTY-NOTICES.txt" (Join-Path $stage "THIRD-PARTY-NOTICES.txt")

$readme = (Get-Content "packaging\README.txt" -Raw).Replace("@VERSION@", $Version)
[System.IO.File]::WriteAllText(
    (Join-Path $stage "README.txt"), $readme,
    (New-Object System.Text.UTF8Encoding($false)))

$zipName = "PS4-Profile-Studio-$Version-win64.zip"
$zipPath = Join-Path $release $zipName
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $stage, $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true)

$hash = (Get-FileHash $zipPath -Algorithm SHA256).Hash.ToLower()
Set-Content -Path "$zipPath.sha256" -Value "$hash  $zipName" -Encoding ASCII

$mb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
$shaBytes = (Get-Item "$zipPath.sha256").Length

$notes = (Get-Content "packaging\RELEASE-NOTES.md" -Raw).
    Replace("@VERSION@", $Version).
    Replace("@SIZE@", "$mb").
    Replace("@SHA_SIZE@", "$shaBytes").
    Replace("@SHA256@", $hash)
[System.IO.File]::WriteAllText(
    (Join-Path $release "RELEASE-NOTES-$Version.md"), $notes,
    (New-Object System.Text.UTF8Encoding($false)))

Remove-Item -Recurse -Force $stage

Write-Host ""
Write-Host "Created: $zipPath"
Write-Host "Notes:   $(Join-Path $release "RELEASE-NOTES-$Version.md")"
Write-Host "Size:    $mb MB"
Write-Host "SHA256:  $hash"

# Issue-opener uninstaller for Windows
# removes the install dir (venv included), the launcher and the
# PATH entry the installer added

$ErrorActionPreference = "Stop"

$App = "issue-opener"
$InstallDir = Join-Path $env:LOCALAPPDATA $App
$BinDir = Join-Path $InstallDir "bin"
$Launcher = Join-Path $BinDir "$App.cmd"

if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -like "*$BinDir*") {
    $newPath = ($userPath -split ";" | Where-Object { $_ -and $_ -ne $BinDir }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "removed $BinDir from the user PATH"
}

Write-Host "$App uninstalled"
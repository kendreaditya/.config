# install.ps1 — Windows bootstrap for kendreaditya/.config
# Usage: irm https://raw.githubusercontent.com/kendreaditya/.config/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'

$Repo = 'https://github.com/kendreaditya/.config.git'
$Dest = "$HOME\.config"

Write-Output "==> .config dotfiles bootstrap (platform: windows)"

# Must run as admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Warning "Please run this script in an Administrator PowerShell."
    exit 1
}

# Ensure git exists (winget comes preinstalled on Windows 11; if not, user must install App Installer)
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Output "winget not found. Install 'App Installer' from the Microsoft Store first."
        Start-Process "ms-windows-store://pdp/?ProductId=9nblggh4nns1&mode=mini"
        exit 1
    }
    Write-Output "==> Installing git..."
    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements -h | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
}

# Clone or update the repo
if (Test-Path "$Dest\.git") {
    Write-Output "==> Updating existing repo at $Dest"
    git -C $Dest pull --ff-only
} else {
    if ((Test-Path $Dest) -and (Get-ChildItem -Path $Dest -Force | Select-Object -First 1)) {
        Write-Output "==> $Dest exists but is not a git repo — backing up to $Dest.bak"
        Move-Item $Dest "$Dest.bak"
    }
    Write-Output "==> Cloning $Repo -> $Dest"
    git clone $Repo $Dest
}

# Hand off to the Windows setup script
$Script = "$Dest\setup-windows.ps1"
Write-Output "==> Running setup-windows.ps1"
& powershell -ExecutionPolicy Bypass -File $Script

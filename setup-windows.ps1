# setup-windows.ps1 — Windows setup mirroring setup-macos.sh

# Must run as admin
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Warning "Please run this script as Administrator!"
    exit
}

# winget check
if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Output "winget not found. Install 'App Installer' from the Microsoft Store, then re-run."
    Start-Process "ms-windows-store://pdp/?ProductId=9nblggh4nns1&mode=mini"
    exit
}

Write-Output "Installing packages via winget..."

# Base tools + dev packages (batched via one call each, but winget doesn't truly batch)
$packages = @(
    # Core
    'Git.Git', 'GitHub.cli', 'Microsoft.PowerShell', 'Microsoft.WindowsTerminal',
    'OpenJS.NodeJS.LTS', 'Python.Python.3.12',
    # Editors
    'Microsoft.VisualStudioCode', 'Neovim.Neovim', 'vim.vim', 'Zed.Zed',
    # CLI utilities
    'cURL.cURL', 'GnuWin32.Wget', 'BurntSushi.ripgrep.MSVC',
    'junegunn.fzf', 'yt-dlp.yt-dlp', 'mikefarah.yq', 'atuinsh.atuin',
    'fastfetch-cli.fastfetch', 'Kitware.CMake', 'LLVM.LLVM', 'GnuWin32.Make',
    # Media / OCR
    'ImageMagick.ImageMagick', 'Gyan.FFmpeg', 'UB-Mannheim.TesseractOCR',
    # Runtimes
    'Oven-sh.Bun', 'DenoLand.Deno',
    # Apps
    'Google.Chrome', 'Mozilla.Firefox', 'Doist.Todoist', 'Zoom.Zoom',
    'bruno.bruno', 'ollama.ollama', 'Warp.Warp', 'Cloudflare.Warp',
    'ProtonTechnologies.ProtonVPN', 'tailscale.tailscale',
    'Obsidian.Obsidian', 'Postman.Postman', 'AnthropicPBC.Claude',
    # Windows extras
    'Microsoft.PowerToys', 'JanDeDobbeleer.OhMyPosh'
)

foreach ($pkg in $packages) {
    Write-Output "→ $pkg"
    winget install --id $pkg -e --accept-source-agreements --accept-package-agreements -h 2>&1 | Out-Null
}

# WSL
Write-Output "Enabling WSL..."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
wsl --install -d Ubuntu --no-launch

# npm globals
Write-Output "Installing npm globals..."
npm install -g wrangler vercel pnpm typescript tailwindcss eslint yarn

# Claude Code CLI (via PowerShell bootstrap)
if (!(Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Output "Installing Claude Code..."
    iwr -useb https://claude.ai/install.ps1 | iex
}

# Python venv for .config scripts
Write-Output "Setting up .config Python venv..."
python -m venv "$HOME\.config\config-venv"
& "$HOME\.config\config-venv\Scripts\pip.exe" install --upgrade pip
& "$HOME\.config\config-venv\Scripts\pip.exe" install -r "$HOME\.config\requirements.txt"

# Workspace dir
New-Item -ItemType Directory -Force -Path "$HOME\workspace" | Out-Null

# Install licensed fonts from assets\fonts into user fonts folder
$fontsDir = "$HOME\.config\assets\fonts"
if (Test-Path $fontsDir) {
    Write-Output "Installing fonts..."
    $userFonts = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
    New-Item -ItemType Directory -Force -Path $userFonts | Out-Null
    Get-ChildItem -Path $fontsDir -Include *.otf, *.ttf -Recurse | ForEach-Object {
        $dest = Join-Path $userFonts $_.Name
        Copy-Item -Force $_.FullName $dest
        # Register with Windows
        $regPath = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
        $name = "$($_.BaseName) (TrueType)"
        New-ItemProperty -Path $regPath -Name $name -PropertyType String -Value $dest -Force | Out-Null
    }
}

# Symlink scripts to a PATH location (requires developer mode or admin for symlinks on Windows)
$scriptsTarget = "$HOME\.local\bin"
New-Item -ItemType Directory -Force -Path $scriptsTarget | Out-Null
Get-ChildItem "$HOME\.config\scripts" | Where-Object { !$_.PSIsContainer } | ForEach-Object {
    $link = Join-Path $scriptsTarget $_.Name
    if (Test-Path $link) { Remove-Item $link -Force }
    New-Item -ItemType SymbolicLink -Path $link -Target $_.FullName -ErrorAction SilentlyContinue | Out-Null
}

# Claude Code behavioral files — symlinks to %USERPROFILE%\.claude
$claudeDir = "$HOME\.claude"
New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null
$claudeLinks = @{
    'skills'        = "$HOME\.config\claude\skills"
    'commands'      = "$HOME\.config\claude\commands"
    'agents'        = "$HOME\.config\claude\agents"
    'settings.json' = "$HOME\.config\claude\settings.json"
    'CLAUDE.md'     = "$HOME\.config\claude\CLAUDE.md"
}
foreach ($name in $claudeLinks.Keys) {
    $link = Join-Path $claudeDir $name
    if (Test-Path $link) { Remove-Item $link -Force -Recurse }
    New-Item -ItemType SymbolicLink -Path $link -Target $claudeLinks[$name] -ErrorAction SilentlyContinue | Out-Null
}

# sync-docs
if (Test-Path "$scriptsTarget\sync-docs") {
    & "$scriptsTarget\sync-docs"
}

# PowerShell profile — oh-my-posh + PSReadLine
Write-Output "Configuring PowerShell profile..."
New-Item -Path $PROFILE -Type File -Force | Out-Null
$profileContent = @'
oh-my-posh init pwsh | Invoke-Expression
Import-Module PSReadLine
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView
'@
Set-Content -Path $PROFILE -Value $profileContent

# PSReadLine
Install-Module -Name PSReadLine -Force -SkipPublisherCheck -AllowClobber

# Default browser prompt
Start-Process "ms-settings:defaultapps"

# Verify
Write-Output ""
Write-Output "Verifying installation..."
foreach ($cmd in @('node', 'python', 'nvim', 'gh', 'claude', 'fastfetch')) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Output "  ✓ $cmd"
    } else {
        Write-Output "  ✗ $cmd (not in PATH — open a new shell)"
    }
}

Write-Output ""
Write-Output "Windows setup complete! Reboot to finish WSL setup."

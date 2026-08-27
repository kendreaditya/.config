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
    'jqlang.jq', 'AGWA.git-crypt', 'astral-sh.uv', 'Schniz.fnm',
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
# NOTE: jqlang.jq, AGWA.git-crypt, astral-sh.uv, and Schniz.fnm winget IDs are
# my best read of each project's current packaging, unverified against an
# actual winget source this session (no Windows machine available). If any
# ID is wrong the per-package loop below only logs and continues — it won't
# abort the rest of setup, but confirm these on first real run.

foreach ($pkg in $packages) {
    Write-Output "→ $pkg"
    winget install --id $pkg -e --accept-source-agreements --accept-package-agreements -h 2>&1 | Out-Null
}

# WSL
Write-Output "Enabling WSL..."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
wsl --install -d Ubuntu --no-launch

# npm globals (yarn removed by request — pnpm covers the same ground, matching
# the macOS/Linux cleanup)
Write-Output "Installing npm globals..."
npm install -g wrangler vercel pnpm typescript tailwindcss eslint

# Claude Code CLI (via PowerShell bootstrap)
if (!(Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Output "Installing Claude Code..."
    iwr -useb https://claude.ai/install.ps1 | iex
}

# Python venv for .config scripts. Skip creation if it already exists so a
# re-run doesn't discard installed packages.
Write-Output "Setting up .config Python venv..."
if (!(Test-Path "$HOME\.config\config-venv\Scripts\python.exe")) {
    python -m venv "$HOME\.config\config-venv"
}
# uv (10-100x faster than pip, resolves the whole set at once) rather than
# pip, matching macOS/Linux. The venv itself stays a plain stdlib venv so
# non-uv tooling still understands it.
uv pip install --python "$HOME\.config\config-venv\Scripts\python.exe" -r "$HOME\.config\requirements.txt"

# --- Git submodules: ws (workspace manager), parlai (AI chat history search) --
# Both are plain git submodules pinned to a specific commit in .gitmodules;
# this one call inits/clones every submodule the repo declares.
git -C "$HOME\.config" submodule update --init --recursive

# --- Standalone CLI tools (isolated envs, not in config-venv) ------------------
# End-user CLIs rather than libraries our scripts import, so they get their
# own isolated environment via `uv tool` (the pipx model) instead of
# config-venv, where their pins would fight our scripts' pins.
uv tool install --quiet subliminal   # movie-subs: subtitle fetching

# parlai: the `parlai` CLI backing agents/skills/parlai (AI chat history
# search). Editable install of the submodule checkout above.
uv tool install --quiet --editable "$HOME\.config\parlai"

# ws: workspace manager. `ws init` symlinks it into a PATH location and seeds
# config.json. Idempotent.
if (Test-Path "$HOME\.config\ws\ws") {
    & "$HOME\.config\ws\ws" init
}

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

# Agent harness wiring (Claude Code + Codex).
#
# All symlinking lives in agents/link.ps1 (this platform's port of
# agents/link.sh — PowerShell can't run link.sh directly) so there is exactly
# one place per platform that knows the layout. Idempotent, refuses to
# clobber real files, handles the shared-vs-per-harness split:
#   agents\{skills,commands,memory,personas}  -> shared by every harness
#   agents\harness\<name>\                    -> that harness only
& "$HOME\.config\agents\link.ps1"

# sync-docs
if (Test-Path "$scriptsTarget\sync-docs") {
    & "$scriptsTarget\sync-docs"
}

# Run per-skill setup scripts (skills own anything beyond pip, e.g. playwright
# browsers). These are bash scripts; Git.Git (installed above) bundles Git
# Bash, so this doesn't need WSL, which isn't usable until the reboot this
# script triggers anyway.
$gitBash = "$env:ProgramFiles\Git\bin\bash.exe"
if (Test-Path $gitBash) {
    Write-Output "Running per-skill setup scripts..."
    Get-ChildItem -Path "$HOME\.config\agents\skills\*\scripts\setup.sh" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Output "  -> $($_.FullName)"
        & $gitBash $_.FullName
    }
} else {
    Write-Warning "Git Bash not found at $gitBash -- skipping per-skill setup.sh scripts."
}

# Verify the result: every CLI in scripts/ exposes a `smoke` self-check, and
# `doctor` runs all of them. It's a bash script — run it via Git Bash, same
# reasoning as the per-skill loop above. Non-fatal: a single broken tool
# shouldn't abort the rest of setup.
if (Test-Path $gitBash) {
    & $gitBash "$HOME\.config\scripts\doctor"
}

# Claude Code MCP servers — source of truth is
# ~/.config/agents/harness/claude/mcp-servers.json. ~/.claude.json holds
# mutable session state (OAuth, counters, project history) so it isn't
# tracked; register each server at user scope via the CLI instead. Native
# PowerShell JSON handling here rather than shelling out to jq, since macOS/
# Linux already cover the jq-based version and maintaining both here would be
# redundant.
$mcpConfigPath = "$HOME\.config\agents\harness\claude\mcp-servers.json"
if ((Get-Command claude -ErrorAction SilentlyContinue) -and (Test-Path $mcpConfigPath)) {
    Write-Output "Syncing Claude Code MCP servers from mcp-servers.json..."
    $mcpConfig = Get-Content $mcpConfigPath -Raw | ConvertFrom-Json
    foreach ($name in $mcpConfig.PSObject.Properties.Name) {
        $cfg = $mcpConfig.$name | ConvertTo-Json -Compress -Depth 10
        claude mcp remove $name -s user 2>$null | Out-Null
        claude mcp add-json $name $cfg -s user | Out-Null
        Write-Output "  + $name"
    }
}

# PowerShell profile — oh-my-posh + PSReadLine
Write-Output "Configuring PowerShell profile..."
New-Item -Path $PROFILE -Type File -Force | Out-Null
$profileContent = @'
oh-my-posh init pwsh | Invoke-Expression
Import-Module PSReadLine
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -PredictionViewStyle ListView

# --- Node version management (fnm) --------------------------------------------
if (Get-Command fnm -ErrorAction SilentlyContinue) {
    fnm env --use-on-cd --shell power-shell | Out-String | Invoke-Expression
}
'@
Set-Content -Path $PROFILE -Value $profileContent

# PSReadLine
Install-Module -Name PSReadLine -Force -SkipPublisherCheck -AllowClobber

# Default browser prompt
Start-Process "ms-settings:defaultapps"

# Verify
Write-Output ""
Write-Output "Verifying installation..."
foreach ($cmd in @('node', 'python', 'nvim', 'gh', 'claude', 'fastfetch', 'uv', 'fnm', 'jq')) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Write-Output "  ✓ $cmd"
    } else {
        Write-Output "  ✗ $cmd (not in PATH — open a new shell)"
    }
}

# git-crypt: warn if the encrypted files are still locked. Nothing here can
# unlock them -- that needs the symmetric key, which by design isn't in the
# repo. Until then .env, agents/memory/**, and the monarch-money prefs are
# ciphertext: API tokens stay unset and agents can't read their memories.
# -AsByteStream needs PowerShell 6+ (Core) -- Microsoft.PowerShell is in the
# winget list above but this script itself may still be running under
# legacy Windows PowerShell 5.1, so fall back to -Encoding Byte there.
$envPath = "$HOME\.config\.env"
if (Test-Path $envPath) {
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $envHead = Get-Content $envPath -AsByteStream -TotalCount 10 -ErrorAction SilentlyContinue
    } else {
        $envHead = Get-Content $envPath -Encoding Byte -TotalCount 10 -ErrorAction SilentlyContinue
    }
    if ($envHead -and ([System.Text.Encoding]::ASCII.GetString($envHead)).Contains("GITCRYPT")) {
        Write-Output ""
        Write-Output "[locked] ~/.config is git-crypt locked -- run 'cd ~\.config; git-crypt unlock \path\to\key'"
        Write-Output "         to decrypt .env (API tokens) and agents/memory/."
    }
}

Write-Output ""
Write-Output "Windows setup complete! Reboot to finish WSL setup."

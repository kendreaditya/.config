# setup-windows.ps1

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Warning "Please run this script as Administrator!"
    exit
}

# Check if winget is installed
if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Output "Installing winget..."
    # Direct users to install winget from Microsoft Store
    Start-Process "ms-windows-store://pdp/?ProductId=9nblggh4nns1&mode=mini"
    Write-Output "Please install App Installer from the Microsoft Store and run this script again."
    exit
}

Write-Output "Installing packages and applications..."

# Install base packages
Write-Output "Installing base packages..."
winget install Microsoft.VisualStudioCode
winget install Google.Chrome
winget install OpenJS.NodeJS
winget install Python.Python.3.10
winget install Git.Git
winget install cURL.cURL
winget install GitHub.cli
winget install Neovim.Neovim
winget install JanDeDobbeleer.OhMyPosh -s winget

# Install additional developer tools
winget install --id ImageMagick.ImageMagick
winget install --id Kitware.CMake
winget install --id GnuWin32.Make
winget install --id LLVM.LLVM
winget install --id GnuWin32.Wget
winget install --id junegunn.fzf
winget install --id yt-dlp.yt-dlp
winget install --id mikefarah.yq
winget install --id tmux.tmux
winget install --id atuinsh.atuin
winget install --id vim.vim
winget install --id dylanaraps.neofetch
winget install --id Microsoft.PowerShell
winget install --id JanDeDobbeleer.OhMyPosh

# Install applications
winget install --id Doist.Todoist
winget install --id Zoom.Zoom
winget install --id bruno.bruno
winget install --id ollama.ollama
winget install --id Microsoft.WindowsTerminal
winget install --id Warp.Warp
winget install --id Cloudflare.Warp
winget install --id Oven-sh.Bun
winget install --id DenoLand.Deno


# Install Windows-specific packages
Write-Output "Installing Windows-specific packages..."
# WSL
Write-Output "Enabling Windows Subsystem for Linux..."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

# PowerToys
Write-Output "Installing Microsoft PowerToys..."
winget install Microsoft.PowerToys -s winget

# Ubuntu for WSL
Write-Output "Installing Ubuntu for WSL..."
wsl --install -d Ubuntu

Write-Output "Configuring Windows settings..."

# Install and configure Oh-My-Posh
New-Item -Path $PROFILE -Type File -Force
Add-Content -Path $PROFILE -Value 'oh-my-posh init pwsh | Invoke-Expression'

# Configure PowerShell to use PSReadLine with better history and auto-completion
Write-Output "Installing PSReadLine module..."
Install-Module -Name PSReadLine -Force -SkipPublisherCheck
Add-Content -Path $PROFILE -Value 'Import-Module PSReadLine'
Add-Content -Path $PROFILE -Value 'Set-PSReadLineOption -PredictionSource History'
Add-Content -Path $PROFILE -Value 'Set-PSReadLineOption -PredictionViewStyle ListView'

# Set Chrome as default browser
Write-Output "Setting Chrome as default browser..."
Start-Process "ms-settings:defaultapps"
Write-Output "Please set Chrome as your default browser in the Settings window that just opened."

Write-Output "Windows setup complete! Some settings may require a system restart to take full effect."
Write-Output "Note: Ubuntu for WSL may need additional setup after installation."

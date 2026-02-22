#!/bin/bash
# setup-linux.sh

# Install package manager if not already installed (apt for Debian/Ubuntu)
if ! command -v apt &> /dev/null; then
  echo "This script is designed for Debian/Ubuntu-based distributions."
  echo "Please adapt it for your distribution."
  exit 1
fi

echo "Updating package repositories..."
sudo apt update && sudo apt upgrade -y

echo "Installing packages and applications..."

# Install packages
sudo apt install -y imagemagick
sudo apt install -y cmake
sudo apt install -y gcc g++
sudo apt install -y ffmpeg
sudo apt install -y curl wget
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y fzf
sudo apt install -y neovim && curl -fLo ~/.local/share/nvim/site/autoload/plug.vim --create-dirs \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
sudo apt install -y vim
sudo apt install -y tmux
sudo apt install -y neofetch
sudo apt install -y git
sudo apt install -y zsh

# Install GitHub CLI
if ! command -v gh &> /dev/null; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt update && sudo apt install -y gh
fi

# Install yt-dlp
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp

# Install yq
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod a+x /usr/local/bin/yq

# Install atuin
if ! command -v atuin &> /dev/null; then
  bash <(curl https://raw.githubusercontent.com/atuinsh/atuin/main/install.sh)
fi

# Install Node.js if not already installed
if ! command -v node &>/dev/null; then
  echo "Installing Node.js..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt install -y nodejs
fi

# Install Bun
if ! command -v bun &>/dev/null; then
  curl -fsSL https://bun.sh/install | bash
fi

# Install Deno
if ! command -v deno &>/dev/null; then
  curl -fsSL https://deno.land/install.sh | sh
fi

# Install Cloudflare WARP
if ! command -v warp-cli &>/dev/null; then
  curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
  sudo apt update
  sudo apt install -y cloudflare-warp
fi

# Install snap if not available
if ! command -v snap &> /dev/null; then
  sudo apt install -y snapd
  sudo systemctl enable --now snapd.socket
fi

# Install applications
sudo snap install code --classic
sudo snap install todoist
sudo snap install protonvpn-community

# Install Zoom
sudo snap install zoom-client

# Install Chrome
if ! command -v google-chrome &> /dev/null; then
  wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
  echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
  sudo apt update
  sudo apt install -y google-chrome-stable
fi

# Install Ollama
if ! command -v ollama &> /dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Install i3 window manager (alternative to Amethyst)
sudo apt install -y i3

# Install Ulauncher (alternative to Raycast)
sudo add-apt-repository ppa:agornostal/ulauncher -y
sudo apt update
sudo apt install -y ulauncher

# Set system defaults
echo "Configuring Linux settings..."

# Set up Oh My Zsh
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "Setting up Oh My Zsh..."
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
fi

# Create .config Python venv and install dependencies
echo "Setting up .config Python venv..."
python3 -m venv ~/.config/config-venv
~/.config/config-venv/bin/pip install --upgrade pip
~/.config/config-venv/bin/pip install -r ~/.config/requirements.txt

# Symlink scripts to PATH
mkdir -p ~/.local/bin
for script in ~/.config/scripts/*; do
  if [ -f "$script" ] && [ -x "$script" ]; then
    scriptname=$(basename "$script")
    ln -sf "$script" ~/.local/bin/"$scriptname"
  fi
done

# Set Zsh as default shell
if [ "$SHELL" != "$(which zsh)" ]; then
  echo "Setting Zsh as default shell..."
  chsh -s $(which zsh)
fi

# Configure GNOME settings if running GNOME
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ]; then
  # Disable automatic spelling correction (if available)
  gsettings set org.gnome.desktop.interface enable-spell-checking false

  # Dock settings (GNOME dash-to-dock extension)
  if gsettings list-schemas | grep -q "org.gnome.shell.extensions.dash-to-dock"; then
    gsettings set org.gnome.shell.extensions.dash-to-dock dock-position BOTTOM
    gsettings set org.gnome.shell.extensions.dash-to-dock dash-max-icon-size 36
    gsettings set org.gnome.shell.extensions.dash-to-dock autohide true
    gsettings set org.gnome.shell.extensions.dash-to-dock autohide-in-fullscreen true
  fi

  # File manager settings
  gsettings set org.gnome.nautilus.preferences show-hidden-files true
  gsettings set org.gnome.nautilus.preferences default-folder-viewer 'list-view'

  # Keyboard settings
  gsettings set org.gnome.desktop.peripherals.keyboard repeat-interval 30
  gsettings set org.gnome.desktop.peripherals.keyboard delay 250
fi

# Configure default browser
if command -v google-chrome &> /dev/null; then
  echo "Setting Chrome as default browser..."
  xdg-settings set default-web-browser google-chrome.desktop
fi

# Create custom keyboard shortcuts (for GNOME)
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ]; then
  # Reset shortcuts
  gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "[]"

  # Add Alt-Tab alternative shortcut
  gsettings set org.gnome.desktop.wm.keybindings switch-applications "['<Alt>Tab']"
  gsettings set org.gnome.desktop.wm.keybindings switch-windows "['<Super>Tab']"
fi

echo "Restarting services to apply changes..."
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ]; then
  # Restart GNOME Shell if possible (only works in X11 sessions)
  if [ "$XDG_SESSION_TYPE" = "x11" ]; then
    echo "Restarting GNOME Shell..."
    busctl --user call org.gnome.Shell /org/gnome/Shell org.gnome.Shell Eval s 'Meta.restart("Restarting…")'
  else
    echo "Please log out and back in for all changes to take effect."
  fi
fi

echo "Linux setup complete!"

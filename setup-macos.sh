#!/bin/bash
# setup-macos.sh

# Script description: Setup script for macOS development environment
# Author: Aditya Kendre (aditya@semant.co)

# Check if ZDOTDIR is set in .zshenv
echo "Checking zsh configuration..."
if [ -f "$HOME/.zshenv" ]; then
  if ! grep -q "ZDOTDIR=\$HOME/.config" "$HOME/.zshenv"; then
    echo "Setting ZDOTDIR in .zshenv..."
    echo 'export ZDOTDIR=$HOME/.config' >> "$HOME/.zshenv"
    echo "ZDOTDIR has been set to \$HOME/.config"
  else
    echo "ZDOTDIR is already set in .zshenv"
  fi
else
  echo "Creating .zshenv and setting ZDOTDIR..."
  echo 'export ZDOTDIR=$HOME/.config' > "$HOME/.zshenv"
  echo ".zshenv created with ZDOTDIR set to \$HOME/.config"
fi

# Suppress login(1)'s "Last login: ..." banner at the top of every shell.
# Must live in $HOME — login(1) predates and ignores ZDOTDIR, so a copy in
# ~/.config would have no effect. Empty file; its existence is the signal.
if [ ! -f "$HOME/.hushlogin" ]; then
  echo "Creating .hushlogin to silence the 'Last login' banner..."
  touch "$HOME/.hushlogin"
else
  echo ".hushlogin already present"
fi

# Install Homebrew if not already installed
if ! command -v brew &> /dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Ensure brew is in PATH for this script (works on fresh installs and re-runs)
[ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"

echo "Installing packages and applications..."

# Skip the implicit `brew update` that otherwise runs before each install call below.
# Doing it once per invocation would re-fetch the formula API several times for no gain.
export HOMEBREW_NO_AUTO_UPDATE=1

# Formulae are installed in two calls: homebrew/core first, third-party taps second.
# Homebrew 6.0 requires explicit trust for non-official taps, and it refuses the
# ENTIRE `brew install` invocation if any one argument comes from an untrusted tap.
# Keeping them in a single call meant three third-party formulae blocked all 30+
# core ones, so nothing installed at all.

# 1. homebrew/core — no trust needed.
#
# Removed by request, with the reasons worth keeping:
#   gemini-cli  deprecated 2026-06-18 (:unsupported), disabled 2026-12-18, after
#               which `brew install` errors out and takes this whole batch with it.
#               Homebrew points to the antigravity-cli cask, but that's a different
#               CLI with a different invocation, so claude/skills/gemini/ (which
#               shells out to `gemini -p`) would need rewriting first.
#   bun         only consumer was gstack, also removed below.
#   ocrmypdf    pulled in ghostscript + tesseract; all three went together.
#   tesseract   OCR engine, only used via ocrmypdf.
#   graphviz    pulled in ~12 X11/cairo/glib deps for diagram rendering.
#   himalaya    TUI email client, unused.
#   deno        NOT removed: it is a *required* dependency of yt-dlp (which
#               claude/skills/clean/scripts/cleansubs.py uses), so brew reinstalls
#               it automatically. Dropping it from this line changes nothing.
#   duti        needed by .macos/defaults.sh to set the default browser. The old
#               `defaults write ... LSHandlers -array-add` approach silently never
#               worked, because lsd owns that array and overwrites it.
brew install mas imagemagick cmake gcc ffmpeg gh wget curl python@3.12 \
  fzf neovim yt-dlp yq jq tmux atuin vim fastfetch node git git-crypt zsh ripgrep tree rclone \
  fswatch ncdu duti uv fnm

# 2. Third-party taps — trust the specific formulae we use rather than the whole
# tap, so trust doesn't silently extend to every formula these taps add later.
# Trust is persistent (~/.homebrew/trust.json), so this is a no-op on re-runs.
# gogcli and wacli migrated out of steipete/tap into openclaw/tap.
brew tap steipete/tap
brew tap openclaw/tap
brew tap assemblyai/assemblyai
brew trust --formula openclaw/tap/gogcli openclaw/tap/wacli steipete/tap/imsg \
  assemblyai/assemblyai/assemblyai
brew install openclaw/tap/gogcli steipete/tap/imsg assemblyai

# wacli: previously fetched by hand because steipete/tap pinned a stale v0.2.0 that
# WhatsApp rejected as "client outdated". The formula moved to openclaw/tap and now
# tracks current releases (0.16.0+), so brew handles it. The old manual path also
# broke whenever the unauthenticated GitHub API hit its rate limit: WACLI_TAG came
# back empty, curl downloaded an error page, and tar failed on it.
brew install openclaw/tap/wacli

# Install global npm CLIs (yarn removed by request — pnpm covers the same ground)
npm install -g wrangler vercel pnpm typescript tailwindcss eslint

# Install vim-plug for neovim
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

# Install the plugins declared in nvim/plug.vim. --sync is required: without it
# PlugInstall returns before its git jobs finish, so +qa exits mid-clone and the
# plugin dirs are left empty or half-cloned. Idempotent — a no-op re-run is ~0.4s.
# Runs after node so plugins with build steps can find their toolchains.
if command -v nvim &>/dev/null; then
  echo "Installing neovim plugins..."
  nvim --headless +'PlugInstall --sync' +qa
fi

# Install all casks in one call (--force handles apps already installed outside brew)
# NOTE: tomatobar handled separately below — we install from a private fork
# (kendreaditya/TomatoBar) that ships our URL scheme extensions on top of upstream.
#
# --appdir: install app bundles under ~/Applications. Where the user isn't an admin
# (managed/corp laptops) /Applications isn't writable and a plain `brew install
# --cask` fails. ~/Applications is a standard macOS location that Spotlight and
# Launchpad index, and needs no sudo. .pkg-based casks ignore --appdir and still
# elevate through the installer.
#
# Excluded from the install call below, but recorded here on purpose so the intent
# survives and they're easy to re-enable per machine:
#
#   CASKS_SKIP_DX="claude-code codex"
#     Both CLIs are installed and kept current by dx (`dx module install claude`),
#     which also owns their gateway config. The casks link binaries into the brew
#     prefix that shadow dx's copy, causing version drift (brew 2.1.220 vs dx
#     2.1.226). Install these only on a machine without dx.
#
#   Blocked by the corporate network — chatgpt and cursor.
#     chatgpt replaces codex-app, which was discontinued upstream and is deprecated
#     in Homebrew (disabled 2027-07-12). chatgpt itself is current, but it downloads
#     from persistent.oaistatic.com, which some corporate networks block. The block
#     page fails checksum verification and, because casks install as one batch,
#     takes every other cask down with it. Re-enable on an unfiltered network.
#     cursor is blocked the same way: downloads.cursor.com is denied by some
#     corporate Cloudflare Gateway deployments, which return a small HTML block
#     page in place of the .zip. On a managed network this needs an IT ticket to
#     unblock, and an LLM tool may additionally need software-onboarding approval
#     before use with company data. (Machine-specific rule IDs and internal ticket
#     URLs deliberately omitted — see the device branch for those.)
brew install --cask --force --appdir="$HOME/Applications" \
  raycast todoist zoom alt-tab bruno \
  hiddenbar thaw caffeine blackhole-2ch ollama \
  visual-studio-code google-chrome warp ghostty logseq obsidian \
  claude whatsapp \
  protonvpn cloudflare-warp iina windows-app

# Caffeine's cask can be blocked by Gatekeeper quarantine on first launch. On
# non-admin machines, launching ~/Applications/Caffeine.app has also been observed
# to remove that bundle while trying to settle under /Applications. Keep a stable
# user-local launch copy with a distinct bundle name.
CAFFEINE_APP="$HOME/Applications/Caffeine.app"
CAFFEINE_LOCAL_APP="$HOME/Applications/Caffeine Local.app"
if [ ! -d "$CAFFEINE_APP" ] && [ ! -d "$CAFFEINE_LOCAL_APP" ]; then
  brew reinstall --cask --appdir="$HOME/Applications" caffeine
fi
if [ -d "$CAFFEINE_APP" ]; then
  if pgrep -f "$CAFFEINE_LOCAL_APP/Contents/MacOS/Caffeine" >/dev/null; then
    echo "Caffeine Local.app is running; leaving existing launch copy in place."
  else
    ditto "$CAFFEINE_APP" "$CAFFEINE_LOCAL_APP"
  fi
fi
for app in "$CAFFEINE_APP" "$CAFFEINE_LOCAL_APP" "/Applications/Caffeine.app" "$(brew --prefix)/Caskroom/caffeine"/*/Caffeine.app; do
  [ -e "$app" ] || continue
  find "$app" -exec xattr -d com.apple.quarantine {} + 2>/dev/null || true
done

# Warp: same Gatekeeper/non-admin failure as Caffeine above, verified 2026-08-13.
# The brew-installed ~/Applications/Warp.app sits fine at rest but DELETES ITSELF
# on launch: it tries to relocate into /Applications, which isn't writable for a
# non-admin (`staff`) account, and the failed move takes the source bundle with it.
# The download is legitimate — sha256 matches formulae.brew.sh, signed by Denver
# Technologies (2BBY89MBSN), and `spctl` reports "accepted, Notarized Developer ID"
# — so this is a relocation bug, not a signature or malware problem. Fix is the
# Caffeine pattern: keep a dequarantined launch copy under a distinct bundle name
# that Warp won't try to relocate, and launch that one instead of Warp.app.
WARP_APP="$HOME/Applications/Warp.app"
WARP_LOCAL_APP="$HOME/Applications/Warp Local.app"
if [ -d "$WARP_APP" ]; then
  # Warp's binary is Contents/MacOS/stable, not .../Warp — match the bundle path.
  # ditto would clobber a running bundle, so only refresh when it isn't running.
  if pgrep -f "Warp Local\.app" >/dev/null 2>&1; then
    echo "Warp Local.app is running; leaving existing launch copy in place."
  elif [ ! -d "$WARP_LOCAL_APP" ] || [ "$WARP_APP" -nt "$WARP_LOCAL_APP" ]; then
    ditto "$WARP_APP" "$WARP_LOCAL_APP"
  else
    echo "Warp Local.app is up to date."
  fi
fi
for app in "$WARP_APP" "$WARP_LOCAL_APP"; do
  [ -e "$app" ] || continue
  find "$app" -exec xattr -d com.apple.quarantine {} + 2>/dev/null || true
done

# TomatoBar: install from kendreaditya/TomatoBar (private fork of ivoronin/TomatoBar).
# Adds the tomatobar://start, ://stop, ://skipRest, ://startStop URL schemes and
# ?duration= overrides on top of upstream, so a timer can be driven from a hotkey or
# script. Builds are ad-hoc signed and tagged 'prerelease' (rolling) — the
# sync-upstream workflow rebases our patches weekly.
# (An earlier comment here credited ~/.config/raycast/scripts/tom.sh as the consumer.
# No such file exists or is tracked, and nothing in raycast/ references the scheme —
# the Raycast script it described was never committed. Bundle verified to register
# tomatobar:// regardless.)
# Requires: gh (Homebrew) authed on github.com with `repo` scope.
#
# Three things this used to get wrong:
#  1. It installed into /Applications, which isn't writable for a non-admin user on a
#     managed laptop — the same reason every cask above uses --appdir=~/Applications.
#     The unzip failed and the sudo xattr then operated on a nonexistent path.
#  2. `gh auth status` exits 0 if ANY host is authed, so on a machine logged into a
#     GitHub Enterprise host but not github.com the guard passed and the download
#     404'd. Both the check and the download are now pinned to github.com, and
#     --repo is host-qualified so it can't resolve against the GHE remote.
#  3. `xattr -r` no longer exists on macOS 26 (only -s/-l/-z/-p/-w/-d/-c), so the
#     recursive clear errored out. Use the same `find -exec xattr -d … +` form as the
#     Caffeine block above. No sudo needed once the app is user-local.
TB_APP="$HOME/Applications/TomatoBar.app"
if command -v gh &>/dev/null && GH_HOST=github.com gh auth status --hostname github.com &>/dev/null; then
  echo "Fetching latest TomatoBar from kendreaditya/TomatoBar..."
  TB_TMP=$(mktemp -d)
  if GH_HOST=github.com gh release download prerelease \
       --repo github.com/kendreaditya/TomatoBar \
       --pattern 'TomatoBar-*.zip' --dir "$TB_TMP" --clobber; then
    rm -rf "$TB_APP"
    unzip -q -o "$TB_TMP"/TomatoBar-*.zip -d "$HOME/Applications/"
    find "$TB_APP" -exec xattr -d com.apple.quarantine {} + 2>/dev/null || true
    if [ -d "$TB_APP" ]; then
      echo "  ✓ TomatoBar installed to $TB_APP"
    else
      echo "  ✗ TomatoBar unzip produced no app bundle"
    fi
  else
    echo "  ✗ TomatoBar download failed (is the github.com token missing 'repo' scope?)"
  fi
  rm -rf "$TB_TMP"
else
  echo "WARN: gh not installed or not authed to github.com — skipping TomatoBar install."
  echo "      Run 'brew install gh && gh auth login --hostname github.com' then re-run."
fi

# Install Mac App Store apps (requires App Store sign-in)
mas install 1475387142  # Tailscale

# Install oh-my-zsh
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  echo "Installing Oh My Zsh..."
  sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
  echo "Oh My Zsh installed successfully!"
else
  echo "Oh My Zsh is already installed, skipping..."
fi

# Create .config Python venv and install dependencies.
# Resolve python3.12 rather than hardcoding /opt/homebrew/bin: the Homebrew prefix
# differs on Intel (/usr/local) and a user-prefix install, and `brew --prefix` is
# authoritative for whichever this machine has. Skip creation if the venv already
# exists so a re-run doesn't discard installed packages.
echo "Setting up .config Python venv..."
PY312="$(brew --prefix python@3.12 2>/dev/null)/bin/python3.12"
[ -x "$PY312" ] || PY312="$(command -v python3.12 || command -v python3)"
if [ ! -x ~/.config/config-venv/bin/python3 ]; then
  "$PY312" -m venv ~/.config/config-venv
fi
# Dependencies are installed with uv (10-100x faster than pip, and it resolves
# the whole set at once instead of sequentially). uv is installed via brew above.
# The venv itself stays a plain stdlib venv so non-uv tooling still understands it.
uv pip install --python ~/.config/config-venv/bin/python3 -r ~/.config/requirements.txt

# --- Standalone CLI tools (isolated envs, not in config-venv) ------------------
# These are end-user CLIs rather than libraries imported by our scripts, so they
# get their own isolated environment via `uv tool` (the pipx model). Installing
# them into config-venv would let their pins fight our scripts' pins.
uv tool install --quiet subliminal || true   # movie-subs: subtitle fetching

# --- External repos that skills depend on -------------------------------------
# parlai: the `parlai` CLI backing claude/skills/parlai (AI chat history search).
# SKILL.md expects it at ~/workspace/parlai and on PATH. Editable install so a
# `git pull` there takes effect without reinstalling.
if [ ! -d ~/workspace/parlai ]; then
  git clone https://github.com/kendreaditya/parlai.git ~/workspace/parlai
fi
uv tool install --quiet --editable ~/workspace/parlai || true

# ws: workspace manager. Lives as a git submodule at ~/.config/ws; `ws init`
# symlinks it into ~/.local/bin and seeds config.json. Idempotent.
git -C ~/.config submodule update --init --recursive
[ -x ~/.config/ws/ws ] && ~/.config/ws/ws init || true

# gstack removed by request. It cloned github.com/garrytan/gstack into
# claude/skills/gstack (1.1GB with node_modules) and its ./setup symlinked ~54
# skills back out as gstack-* dirs. It was also the only consumer of bun, so both
# went together. To restore: re-add bun to the brew line above, then
#   git clone --depth 1 https://github.com/garrytan/gstack.git \
#     ~/.config/agents/skills/gstack && (cd $_ && ./setup)
# Note claude/skills/gstack/ is gitignored, so nothing here tracks it.

# Run per-skill setup scripts (skills own anything beyond pip, e.g. playwright browsers)
echo "Running per-skill setup scripts..."
for s in ~/.config/agents/skills/*/scripts/setup.sh; do
  [ -f "$s" ] || continue
  echo "  → $s"
  bash "$s"
done

# Create workspace directory
mkdir -p ~/workspace

# Install licensed fonts from assets/fonts into ~/Library/Fonts
if [ -d ~/.config/assets/fonts ]; then
  echo "Installing fonts..."
  mkdir -p ~/Library/Fonts
  for font in ~/.config/assets/fonts/*.{otf,ttf}; do
    [ -f "$font" ] && cp -f "$font" ~/Library/Fonts/
  done
fi

# Symlink scripts to PATH
mkdir -p ~/.local/bin
for script in ~/.config/scripts/*; do
  if [ -f "$script" ] && [ -x "$script" ]; then
    scriptname=$(basename "$script")
    ln -sf "$script" ~/.local/bin/"$scriptname"
  fi
done

# LaunchAgents (symlinked from ~/.config so edits land in one place)
mkdir -p ~/Library/LaunchAgents
for plist in ~/.config/scripts/*/*.plist; do
  [ -f "$plist" ] || continue
  label=$(basename "$plist")
  target="$HOME/Library/LaunchAgents/$label"
  ln -sfn "$plist" "$target"
  launchctl unload "$target" 2>/dev/null || true
  launchctl load "$target"
done

# Agent harness wiring (Claude Code + Codex).
#
# All symlinking now lives in agents/link.sh so there is exactly one place that
# knows the layout. It is idempotent, refuses to clobber real files, and handles
# the shared-vs-per-harness split:
#   agents/{skills,commands,memory,personas}  -> shared by every harness
#   agents/harness/<name>/                    -> that harness only
#
# Note ~/.claude/agents points at agents/personas (Claude calls them "agents",
# Codex uses .toml files kept in harness/codex/agents), and Codex user skills go
# to ~/.codex/skills/user so its generated .system dir is preserved.
~/.config/agents/link.sh

# Verify the result: every CLI in scripts/ exposes a `smoke` self-check, and
# `doctor` runs all of them. Non-fatal here so a single broken tool does not
# abort setup, but it surfaces breakage immediately instead of weeks later.
~/.config/scripts/doctor || true

# Zap terminal — config lives in ~/.config/zap, exposed at the hardcoded ~/.zap.
#
# Zap has no XDG support for its own settings: the only path strings in the binary
# are ".zap" and ".zap/remote-server", both built from $HOME, and there is no
# config-path CLI flag or env var override. So the directory has to be symlinked.
#
# Link the DIRECTORY, not settings.toml alone, for two reasons:
#   1. Zap hot-reloads settings.toml via a file watcher. Watchers commonly break on
#      symlinked *files*, because a save-by-rename swaps the inode out from under the
#      watcher and it silently stops firing. Linking the dir keeps a real file inside.
#   2. Zap also writes ~/.zap/remote-server (a Linux binary it installs on remote hosts
#      over SSH). Linking only settings.toml would scatter that back into a stray ~/.zap.
# remote-server and other runtime state are gitignored; see .gitignore.
mkdir -p ~/.config/zap
# Zap creates ~/.zap as a real dir on first run, which shadows the tracked config.
# Migrate any settings.toml it wrote there, then replace the dir — but only when
# empty after the move, so a real directory with other content is never discarded.
if [ -d ~/.zap ] && [ ! -L ~/.zap ]; then
  [ -f ~/.zap/settings.toml ] && [ ! -f ~/.config/zap/settings.toml ] && \
    mv ~/.zap/settings.toml ~/.config/zap/settings.toml
  rmdir ~/.zap 2>/dev/null || \
    echo "WARN: ~/.zap is a non-empty real directory — not replacing it; move its contents into ~/.config/zap by hand"
fi
[ -e ~/.zap ] || ln -sfn ~/.config/zap ~/.zap

# Claude Code MCP servers — source of truth is ~/.config/agents/harness/claude/mcp-servers.json.
# ~/.claude.json holds mutable session state (OAuth, counters, project history) so we
# don't track it; instead, register each server at user scope via the CLI.
if command -v claude &>/dev/null && [ -f ~/.config/agents/harness/claude/mcp-servers.json ]; then
  echo "Syncing Claude Code MCP servers from mcp-servers.json..."
  jq -r 'keys[]' ~/.config/agents/harness/claude/mcp-servers.json | while read -r name; do
    cfg=$(jq -c --arg n "$name" '.[$n]' ~/.config/agents/harness/claude/mcp-servers.json)
    claude mcp remove "$name" -s user 2>/dev/null || true
    claude mcp add-json "$name" "$cfg" -s user >/dev/null && echo "  ✓ $name"
  done
fi

# Download Claude Code docs locally (scripts symlinked above)
~/.local/bin/sync-docs || echo "Warning: sync-docs failed (may need 'requests' — install manually)"


# Apply macOS configuration
echo "Applying macOS settings..."
MACOS_DIR="$(dirname "$0")/.macos"
chmod +x "$MACOS_DIR"/*.sh
export MACOS_SETUP_RUNNING=1

bash "$MACOS_DIR/defaults.sh"
bash "$MACOS_DIR/dock.sh"
bash "$MACOS_DIR/finder.sh"
bash "$MACOS_DIR/sidebar.sh"
bash "$MACOS_DIR/power.sh"

# Restart affected services so the defaults above take effect. Loop instead of a
# single `killall Dock Finder SystemUIServer`: killall exits non-zero if ANY named
# process isn't running (e.g. SystemUIServer on some setups), and a failure here
# would leave settings like AppleShowAllFiles written but never applied, since
# Finder only reads them at launch.
echo "Restarting services to apply changes..."
for app in Dock Finder SystemUIServer; do
  killall "$app" 2>/dev/null || true
done

# Reclaim disk space from stale brew downloads
brew cleanup

# Clear pip download cache (packages already installed into venv)
pip3 cache purge

# Verify critical tools are available
echo ""
echo "Verifying installation..."
for cmd in brew node python3 nvim tmux gh claude; do
  if command -v "$cmd" &>/dev/null; then
    echo "  ✓ $cmd"
  else
    echo "  ✗ $cmd (not in PATH — open a new shell)"
  fi
done

# git-crypt: warn if the encrypted files are still locked. Nothing here can unlock
# them — that needs the symmetric key (or an authorised GPG key), which by design
# isn't in the repo. Until then .env, claude/memory/**, and the monarch-money prefs
# are ciphertext: API tokens stay unset and Claude can't read its memories.
if head -c 10 ~/.config/.env 2>/dev/null | grep -aq GITCRYPT; then
  echo ""
  echo "🔒 ~/.config is git-crypt locked — run 'cd ~/.config && git-crypt unlock /path/to/key'"
  echo "   to decrypt .env (API tokens) and claude/memory/."
fi

echo ""
echo "✅ macOS setup complete!"
echo "👉 Run 'exec zsh' or open a new terminal to pick up shell changes."
echo ""
echo "⚠️  Log out and back in (or reboot) for everything to take effect."
echo ""
echo "🔐 Privacy prompts (Full Disk Access, Accessibility, Automation) can't be scripted — macOS TCC is SIP-protected, so grant them per app on first launch, or ask IT for an MDM PPPC profile."

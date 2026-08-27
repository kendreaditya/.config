# agents/link.ps1 — wire this repo's agents/ tree into each harness's config
# directory, on Windows. PowerShell port of agents/link.sh: same layout, same
# idempotent/non-destructive semantics, kept in lockstep by hand since
# link.sh can't run natively under PowerShell.
#
# Layout:
#   agents/skills|commands|memory|personas   harness-agnostic, shared by all
#   agents/harness/<name>/...                per-harness config (settings, prompts)
#
# Shared content is symlinked into every harness; harness/<name>/ only into
# that harness. Idempotent — safe to re-run. Currently wires claude + codex.
#
# Creating a SymbolicLink on Windows normally requires Developer Mode or an
# elevated (Administrator) shell — setup-windows.ps1 already requires admin,
# so this inherits that.

param([switch]$DryRun)

$Repo = Split-Path -Parent $PSScriptRoot
$Agents = Join-Path $Repo "agents"

function Write-Log($msg) { Write-Output "  $msg" }
function Write-Warn2($msg) { Write-Warning "  $msg" }

function Link-Path($Target, $LinkPath) {
    if (!(Test-Path $Target)) {
        Write-Warn2 "missing target, skipped: $Target"
        return
    }
    $existing = Get-Item -Path $LinkPath -ErrorAction SilentlyContinue
    if ($existing -and $existing.LinkType -in @('SymbolicLink', 'Junction')) {
        # .Target can come back as a string or a single-element string[]
        # depending on PowerShell version — -contains handles both, -eq does
        # not (array -eq string is an unreliable elementwise comparison).
        if ($existing.Target -contains $Target) {
            Write-Log "ok       $LinkPath"
            return
        }
    } elseif ($existing) {
        # Exists as a real file/dir, not a symlink/junction — refuse to
        # clobber it, same rule as link.sh.
        Write-Warn2 "exists as real file/dir, NOT replacing: $LinkPath"
        Write-Warn2 "         move it aside and re-run to link $Target"
        return
    }
    if ($DryRun) {
        Write-Log "would    $LinkPath -> $Target"
        return
    }
    $parent = Split-Path -Parent $LinkPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if ($existing) { Remove-Item $LinkPath -Force -Recurse }
    $itemType = if ((Get-Item $Target) -is [System.IO.DirectoryInfo]) { 'Junction' } else { 'SymbolicLink' }
    # Junction (not SymbolicLink) for directories: junctions don't require
    # Developer Mode/admin on Windows, so shared dirs still link even if this
    # script is somehow run without elevation.
    New-Item -ItemType $itemType -Path $LinkPath -Target $Target -ErrorAction SilentlyContinue | Out-Null
    Write-Log "linked   $LinkPath -> $Target"
}

# ---------------------------------------------------------------- claude code
Write-Output "claude:"
$ClaudeDir = "$HOME\.claude"
Link-Path "$Agents\skills"                       "$ClaudeDir\skills"
Link-Path "$Agents\commands"                     "$ClaudeDir\commands"
Link-Path "$Agents\memory"                       "$ClaudeDir\memory"
Link-Path "$Agents\personas"                     "$ClaudeDir\agents"
Link-Path "$Agents\harness\claude\settings.json" "$ClaudeDir\settings.json"
Link-Path "$Agents\harness\claude\CLAUDE.md"     "$ClaudeDir\CLAUDE.md"
Link-Path "$Agents\harness\claude\output-styles" "$ClaudeDir\output-styles"

# ---------------------------------------------------------------------- codex
# Codex namespaces user skills under ~/.codex/skills/user (its own generated
# content lives in ~/.codex/skills/.system, so do NOT link the parent).
Write-Output "codex:"
$CodexDir = "$HOME\.codex"
Link-Path "$Agents\skills"                    "$CodexDir\skills\user"
Link-Path "$Agents\commands"                  "$CodexDir\prompts"
Link-Path "$Agents\memory"                    "$CodexDir\memory"
Link-Path "$Agents\harness\codex\AGENTS.md"   "$CodexDir\AGENTS.md"
Link-Path "$Agents\harness\codex\agents"      "$CodexDir\agents"

# NOTE: ~/.codex/config.toml and ~/.claude.json are intentionally NOT linked —
# both mix MCP config with mutable session state. Same reasoning as link.sh.

Write-Output ""
Write-Output "done. re-run anytime; nothing is destructive to real files."

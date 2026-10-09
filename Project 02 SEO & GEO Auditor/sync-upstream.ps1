<#
.SYNOPSIS
    Sync & Inspect upstream changes from AgriciDaniel/claude-seo for Antigravity Agent adaptation.

.DESCRIPTION
    Pulls upstream changes into upstream-claude-seo/ without modifying Antigravity files directly.
    Generates an Agent-Ready Change Manifest (UPSTREAM_CHANGES.md and data/upstream_manifest.json)
    so an AI Agent can review and port the changes adhering strictly to Windows UTF-8, UV execution,
    and Antigravity skill architecture.

.PARAMETER Pull
    Pull latest changes from upstream git repository.

.PARAMETER Status
    Show summary of differences between upstream and local Antigravity workspace.

.PARAMETER Manifest
    Generate UPSTREAM_CHANGES.md and data/upstream_manifest.json for AI Agent adaptation.

.PARAMETER Diff
    Show unified diff of a specific relative path (e.g. scripts/google_auth.py).

.EXAMPLE
    .\sync-upstream.ps1 -Status
    .\sync-upstream.ps1 -Pull
    .\sync-upstream.ps1 -Manifest
    .\sync-upstream.ps1 -Diff "scripts/google_auth.py"
#>

[CmdletBinding()]
param(
    [switch]$Pull,
    [switch]$Status,
    [switch]$Manifest,
    [string]$Diff
)

$env:PYTHONUTF8 = "1"
$scriptPath = Join-Path $PSScriptRoot "scripts\sync_upstream.py"

$argsList = @()
if ($Pull) { $argsList += "--pull" }
if ($Status) { $argsList += "--status" }
if ($Manifest) { $argsList += "--manifest" }
if ($Diff) { $argsList += "--diff"; $argsList += $Diff }

if ($argsList.Count -eq 0) {
    # Default to manifest generation
    $argsList += "--manifest"
}

uv run python $scriptPath @argsList

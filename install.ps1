<#
.SYNOPSIS
  OptimizeIT installer (Windows PowerShell 5.1+ / PowerShell 7+)

.EXAMPLE
  .\install.ps1                              # all agents, user level
.EXAMPLE
  .\install.ps1 -Target cursor               # Cursor only, user level
.EXAMPLE
  .\install.ps1 -Target claude -Project .    # Claude Code only, this project
#>
param(
    [ValidateSet('claude', 'codex', 'cursor', 'gemini', 'all')]
    [string]$Target = 'all',
    [string]$Project = ''
)

$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'skills\optimizeit'
if (-not (Test-Path (Join-Path $source 'SKILL.md'))) {
    throw "Skill not found: $source"
}

if ($Project) {
    $base = (Resolve-Path $Project).Path
} else {
    $base = $HOME
}

$agents = [ordered]@{
    claude = @{ Label = 'Claude Code'; Dir = Join-Path $base '.claude\skills' }
    codex  = @{ Label = 'Codex';       Dir = Join-Path $base '.agents\skills' }
    cursor = @{ Label = 'Cursor';      Dir = Join-Path $base '.cursor\skills' }
    gemini = @{ Label = 'Gemini CLI';  Dir = Join-Path $base '.gemini\skills' }
}

if ($Target -eq 'all') { $selected = @($agents.Keys) } else { $selected = @($Target) }

foreach ($key in $selected) {
    $agent = $agents[$key]
    $dest = Join-Path $agent.Dir 'optimizeit'
    New-Item -ItemType Directory -Force -Path $agent.Dir | Out-Null
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Copy-Item -Recurse -Path $source -Destination $dest
    Write-Host "[$($agent.Label)] installed: $dest"
}

Write-Host 'Done. Restart your agent (in Gemini CLI: /skills reload).'

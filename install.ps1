<#
.SYNOPSIS
  OptimizeIT kurulum betiği (Windows PowerShell 5.1+ / PowerShell 7+)

.EXAMPLE
  .\install.ps1                              # tüm ajanlara, kullanıcı düzeyinde
.EXAMPLE
  .\install.ps1 -Hedef cursor                # yalnızca Cursor, kullanıcı düzeyinde
.EXAMPLE
  .\install.ps1 -Hedef claude -Proje .       # yalnızca Claude Code, bu projeye
#>
param(
    [ValidateSet('claude', 'codex', 'cursor', 'gemini', 'hepsi')]
    [string]$Hedef = 'hepsi',
    [string]$Proje = ''
)

$ErrorActionPreference = 'Stop'

$kaynak = Join-Path $PSScriptRoot 'skills\optimizeit'
if (-not (Test-Path (Join-Path $kaynak 'SKILL.md'))) {
    throw "Skill bulunamadı: $kaynak"
}

if ($Proje) {
    $kok = (Resolve-Path $Proje).Path
} else {
    $kok = $HOME
}

$dizinler = [ordered]@{
    claude = @{ Ad = 'Claude Code'; Yol = Join-Path $kok '.claude\skills' }
    codex  = @{ Ad = 'Codex';       Yol = Join-Path $kok '.agents\skills' }
    cursor = @{ Ad = 'Cursor';      Yol = Join-Path $kok '.cursor\skills' }
    gemini = @{ Ad = 'Gemini CLI';  Yol = Join-Path $kok '.gemini\skills' }
}

if ($Hedef -eq 'hepsi') { $secilenler = @($dizinler.Keys) } else { $secilenler = @($Hedef) }

foreach ($anahtar in $secilenler) {
    $bilgi = $dizinler[$anahtar]
    $hedefDizin = Join-Path $bilgi.Yol 'optimizeit'
    New-Item -ItemType Directory -Force -Path $bilgi.Yol | Out-Null
    if (Test-Path $hedefDizin) { Remove-Item -Recurse -Force $hedefDizin }
    Copy-Item -Recurse -Path $kaynak -Destination $hedefDizin
    Write-Host "[$($bilgi.Ad)] kuruldu: $hedefDizin"
}

Write-Host 'Tamamlandı. Ajanı yeniden başlatın (Gemini CLI''da: /skills reload).'

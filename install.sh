#!/usr/bin/env sh
# OptimizeIT kurulum betiği (macOS / Linux / Git Bash)
#
# Kullanım:
#   sh install.sh [--hedef claude|codex|cursor|gemini|hepsi] [--proje <dizin>]
#
# Örnekler:
#   sh install.sh                          # tüm ajanlara, kullanıcı düzeyinde
#   sh install.sh --hedef cursor           # yalnızca Cursor, kullanıcı düzeyinde
#   sh install.sh --hedef claude --proje . # yalnızca Claude Code, bu projeye
set -eu

HEDEF="hepsi"
PROJE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --hedef) HEDEF="${2:?--hedef bir değer bekler}"; shift 2 ;;
    --proje) PROJE="${2:?--proje bir dizin bekler}"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Bilinmeyen argüman: $1" >&2; exit 1 ;;
  esac
done

KAYNAK_KOK="$(cd "$(dirname "$0")" && pwd)"
KAYNAK="$KAYNAK_KOK/skills/optimizeit"
[ -f "$KAYNAK/SKILL.md" ] || { echo "Skill bulunamadı: $KAYNAK" >&2; exit 1; }

if [ -n "$PROJE" ]; then
  KOK="$(cd "$PROJE" && pwd)"
  CLAUDE_DIR="$KOK/.claude/skills"
  CODEX_DIR="$KOK/.agents/skills"
  CURSOR_DIR="$KOK/.cursor/skills"
  GEMINI_DIR="$KOK/.gemini/skills"
else
  CLAUDE_DIR="$HOME/.claude/skills"
  CODEX_DIR="$HOME/.agents/skills"
  CURSOR_DIR="$HOME/.cursor/skills"
  GEMINI_DIR="$HOME/.gemini/skills"
fi

kur() {
  ad="$1"; hedef_dizin="$2"
  mkdir -p "$hedef_dizin"
  rm -rf "$hedef_dizin/optimizeit"
  cp -R "$KAYNAK" "$hedef_dizin/optimizeit"
  echo "[$ad] kuruldu: $hedef_dizin/optimizeit"
}

case "$HEDEF" in
  claude) kur "Claude Code" "$CLAUDE_DIR" ;;
  codex)  kur "Codex" "$CODEX_DIR" ;;
  cursor) kur "Cursor" "$CURSOR_DIR" ;;
  gemini) kur "Gemini CLI" "$GEMINI_DIR" ;;
  hepsi)
    kur "Claude Code" "$CLAUDE_DIR"
    kur "Codex" "$CODEX_DIR"
    kur "Cursor" "$CURSOR_DIR"
    kur "Gemini CLI" "$GEMINI_DIR"
    ;;
  *) echo "Geçersiz hedef: $HEDEF (claude|codex|cursor|gemini|hepsi)" >&2; exit 1 ;;
esac

echo "Tamamlandı. Ajanı yeniden başlatın (Gemini CLI'da: /skills reload)."

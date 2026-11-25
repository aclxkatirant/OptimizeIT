#!/usr/bin/env sh
# OptimizeIT installer (macOS / Linux / Git Bash)
#
# Usage:
#   sh install.sh [--target claude|codex|cursor|gemini|all] [--project <dir>]
#
# Examples:
#   sh install.sh                              # all agents, user level
#   sh install.sh --target cursor              # Cursor only, user level
#   sh install.sh --target claude --project .  # Claude Code only, this project
set -eu

TARGET="all"
PROJECT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target needs a value}"; shift 2 ;;
    --project) PROJECT="${2:?--project needs a directory}"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

SOURCE_ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SOURCE_ROOT/skills/optimizeit"
[ -f "$SOURCE/SKILL.md" ] || { echo "Skill not found: $SOURCE" >&2; exit 1; }

if [ -n "$PROJECT" ]; then
  BASE="$(cd "$PROJECT" && pwd)"
else
  BASE="$HOME"
fi

CLAUDE_DIR="$BASE/.claude/skills"
CODEX_DIR="$BASE/.agents/skills"
CURSOR_DIR="$BASE/.cursor/skills"
GEMINI_DIR="$BASE/.gemini/skills"

install_to() {
  label="$1"; dest="$2"
  mkdir -p "$dest"
  rm -rf "$dest/optimizeit"
  cp -R "$SOURCE" "$dest/optimizeit"
  echo "[$label] installed: $dest/optimizeit"
}

case "$TARGET" in
  claude) install_to "Claude Code" "$CLAUDE_DIR" ;;
  codex)  install_to "Codex" "$CODEX_DIR" ;;
  cursor) install_to "Cursor" "$CURSOR_DIR" ;;
  gemini) install_to "Gemini CLI" "$GEMINI_DIR" ;;
  all)
    install_to "Claude Code" "$CLAUDE_DIR"
    install_to "Codex" "$CODEX_DIR"
    install_to "Cursor" "$CURSOR_DIR"
    install_to "Gemini CLI" "$GEMINI_DIR"
    ;;
  *) echo "Invalid target: $TARGET (claude|codex|cursor|gemini|all)" >&2; exit 1 ;;
esac

echo "Done. Restart your agent (in Gemini CLI: /skills reload)."

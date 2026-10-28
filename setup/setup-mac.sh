#!/usr/bin/env bash
# One-time setup of a Mac editing laptop for the podcast skills.
# Safe to re-run: it updates what exists and only installs what is missing.
#
#   bash setup/setup-mac.sh            # repo goes to ~/podcast-edit-shorts-trailer-
#   bash setup/setup-mac.sh ~/Work/pod # or choose the folder
set -euo pipefail

REPO_URL="https://github.com/vikasbanjare/podcast-edit-shorts-trailer-.git"
BRANCH="${BRANCH:-claude/new-session-sd91hc}"
DEST="${1:-$HOME/podcast-edit-shorts-trailer-}"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1; }

say "1/5  Checking tools"
need git     && ok "git"     || { warn "git missing: run 'xcode-select --install', then re-run"; exit 1; }
need python3 && ok "python3" || { warn "python3 missing: run 'xcode-select --install' or 'brew install python'"; exit 1; }
need claude  && ok "Claude Code ($(claude --version 2>/dev/null | head -1))" \
             || { warn "Claude Code missing: install it from https://claude.com/claude-code, then re-run"; exit 1; }
if need node && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]; then ok "node $(node -v)"
else warn "Node.js 20+ missing (needed for the Premiere MCP): 'brew install node' or https://nodejs.org"; exit 1; fi
need ffmpeg  && ok "ffmpeg"  || warn "ffmpeg missing (optional: silence detection and fallback renders): 'brew install ffmpeg'"

say "2/5  Getting the skills"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch -q origin "$BRANCH" && git -C "$DEST" checkout -q "$BRANCH" && git -C "$DEST" pull -q --ff-only origin "$BRANCH"
  ok "updated $DEST"
else
  git clone -q --branch "$BRANCH" "$REPO_URL" "$DEST"
  ok "cloned to $DEST"
fi

say "3/5  Premiere Pro MCP for Claude Code"
if claude mcp list 2>/dev/null | grep -qi premiere; then
  ok "a Premiere MCP is already configured; keeping it:"
  claude mcp list 2>/dev/null | grep -i premiere | sed 's/^/    /'
else
  need premiere-pro-mcp || npm install -g adobe-premiere-pro-mcp
  premiere-pro-mcp --install-cep
  claude mcp add -s user -e PREMIERE_MCP_TELEMETRY=0 premiere-pro -- premiere-pro-mcp
  ok "installed adobe-premiere-pro-mcp and registered it with Claude Code"
fi
need premiere-pro-mcp && premiere-pro-mcp --doctor || true

say "4/5  Self-test of the skill scripts"
for s in podcast-clip-intelligence premiere-podcast-cutter; do
  (cd "$DEST/.claude/skills/$s" && python3 -m unittest discover -s tests >/dev/null 2>&1) \
    && ok "$s tests pass" || warn "$s tests failed: run them in $DEST/.claude/skills/$s to see why"
done

say "5/5  Done. Each editing day:"
cat <<EOF
  1. Open Premiere Pro and your project, then Window > Extensions > MCP Bridge (CEP) and start the bridge.
  2. In Terminal:
       cd "$DEST"
       caffeinate -dimsu claude remote-control
     (caffeinate keeps the Mac awake while the session runs, so it doesn't drop offline.)
  3. In the Claude app, this laptop now shows up. Ask, for example:
       "test-2 is the full podcast. Find the best Shorts and make a trailer."
EOF

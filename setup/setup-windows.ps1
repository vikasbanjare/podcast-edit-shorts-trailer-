# One-time setup of a Windows editing laptop for the podcast skills.
# Safe to re-run: it updates what exists and only installs what is missing.
#
#   powershell -ExecutionPolicy Bypass -File setup\setup-windows.ps1
#   powershell -ExecutionPolicy Bypass -File setup\setup-windows.ps1 -Dest D:\Work\pod
param([string]$Dest = $(if (Test-Path "$PSScriptRoot\..\.git") { (Resolve-Path "$PSScriptRoot\..").Path } else { "$HOME\podcast-edit-shorts-trailer-" }),
      [string]$Branch = "claude/new-session-sd91hc")
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/vikasbanjare/podcast-edit-shorts-trailer-.git"

function Say($m)  { Write-Host "`n$m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" }
function Warn($m) { Write-Host "  !   $m" -ForegroundColor Yellow }
function Has($c)  { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Say "1/5  Checking tools"
if (-not (Has git))    { Warn "git missing: winget install Git.Git, then re-run"; exit 1 }; Ok "git"
$py = if (Has python) { "python" } elseif (Has py) { "py" } else { $null }
if (-not $py)          { Warn "Python missing: winget install Python.Python.3.12, then re-run"; exit 1 }; Ok "python ($py)"
if (-not (Has claude)) { Warn "Claude Code missing: install it from https://claude.com/claude-code, then re-run"; exit 1 }; Ok "Claude Code"
if (-not (Has node) -or [int](node -p "process.versions.node.split('.')[0]") -lt 20) {
  Warn "Node.js 20+ missing (needed for the Premiere MCP): winget install OpenJS.NodeJS.LTS"; exit 1 }; Ok "node $(node -v)"
if (Has ffmpeg) { Ok "ffmpeg" } else { Warn "ffmpeg missing (optional): winget install Gyan.FFmpeg" }

Say "2/5  Getting the skills"
if (Test-Path "$Dest\.git") {
  git -C $Dest fetch -q origin $Branch; git -C $Dest checkout -q $Branch; git -C $Dest pull -q --ff-only origin $Branch
  Ok "updated $Dest"
} else {
  git clone -q --branch $Branch $RepoUrl $Dest; Ok "cloned to $Dest"
}

Say "3/5  Premiere Pro MCP for Claude Code"
$existing = (claude mcp list 2>$null) | Select-String -Pattern "premiere" -SimpleMatch
if ($existing) {
  Ok "a Premiere MCP is already configured; keeping it:"; $existing | ForEach-Object { "    $_" }
} else {
  if (-not (Has premiere-pro-mcp)) { npm install -g adobe-premiere-pro-mcp }
  premiere-pro-mcp --install-cep
  claude mcp add -s user -e PREMIERE_MCP_TELEMETRY=0 premiere-pro -- premiere-pro-mcp
  Ok "installed adobe-premiere-pro-mcp and registered it with Claude Code"
}
if (Has premiere-pro-mcp) { premiere-pro-mcp --doctor }

Say "4/5  Self-test of the skill scripts"
foreach ($s in "podcast-clip-intelligence", "premiere-podcast-cutter") {
  Push-Location "$Dest\.claude\skills\$s"
  & $py -m unittest discover -s tests *> $null
  if ($LASTEXITCODE -eq 0) { Ok "$s tests pass" } else { Warn "$s tests failed: run them in $PWD to see why" }
  Pop-Location
}

Say "5/5  Done. Each editing day:"
@"
  1. Open Premiere Pro and your project, then Window > Extensions > MCP Bridge (CEP) and start the bridge.
  2. In PowerShell:
       cd "$Dest"
       claude remote-control
     Keep the laptop plugged in and set Settings > System > Power > Sleep to 'Never' while it runs,
     so it doesn't drop offline.
  3. In the Claude app, this laptop now shows up. Ask, for example:
       "test-2 is the full podcast. Find the best Shorts and make a trailer."
"@

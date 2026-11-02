# Installs the Houdini MCP bridge package for the newest Houdini user prefs folder.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Plugin = Join-Path $Root "houdini_plugin"

$docs = Join-Path $env:USERPROFILE "Documents"
$candidates = Get-ChildItem $docs -Directory -Filter "houdini*" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending

if (-not $candidates) {
    Write-Error "No houdini* folder found under $docs. Open Houdini once, then re-run."
}

$targetPrefs = $candidates[0].FullName
$packagesDir = Join-Path $targetPrefs "packages"
New-Item -ItemType Directory -Force -Path $packagesDir | Out-Null

$pkgJson = Join-Path $packagesDir "houdini_mcp.json"
$pluginPath = $Plugin.Replace("\", "/")
@"
{
  "load_package_once": true,
  "path": "$pluginPath",
  "env": [
    {
      "PYTHONPATH": {
        "value": "$pluginPath/python",
        "method": "prepend"
      }
    }
  ]
}
"@ | Set-Content -Encoding UTF8 $pkgJson

# Sync user-prefs startup hooks so they call GUI-only autostart (no .bak dance).
$scriptsDir = Join-Path $targetPrefs "scripts"
New-Item -ItemType Directory -Force -Path $scriptsDir | Out-Null
$hook = @"
"""User-prefs hook — GUI-only MCP bridge autostart (skips hython/hbatch)."""
from __future__ import annotations
import sys
root = r"$($Plugin.Replace('\', '\\'))\python"
if root not in sys.path:
    sys.path.insert(0, root)
try:
    import houdini_mcp_bridge
    houdini_mcp_bridge.autostart_bridge()
except Exception as exc:
    print("[houdini-mcp] autostart failed:", exc)
"@
Set-Content -Encoding UTF8 (Join-Path $scriptsDir "123.py") $hook
Set-Content -Encoding UTF8 (Join-Path $scriptsDir "456.py") $hook

Write-Host "Installed Houdini package -> $pkgJson"
Write-Host "Synced startup hooks -> $scriptsDir\123.py / 456.py"
Write-Host "Restart Houdini. Bridge listens on 127.0.0.1:18812 (GUI only)."
Write-Host "Recovery in Python Shell: houdini_mcp_bridge.ensure_bridge()"

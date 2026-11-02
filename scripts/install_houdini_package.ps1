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

Write-Host "Installed Houdini package -> $pkgJson"
Write-Host "Restart Houdini. Bridge will listen on 127.0.0.1:18812"

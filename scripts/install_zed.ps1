# Install Python package and register houdini-mcp in Zed settings.json
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Installing houdini-mcp Python package..."
& python -m pip install -e "$Root"

$settingsPath = Join-Path $env:APPDATA "Zed\settings.json"
if (-not (Test-Path $settingsPath)) {
    Write-Error "Zed settings not found at $settingsPath"
}

$backup = "$settingsPath.bak-houdini-mcp"
Copy-Item $settingsPath $backup -Force
Write-Host "Backup written to $backup"

$python = (Get-Command python).Source.Replace("\", "/")
$raw = Get-Content -Raw $settingsPath

if ($raw -match '"houdini-mcp"\s*:') {
    Write-Host "houdini-mcp already present in Zed settings - leaving as-is."
} elseif ($raw -match '"context_servers"\s*:\s*\{') {
    $insert = @"
    "houdini-mcp": {
      "command": "$python",
      "args": ["-m", "houdini_mcp"],
      "env": {
        "HOUDINI_MCP_HOST": "127.0.0.1",
        "HOUDINI_MCP_PORT": "18812"
      }
    },
"@
    $updated = [regex]::Replace(
        $raw,
        '"context_servers"\s*:\s*\{',
        { param($m) ($m.Value + "`r`n" + $insert) },
        1
    )
    Set-Content -Path $settingsPath -Value $updated -Encoding UTF8
    Write-Host "Added houdini-mcp to context_servers in $settingsPath"
} else {
    Write-Host "Could not find context_servers block. Add this manually:"
    Write-Host $python
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. In Zed: Extensions -> Install Dev Extension -> select:"
Write-Host "   $Root"
Write-Host "2. Settings -> AI -> MCP Servers -> confirm Houdini MCP is active"
Write-Host "3. Optional live Houdini: .\scripts\install_houdini_package.ps1"

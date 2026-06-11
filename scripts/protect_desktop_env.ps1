$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "protect_desktop_env.py"
python $scriptPath @args
exit $LASTEXITCODE

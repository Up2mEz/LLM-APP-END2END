param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
& (Join-Path $PSScriptRoot '.venv312\Scripts\python.exe') -m ncd_gemma.cli serve --port $Port

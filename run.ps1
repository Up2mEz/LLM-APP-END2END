param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
& (Join-Path $PSScriptRoot '.venv312\Scripts\python.exe') -B -m ncd_gemma.cli serve --port $Port

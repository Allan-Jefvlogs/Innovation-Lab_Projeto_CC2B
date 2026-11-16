# Inicia o Reflex usando os mesmos defaults e overrides do comando `reflex run`.
$ErrorActionPreference = 'Stop'
$nexstockProjectRoot = Split-Path -Parent $PSScriptRoot
$nexstockReflex = Join-Path $nexstockProjectRoot '.venv\Scripts\reflex.exe'
if (-not (Test-Path -LiteralPath $nexstockReflex)) {
    throw 'Reflex nao encontrado na .venv do projeto.'
}

Push-Location -LiteralPath $nexstockProjectRoot
try {
    & $nexstockReflex run --env dev
}
finally {
    Pop-Location
}

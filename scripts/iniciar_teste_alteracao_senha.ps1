# Habilita somente a troca de senha durante esta execucao local do Reflex.
$ErrorActionPreference = 'Stop'
$nexstockProjectRoot = Split-Path -Parent $PSScriptRoot
$nexstockReflex = Join-Path $nexstockProjectRoot '.venv\Scripts\reflex.exe'
if (-not (Test-Path -LiteralPath $nexstockReflex)) {
    throw 'Reflex nao encontrado na .venv do projeto.'
}
$nexstockPreviousPasswordFlag = [Environment]::GetEnvironmentVariable('NEXSTOCK_ACCOUNT_PASSWORD_ENABLED', 'Process')
Push-Location -LiteralPath $nexstockProjectRoot
try {
    $env:NEXSTOCK_ACCOUNT_PASSWORD_ENABLED = 'true'
    & $nexstockReflex run --env dev
}
finally {
    [Environment]::SetEnvironmentVariable('NEXSTOCK_ACCOUNT_PASSWORD_ENABLED', $nexstockPreviousPasswordFlag, 'Process')
    Pop-Location
}

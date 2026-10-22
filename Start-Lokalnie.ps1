param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$runtimeDir = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonExe = if ($pythonCmd) { $pythonCmd.Source } else { Join-Path $runtimeDir 'python\python.exe' }
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$nodeExe = if ($nodeCmd) { $nodeCmd.Source } else { Join-Path $runtimeDir 'node\bin\node.exe' }
$pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
$pnpmExe = if ($pnpmCmd) { $pnpmCmd.Source } else { Join-Path $runtimeDir 'bin\fallback\pnpm.cmd' }
foreach ($exe in @($pythonExe,$nodeExe,$pnpmExe)) { if (-not (Test-Path -LiteralPath $exe)) { throw "Brak wymaganego programu: $exe" } }
$localDir = Join-Path $projectDir '.local'
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$env:PYTHONPATH = Join-Path $localDir 'pylibs'
$databaseFile = (Join-Path $localDir 'lims.db').Replace('\','/')
$env:DATABASE_URL = "sqlite:///$databaseFile"
$env:COOKIE_SECURE = 'false'
$env:PUBLIC_URL = 'http://127.0.0.1:8080'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:SMTP_ENABLED = 'false'
Push-Location (Join-Path $projectDir 'backend')
try {
    & $pythonExe -m pip install --target $env:PYTHONPATH -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Nie udało się zainstalować zależności backendu' }
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migracja nie powiodła się' }
    & $pythonExe -c 'from app.models import Session,User; from sqlalchemy import select; import sys; sys.exit(0 if Session().scalar(select(User.id)) else 2)'
    if ($LASTEXITCODE -eq 2) { & $pythonExe -m app.cli create-admin --login admin; if ($LASTEXITCODE -ne 0) { throw 'Nie utworzono administratora' } }
} finally { Pop-Location }
Push-Location (Join-Path $projectDir 'frontend')
try { & $pnpmExe install --frozen-lockfile; if ($LASTEXITCODE -ne 0) { throw 'Instalacja frontendu nie powiodła się' } } finally { Pop-Location }
if ($PrepareOnly) { Write-Host 'Przygotowano lokalną bazę i zależności.'; exit 0 }
Write-Host 'Tryb lokalny SQLite dla jednego operatora. URL: http://127.0.0.1:8080. Ctrl+C zatrzymuje serwery.'
$backendDir = Join-Path $projectDir 'backend'
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru
Push-Location (Join-Path $projectDir 'frontend')
try { & $nodeExe 'node_modules/vite/bin/vite.js' '--host' '127.0.0.1' '--port' '8080' '--strictPort' } finally { if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id }; Pop-Location }

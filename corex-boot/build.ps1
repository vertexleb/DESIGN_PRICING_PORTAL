<#
  Builds dist\CorexBoot.exe on Windows 10/11 (64-bit).
  Requires Python 3.12+ on PATH (python.org installer or `py` launcher).
  Usage:  powershell -ExecutionPolicy Bypass -File build.ps1 [-SkipTests]
#>
param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
    if ($LASTEXITCODE) { throw 'Could not create a Python virtual environment' }
}
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

& $venvPy -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'"
& $venvPy -m pip install --upgrade pip | Out-Null
& $venvPy -m pip install -r requirements-dev.txt
if ($LASTEXITCODE) { throw 'pip install failed' }

if (-not $SkipTests) {
    & $venvPy -m pytest -q
    if ($LASTEXITCODE) { throw 'Tests failed - not building.' }
}

& $venvPy -m PyInstaller --noconfirm --clean corex_boot.spec
if ($LASTEXITCODE) { throw 'PyInstaller failed' }

$exe = Join-Path $PSScriptRoot 'dist\CorexBoot.exe'
if (-not (Test-Path $exe)) { throw "Build finished but $exe is missing" }
Write-Host "Built: $exe" -ForegroundColor Green

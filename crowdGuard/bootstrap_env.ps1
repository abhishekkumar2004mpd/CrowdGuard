param(
    [string]$VenvName = ".venv"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot $VenvName

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath"
    python -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists at $venvPath"
}

$pythonExe = Join-Path $venvPath "Scripts\python.exe"

Write-Host "Upgrading pip"
python -m pip --python $pythonExe install --upgrade pip setuptools wheel

Write-Host "Installing project dependencies"
python -m pip --python $pythonExe install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "Environment ready"

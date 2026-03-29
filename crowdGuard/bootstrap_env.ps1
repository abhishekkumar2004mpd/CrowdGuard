param(
    [string]$VenvName = ".venv",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot $VenvName

if (-not $PythonExe) {
    $python312Candidate = "C:\Users\KIIT0001\AppData\Local\Programs\Python\Python312\python.exe"
    if (Test-Path $python312Candidate) {
        $PythonExe = $python312Candidate
    } else {
        try {
            py -3.12 --version | Out-Null
            $PythonExe = "py -3.12"
        } catch {
            $PythonExe = "python"
        }
    }
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath"
    if ($PythonExe -eq "py -3.12") {
        py -3.12 -m venv $venvPath
    } else {
        & $PythonExe -m venv $venvPath
    }
} else {
    Write-Host "Virtual environment already exists at $venvPath"
}

$venvPythonExe = Join-Path $venvPath "Scripts\python.exe"

Write-Host "Upgrading pip"
python -m pip --python $venvPythonExe install --upgrade pip setuptools wheel

Write-Host "Installing project dependencies"
python -m pip --python $venvPythonExe install -r (Join-Path $projectRoot "requirements.txt")

Write-Host "Environment ready"

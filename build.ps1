$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller no está instalado. Instálalo con: python -m pip install pyinstaller"
    exit 1
}

python -m PyInstaller --noconfirm --onefile --windowed --name Analizador_EMU8086 main.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

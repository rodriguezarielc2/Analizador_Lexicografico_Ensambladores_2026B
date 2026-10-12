@echo off
setlocal
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo No se pudo iniciar el analizador. Verifica Python 3.11 y Tkinter.
    pause
)
endlocal

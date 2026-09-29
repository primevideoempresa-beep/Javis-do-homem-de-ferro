@echo off
setlocal
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo.
        echo Python nao foi encontrado.
        echo Instale Python 3.11 ou mais recente em https://www.python.org/downloads/windows/
        echo Marque "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )
)

echo Iniciando Javis Windows...
start "Javis Windows Bridge" /min %PY% windows\javis_windows.py
timeout /t 1 /nobreak >nul
start "Javis Windows Painel" %PY% windows\painel_javis.py
exit /b 0

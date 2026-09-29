@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (
  where python >nul 2>nul
  if %errorlevel%==0 (set "PY=python") else (
    echo Python nao encontrado.
    echo Baixe em https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
)
echo Testando os arquivos Javis Windows...
%PY% -m py_compile windows\javis_windows.py windows\painel_javis.py windows\test_javis_windows.py
if errorlevel 1 (
  echo.
  echo ERRO: corrija os arquivos Python.
  pause
  exit /b 1
)
echo.
echo Tudo certo. Nenhum pacote Python externo e necessario.
echo.
pause

@echo off
setlocal

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "BACKEND_VENV=%BACKEND%\.venv"
set "VENV_PYTHON=%BACKEND_VENV%\Scripts\python.exe"
set "VENV_ACTIVATE=%BACKEND_VENV%\Scripts\activate.bat"

if exist "%BACKEND%\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /R /C:"^API_HOST=" /C:"^API_PORT=" "%BACKEND%\.env"`) do (
    if /I "%%A"=="API_HOST" set "BACKEND_HOST=%%B"
    if /I "%%A"=="API_PORT" set "BACKEND_PORT=%%B"
  )
)

if "%BACKEND_HOST%"=="" set "BACKEND_HOST=127.0.0.1"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8000"

if not exist "%BACKEND%" (
  echo Backend folder not found: %BACKEND%
  exit /b 1
)

if not exist "%BACKEND%\requirements.txt" (
  echo requirements.txt not found: %BACKEND%\requirements.txt
  exit /b 1
)

cd /d "%BACKEND%"

if not exist "%VENV_PYTHON%" (
  echo [setup] Creating virtual environment in %BACKEND_VENV%
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    py -3 -m venv ".venv"
  ) else (
    where python >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
      echo [error] Python not found. Install Python 3 and try again.
      exit /b 1
    )
    python -m venv ".venv"
  )
)

if not exist "%VENV_ACTIVATE%" (
  echo [error] Failed to create virtual environment at %BACKEND_VENV%
  exit /b 1
)

call "%VENV_ACTIVATE%"
if %ERRORLEVEL% NEQ 0 (
  echo [error] Failed to activate virtual environment.
  exit /b 1
)

echo [setup] Installing backend dependencies...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
  echo [error] Failed to upgrade pip.
  exit /b 1
)

python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo [error] Failed to install backend dependencies.
  exit /b 1
)

echo [start] Starting backend on http://%BACKEND_HOST%:%BACKEND_PORT%
python -m uvicorn main:app --host %BACKEND_HOST% --port %BACKEND_PORT%

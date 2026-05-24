@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"

if not exist "%FRONTEND%" (
  echo Frontend folder not found: %FRONTEND%
  exit /b 1
)

cd /d "%FRONTEND%"
npm run dev -- --host 127.0.0.1 --port 5173

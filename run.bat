@echo off
REM Mushar Benchmark Studio - starts on http://localhost:8765
REM Optional: set ANTHROPIC_API_KEY=... before running to enable live Claude research.
set PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if not exist "%PY%" set PY=python
cd /d "%~dp0"
start "" http://localhost:8765
"%PY%" app\server.py

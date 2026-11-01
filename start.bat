@echo off
rem Double-click this file on Windows to start Job Finder.
rem First time: it creates a private Python folder (.venv) and installs the
rem libraries. After that it starts the app right away.

cd /d "%~dp0"

rem "py" is the Python launcher that python.org installs. Fall back to "python".
set PY=python
where py >nul 2>nul && set PY=py

if exist .venv\Scripts\python.exe goto installed
%PY% --version >nul 2>nul || goto nopython
echo First time setup, this takes a minute...
%PY% -m venv .venv || goto failed

:installed
rem Install the libraries only if requirements.txt changed since last time
fc /b requirements.txt .venv\installed-requirements.txt >nul 2>nul && goto run
echo Installing libraries...
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt || goto failed
copy /y requirements.txt .venv\installed-requirements.txt >nul

:run
.venv\Scripts\python.exe job_finder.py
echo.
pause
exit /b 0

:nopython
echo Python is not installed. Get it from https://www.python.org/downloads/
echo When installing, tick the box "Add python.exe to PATH".
pause
exit /b 1

:failed
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1

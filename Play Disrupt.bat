@echo off
rem Starts Disrupt from this folder. If the game crashes, the error stays on screen.
cd /d "%~dp0"
python "code (finish)\main.py"
if errorlevel 1 pause

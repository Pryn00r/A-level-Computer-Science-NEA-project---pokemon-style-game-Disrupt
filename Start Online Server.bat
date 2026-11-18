@echo off
rem Iteration 37: runs the online server on this computer, for testing with two copies of the game.
rem The game connects to it as long as there is no online_server.txt in the code folder.
cd /d "%~dp0"
python -m pip install --quiet websockets
python "code (finish)\online_server.py"
pause

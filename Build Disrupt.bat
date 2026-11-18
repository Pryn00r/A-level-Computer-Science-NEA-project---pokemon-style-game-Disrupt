@echo off
rem Iteration 37: makes Disrupt.exe, so people can play without installing Python.
rem The result is dist\Disrupt-Windows.zip - upload that to itch.io.
cd /d "%~dp0"
python -m pip install --quiet pyinstaller pygame-ce pytmx websockets
if exist build rmdir /s /q build
if exist dist\Disrupt rmdir /s /q dist\Disrupt
python -m PyInstaller --noconfirm --windowed --name Disrupt --icon disrupt.ico --paths "code (finish)" "code (finish)\main.py"
if errorlevel 1 goto failed
xcopy /e /i /q /y graphics dist\Disrupt\graphics >nul
xcopy /e /i /q /y audio dist\Disrupt\audio >nul
xcopy /e /i /q /y data dist\Disrupt\data >nul
if exist "code (finish)\online_server.txt" copy /y "code (finish)\online_server.txt" dist\Disrupt\_internal\ >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path dist\Disrupt -DestinationPath dist\Disrupt-Windows.zip"
echo.
echo Done! Your game is in dist\Disrupt (double-click Disrupt.exe) and dist\Disrupt-Windows.zip
pause
exit /b 0
:failed
echo The build failed - read the message above.
pause

@echo off
rem Creates a "Disrupt" shortcut on the Desktop that starts the game with its own icon.
rem Double-click this file once. It finds Python (pythonw, so no black console window opens).
setlocal
set "ROOT=%~dp0"
set "PYW="
for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%P"
if not defined PYW for /f "delims=" %%P in ('where pyw 2^>nul') do if not defined PYW set "PYW=%%P"
if not defined PYW (
  echo Could not find Python. Install Python from python.org and tick "Add to PATH", then run this again.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=$env:ROOT; $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'Disrupt.lnk')); $s.TargetPath=$env:PYW; $s.Arguments='\"'+$root+'code (finish)\main.py\"'; $s.WorkingDirectory=$root.TrimEnd([char]92); $s.IconLocation=$root+'disrupt.ico'; $s.Description='Disrupt - an NEA project by Prabnoor'; $s.Save()"
if errorlevel 1 (
  echo Something went wrong making the shortcut.
  pause
  exit /b 1
)
echo Done! There is now a Disrupt shortcut on your Desktop.
pause

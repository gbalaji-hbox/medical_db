@echo off
echo =====================================
echo Installing Git, Node.js, and Python
echo =====================================

:: --- Download installers ---
echo Downloading installers...

powershell -Command "Invoke-WebRequest https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe -OutFile git.exe"
powershell -Command "Invoke-WebRequest https://nodejs.org/dist/latest-v20.x/node-v20.20.2-x64.msi -OutFile node.msi"
powershell -Command "Invoke-WebRequest https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe -OutFile python.exe"

:: --- Install Git silently ---
echo Installing Git...
start /wait git.exe /VERYSILENT /NORESTART

:: --- Install Node.js silently ---
echo Installing Node.js...
start /wait msiexec /i node.msi /qn /norestart

:: --- Install Python silently ---
echo Installing Python...
start /wait python.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

:: --- Set Git configuration ---
echo Configuring Git...
git config --global user.name "Balaji.G"
git config --global user.email "balaji.g@hbox.ai"

:: --- Optional: install pnpm (lightweight package manager) ---
echo Installing pnpm...
npm install -g pnpm

:: --- Cleanup ---
echo Cleaning up installers...
del git.exe
del node.msi
del python.exe

echo.
echo =====================================
echo Installation complete!
echo Restart terminal before using tools
echo =====================================
pause
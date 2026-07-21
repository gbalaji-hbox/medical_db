@echo off
echo =====================================
echo  DrChrono Automation Runner
echo =====================================

:: ── CONFIGURATION ─────────────────────────────────────────────────────────────
set drchrono_username=Hbox01
set drchrono_password=Springxhi2026@
set API_BASE_URL=https://qam.hbox.ai/emr
set API_KEY=7C8SBVLtOuADV5HrrrbsO2KXjeRABkKcUoNqA2vHMzE
:: ─────────────────────────────────────────────────────────────────────────────

:: ── Check Node.js — install if missing (portable zip, no MSI) ────────────────
set NODE_DIR=%LOCALAPPDATA%\node-v20.20.2-win-x64
where node >nul 2>&1
if errorlevel 1 (
  if exist "%NODE_DIR%\node.exe" (
    echo Node.js portable install found.
  ) else (
    echo Node.js not found. Downloading portable zip...
    powershell -Command "Invoke-WebRequest https://nodejs.org/dist/v20.20.2/node-v20.20.2-win-x64.zip -OutFile '%TEMP%\node.zip'"
    powershell -Command "Expand-Archive -Path '%TEMP%\node.zip' -DestinationPath '%LOCALAPPDATA%' -Force"
    del "%TEMP%\node.zip"
    echo Node.js extracted to %NODE_DIR%.
  )
  set "PATH=%NODE_DIR%;%PATH%"
)

:: ── Prepare dated output folder on Desktop ────────────────────────────────────
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i
set DESKTOP=%USERPROFILE%\Desktop
set OUT_ROOT=%DESKTOP%\DrChrono_%TODAY%
set RAW_DIR=%OUT_ROOT%\raw
set OUTPUT_DIR=%OUT_ROOT%\output

if not exist "%RAW_DIR%"    mkdir "%RAW_DIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

:: ── Working directory ─────────────────────────────────────────────────────────
set ORIGIN_DIR=%CD%
set WORK_DIR=%TEMP%\drchrono_run
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"
mkdir output\drchrono

:: ── Download automation script ────────────────────────────────────────────────
echo Downloading automation script...
curl -H "X-Api-Key: %API_KEY%" "%API_BASE_URL%/api/scripts/drchrono-submit.ts" -o drchrono-submit.ts

if not exist drchrono-submit.ts (
  echo ERROR: Script download failed
  pause
  exit /b 1
)

:: ── Install dependency (NO npm init needed) ───────────────────────────────────
echo Installing dependencies...
call npm install @balaji-g42/libretto @types/node --yes

if errorlevel 1 (
  echo ERROR: npm install failed
  pause
  exit /b 1
)

:: ── Install Playwright browser ───────────────────────────────────────────────
echo Installing browser...
call node_modules\.bin\playwright install chromium

if errorlevel 1 (
  echo ERROR: Playwright browser install failed
  pause
  exit /b 1
)

:: ── Force Node to see installed modules ───────────────────────────────────────
set NODE_PATH=%WORK_DIR%\node_modules

:: ── Run automation ────────────────────────────────────────────────────────────
echo Starting DrChrono automation...
call npx libretto run drchrono-submit.ts --headless

if errorlevel 1 (
  echo ERROR: Automation failed. Check logs above.
  pause
  exit /b 1
)

:: ── Copy outputs ──────────────────────────────────────────────────────────────
echo Saving files to Desktop...
for %%f in ("%WORK_DIR%\output\drchrono\*.csv") do copy "%%f" "%RAW_DIR%\" >nul
for %%f in ("%WORK_DIR%\output\drchrono\*.xlsx") do copy "%%f" "%OUTPUT_DIR%\" >nul

:: ── Cleanup ───────────────────────────────────────────────────────────────────
cd /d "%ORIGIN_DIR%"
rmdir /s /q "%WORK_DIR%"

echo.
echo =====================================
echo  Done!
echo  Raw reports : %RAW_DIR%
echo  Output file : %OUTPUT_DIR%
echo =====================================
pause
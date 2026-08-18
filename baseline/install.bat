@echo off
setlocal enabledelayedexpansion

for %%I in ("%CD%") do set PROJECTNAME=%%~nI

echo ============================================
echo  %PROJECTNAME% - First-Time Setup
echo ============================================
echo.

REM --- Step 1: Check Node.js is installed ---
REM `call` matters here: node/npm on Windows can be .cmd/.bat shims (npm
REM in particular always ships as npm.cmd), and invoking a batch file
REM from inside another batch file WITHOUT `call` hands off execution
REM permanently instead of returning - silently ending this whole
REM script right here with no error shown. Every node/npm call below
REM uses `call` for that reason, not just the ones that install packages.
call node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found on this computer.
    echo Please install the LTS version from https://nodejs.org/
    echo During install, keep the default options ^(they add Node to PATH^).
    echo.
    pause
    exit /b 1
)

for /f "tokens=1" %%v in ('node --version') do set NODEVER=%%v
echo Detected Node.js version: %NODEVER%

REM --- Step 1b: Sanity-check the Node major version. Most current Next.js
REM / React versions require Node 18.18+ or 20.9+. A too-old Node will
REM often still let npm install "succeed" and then fail confusingly
REM later - this check catches that early instead. Adjust the minimum
REM below if a specific project needs something different.
set NODEVER_NUM=%NODEVER:v=%
for /f "tokens=1 delims=." %%m in ("%NODEVER_NUM%") do set NODEMAJOR=%%m
if %NODEMAJOR% LSS 18 (
    echo.
    echo [ERROR] Node.js %NODEVER% is too old for this app ^(needs 18.18+ or 20.9+^).
    echo Please install a current LTS version from https://nodejs.org/ and re-run this script.
    echo.
    pause
    exit /b 1
)

REM --- Step 2: Check npm is available ---
call npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found. It normally ships with Node.js.
    echo Try reinstalling Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

REM --- Step 3: Install dependencies ---
echo.
echo Installing required packages... this may take a few minutes.
call npm install
if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong installing packages. See the messages above.
    pause
    exit /b 1
)

REM --- Step 4: Create env files from .env.example ---
REM     (also treats an existing-but-empty file as "needs creation",
REM     not just a missing one)
echo.
if exist .env.example (
    call :create_env_if_needed .env
    call :create_env_if_needed .env.local
    call :create_env_if_needed .env.production
) else (
    echo [WARNING] .env.example was not found - skipping env file creation.
    echo You will need to create .env / .env.local / .env.production manually.
)

REM --- Step 5: Remind the user to fill in values ---
echo.
echo ============================================
echo  IMPORTANT - Before running the app:
echo ============================================
echo  Open .env.local ^(used for local development^) and
echo  .env.production ^(used for production builds^) and
echo  fill in the real values - things like API URLs,
echo  keys, or feature flags. The copied files only
echo  contain placeholder/example values right now.
echo ============================================
echo.

set /p OPENENV="Open .env.local now to fill it in? (Y/N): "
if /i "%OPENENV%"=="Y" (
    if exist .env.local (
        notepad .env.local
    )
)

echo.
echo ============================================
echo  %PROJECTNAME% setup complete!
echo  Double-click run.bat any time to start the app.
echo ============================================
pause
exit /b 0

:create_env_if_needed
set TARGET=%~1
set NEEDS_CREATION=0
if not exist "%TARGET%" (
    set NEEDS_CREATION=1
) else (
    for %%A in ("%TARGET%") do if %%~zA==0 set NEEDS_CREATION=1
)

if "%NEEDS_CREATION%"=="1" (
    copy /y .env.example "%TARGET%" >nul
    echo Created %TARGET% from .env.example.
) else (
    echo A %TARGET% file already exists - leaving it untouched.
)
exit /b 0
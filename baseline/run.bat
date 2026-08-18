@echo off
setlocal enabledelayedexpansion

for %%I in ("%CD%") do set PROJECTNAME=%%~nI

echo ============================================
echo  Starting %PROJECTNAME% (development mode)
echo ============================================
echo.

if not exist node_modules (
    echo [ERROR] Dependencies are not installed yet.
    echo Please run install.bat first.
    echo.
    pause
    exit /b 1
)

if not exist .env.local (
    echo [ERROR] .env.local was not found.
    echo Please run install.bat first to set it up.
    echo.
    pause
    exit /b 1
)

echo App starting - check the output below for the local URL
echo ^(usually http://localhost:3000, but the exact port depends
echo  on this project's configuration^).
echo Keep this window open while using %PROJECTNAME%.
echo Press CTRL+C in this window to stop the app.
echo.

REM `call` matters here: npm on Windows ships as npm.cmd (a batch file),
REM and invoking a batch file from inside another batch file WITHOUT
REM `call` hands off execution permanently instead of returning -- this
REM was confirmed as a real, reproducible failure mode while testing
REM this script, not a theoretical concern.
call npm run dev

pause
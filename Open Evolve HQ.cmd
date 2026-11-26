@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto missing
if exist "node_modules\three\build\three.module.js" if exist "node_modules\@fontsource-variable\geist\package.json" goto start
call npm.cmd ci --ignore-scripts --no-audit --no-fund
if errorlevel 1 goto failed
:start
node scripts\start.mjs %*
if errorlevel 1 goto failed
exit /b 0
:missing
echo Install Node.js 20 or newer, then double-click this launcher again.
:failed
echo See docs\SETUP.md for help.
pause
exit /b 1

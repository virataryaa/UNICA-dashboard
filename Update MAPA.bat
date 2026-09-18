@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem  Downloads any new MAPA/SAPCANA reports, rebuilds mapa_master.csv, pushes it.
rem  Double-click to run. For Task Scheduler, pass /nopause.

echo ============================================
echo  Update MAPA
echo ============================================
echo.
set RC=0

rem  Streamlit Cloud deploys from main only. On any other branch the push
rem  would succeed and report "Published" while nothing went live, so refuse
rem  before doing any work.
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if not "!BRANCH!"=="main" (
    echo   This folder is on branch "!BRANCH!", not main.
    echo   Streamlit publishes from main, so nothing would go live.
    echo   Switch back first:   git checkout main
    set RC=1
    goto :finish
)

echo [1/2] Downloading new reports from gov.br ...
python Cleansing\mapa_fetch.py
if errorlevel 1 (
    echo.
    echo   WARNING: some downloads failed. gov.br drops connections from this
    echo   network for hours at a time. Carrying on with the reports already on
    echo   disk - run this again later to pick up anything missed.
)

echo.
echo [2/2] Rebuilding Database\mapa_master.csv ...
python Cleansing\mapa_ingest.py
if errorlevel 1 (
    echo.
    echo   REBUILD FAILED - nothing was pushed.
    set RC=1
    goto :finish
)
echo.
echo [publish] Checking for changes ...
git diff --quiet -- Database\mapa_master.csv
if not errorlevel 1 (
    echo   Nothing new to publish.
    goto :finish
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set STAMP=%%i

rem  The commit names the CSV explicitly, so nothing else sitting in the
rem  working tree can ride along into a data release.
git add Database\mapa_master.csv
git commit -m "MAPA data update !STAMP!" -- Database\mapa_master.csv
if errorlevel 1 (
    echo.
    echo   Commit failed - see the error above.
    set RC=1
    goto :finish
)

git push
if errorlevel 1 (
    echo.
    echo   Push failed - see the error above. The commit is saved locally;
    echo   ask for help before running this again.
    set RC=1
    goto :finish
)

echo.
echo   Published. Streamlit Cloud redeploys within about a minute.

:finish
echo.
echo ============================================
if "!RC!"=="0" (echo  Done.) else (echo  Stopped - read the messages above.)
echo ============================================
if /i not "%~1"=="/nopause" pause
exit /b !RC!

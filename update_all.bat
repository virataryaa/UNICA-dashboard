@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem  One button for both sources. MAPA is downloaded and rebuilt; UNICA is
rem  maintained by hand in Database\unica_master.csv, so it is only checked.
rem  Each source publishes on its own merits: a MAPA failure never holds back
rem  a good UNICA file, and the other way round.
rem
rem  Double-click to run. For Task Scheduler, pass /nopause.

echo ============================================
echo  Brazil Sugar - update and publish
echo ============================================
echo.

rem  Streamlit Cloud deploys from main only. On any other branch the push
rem  would succeed and report "Published" while nothing went live, so refuse
rem  before doing any work.
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if not "!BRANCH!"=="main" (
    echo   This folder is on branch "!BRANCH!", not main.
    echo   Streamlit publishes from main, so nothing would go live.
    echo   Switch back first:   git checkout main
    echo.
    echo ============================================
    echo  Stopped - nothing was downloaded or pushed.
    echo ============================================
    if /i not "%~1"=="/nopause" pause
    exit /b 1
)

set MAPA_OK=1
set UNICA_OK=1
set RC=0

echo [1/4] MAPA - downloading new reports from gov.br ...
python Cleansing\mapa_fetch.py
if errorlevel 1 (
    echo.
    echo   WARNING: some downloads failed. gov.br drops connections from this
    echo   network for hours at a time. Carrying on with the reports already on
    echo   disk - run this again later to pick up anything missed.
)

echo.
echo [2/4] MAPA - rebuilding Database\mapa_master.csv ...
python Cleansing\mapa_ingest.py
if errorlevel 1 (
    set MAPA_OK=0
    echo.
    echo   MAPA REBUILD FAILED - MAPA will not be published this run.
)

echo.
echo [3/4] UNICA - checking Database\unica_master.csv ...
python Cleansing\validate_csv.py
if errorlevel 1 (
    set UNICA_OK=0
    echo.
    echo   UNICA CHECK FAILED - UNICA will not be published this run.
    echo   Fix the issues above in Database\unica_master.csv, then run again.
)

echo.
echo [4/4] Publishing ...
set FILES=
set WHAT=
if "!MAPA_OK!"=="1" (
    git diff --quiet -- Database\mapa_master.csv
    if errorlevel 1 (
        set FILES=!FILES! Database\mapa_master.csv
        set WHAT=MAPA
    )
)
if "!UNICA_OK!"=="1" (
    git diff --quiet -- Database\unica_master.csv
    if errorlevel 1 (
        set FILES=!FILES! Database\unica_master.csv
        if defined WHAT (set WHAT=!WHAT! + UNICA) else (set WHAT=UNICA)
    )
)

if not defined FILES (
    echo   Nothing new to publish.
    goto :finish
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set STAMP=%%i

rem  Commit names the two CSVs explicitly, so nothing else sitting in the
rem  working tree can ride along into a data release.
git add !FILES!
git commit -m "Data update !STAMP! - !WHAT!" -- !FILES!
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
echo   Published: !WHAT!. Streamlit Cloud redeploys within about a minute.

:finish
if "!MAPA_OK!"=="0" set RC=1
if "!UNICA_OK!"=="0" set RC=1
echo.
echo ============================================
if "!RC!"=="0" (echo  Done.) else (echo  Finished with problems - read the messages above.)
echo ============================================
if /i not "%~1"=="/nopause" pause
exit /b !RC!

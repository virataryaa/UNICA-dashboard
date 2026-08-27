@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  MAPA / SAPCANA data update
echo ============================================
echo.

echo Step 1/3: Downloading any new reports from gov.br ...
python Code\mapa_fetch.py
if errorlevel 1 (
    echo.
    echo ============================================
    echo  DOWNLOAD FAILED - nothing was pushed.
    echo  Check the error above, then run this again.
    echo ============================================
    pause
    exit /b 1
)

echo.
echo Step 2/3: Rebuilding Database\mapa_master.csv ...
python Code\mapa_ingest.py
if errorlevel 1 (
    echo.
    echo ============================================
    echo  INGEST FAILED - nothing was pushed.
    echo  Check the error above, then run this again.
    echo ============================================
    pause
    exit /b 1
)

echo.
echo Step 3/3: Checking for changes ...
git diff --quiet -- Database\mapa_master.csv
if not errorlevel 1 (
    echo No changes in Database\mapa_master.csv - nothing to push.
    pause
    exit /b 0
)

echo Committing and pushing to GitHub ...
git add Database\mapa_master.csv
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set STAMP=%%i
git commit -m "MAPA data update %STAMP%"
if errorlevel 1 (
    echo.
    echo Commit failed - see error above.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo Push failed - see error above. Your commit is still saved locally;
    echo ask for help before trying again.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done. Streamlit Cloud will redeploy within
echo  about a minute.
echo ============================================
pause

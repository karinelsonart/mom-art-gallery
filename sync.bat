@echo off
REM =====================================================================
REM == MOM'S ART GALLERY SYNC SCRIPT (v15 - FINAL FILENAME FIX)    	==
REM == This version uses 'copyto' to create a file, not a folder.  	==
REM =====================================================================

echo.
echo [STEP 1 of 2] Syncing painting images...
echo.

:: This command is proven to work.
.\rclone.exe sync "gdrive:website-content/kari-paintings/" "static\gallery" --progress

echo.
echo -----------------------------------------------------------------
echo.
echo [STEP 2 of 2] Downloading and renaming the data file...
echo.

:: THIS IS THE FINAL, CORRECTED COMMAND:
:: 1. Uses 'copyto' to ensure it creates a single file.
:: 2. Sets the final filename to "gallery data.csv" inside the assets folder.
.\rclone.exe copyto "gdrive:website-content/gallery-data-new - Sheet1.csv" "assets\gallery-data.csv" --progress

echo.
echo -----------------------------------------------------------------
echo.
echo Sync Complete!
pause

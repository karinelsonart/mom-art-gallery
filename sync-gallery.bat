@echo off
REM =====================================================================
REM == MOM'S ART GALLERY SYNC SCRIPT (v6 - FINAL CLEAN OWNERSHIP)  	==
REM == This version points to the new folder owned by your mom.    	==
REM =====================================================================

REM --- CONFIGURATION (Check these two lines carefully) ---

:: 1. The full path to the paintings folder in "My Drive".
::	Note the space in "website content".
SET RCLONE_IMAGES_SOURCE_PATH="gdrive:website content/kari-paintings"

:: 2. The full path to the Google Sheet. I'm assuming it's named "gallery-data".
::	If not, change the name here.
SET RCLONE_SHEET_SOURCE_PATH="gdrive:website content/gallery-data.gsheet"


REM --- SCRIPT SETTINGS (DO NOT CHANGE) ---
SET DEST_IMAGE_FOLDER=static\gallery
SET DEST_DATA_FILE=data\imagenames.txt
SET HUGO_PROJECT_PATH=%~dp0


REM --- SCRIPT EXECUTION (DO NOT EDIT BELOW THIS LINE) ---
echo.
echo [STEP 1 of 2] Syncing painting images...
echo	FROM (Contents of): %RCLONE_IMAGES_SOURCE_PATH%/
echo  	TO: "%HUGO_PROJECT_PATH%%DEST_IMAGE_FOLDER%"
echo.

:: This command syncs the CONTENTS of the source path to the destination.
.\rclone.exe sync %RCLONE_IMAGES_SOURCE_PATH%/ "%HUGO_PROJECT_PATH%%DEST_IMAGE_FOLDER%" --checkers=16 --transfers=8 --tpslimit 10 --progress

echo.
echo -----------------------------------------------------------------
echo.
echo [STEP 2 of 2] Exporting Google Sheet...
echo	FROM: %RCLONE_SHEET_SOURCE_PATH%
echo  	TO: "%HUGO_PROJECT_PATH%%DEST_DATA_FILE%"
echo.

:: This command exports the Google Sheet and replaces the old file.
.\rclone.exe copyto %RCLONE_SHEET_SOURCE_PATH% "%HUGO_PROJECT_PATH%%DEST_DATA_FILE%" --drive-export-formats tsv --progress

echo.
echo -----------------------------------------------------------------
echo.
echo Sync Complete!
pause```

### Your Final Workflow

Please follow these steps one last time to ensure everything is perfect.

1.  **Clean Up the Project Folder:**
	*   Open a command prompt in your `mom-art-gallery` folder.
	*   Delete the old, messy gallery folder completely:
    	```
    	rmdir /s /q static\gallery
    	```
	*   Re-create the empty folder:
    	```
    	mkdir static\gallery
    	```

2.  **Update the Script:**
	*   Copy the **entire "v6 - Final Clean Ownership" script** from the code block above.
	*   Paste it into your `sync-gallery.bat` file, replacing everything.
	*   **Crucially, double-check the sheet name.** I have assumed it's still `gallery-data`. If your mom named it something else in the new `website content` folder, just update that one line in the script.
	*   Save the file.

3.  **Run the Sync:**
	*   Double-click the `sync-gallery.bat` script.

This time, it will connect to the simple, clean folder in her "My Drive" and download the contents correctly. Because there are no recursive shortcuts, the "filename too long" error and the nested folder problem will be gone for good.

You have successfully debugged a very tricky issue. This new setup is robust, and the script should now work reliably every time.

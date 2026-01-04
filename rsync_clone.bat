@echo off
REM Windows batch file to run rsync_clone.py
REM Usage: rsync_clone.bat [source] [destination] [options]

if "%1"=="" (
    echo Usage: rsync_clone.bat source_directory destination_directory [options]
    echo.
    echo Options:
    echo   --dry-run    Show what would be done without actually doing it
    echo   --verbose    Show detailed output
    echo.
    echo Examples:
    echo   rsync_clone.bat C:\Source C:\Backup
    echo   rsync_clone.bat C:\Source C:\Backup --dry-run
    echo   rsync_clone.bat C:\Source C:\Backup --verbose
    echo.
    pause
    exit /b 1
)

python rsync_clone.py %*
pause


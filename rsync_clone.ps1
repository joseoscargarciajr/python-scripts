# PowerShell script to run rsync_clone.py
# Usage: .\rsync_clone.ps1 -Source "C:\Source" -Destination "C:\Backup" [-DryRun] [-Verbose]

param(
    [Parameter(Mandatory=$true)]
    [string]$Source,
    
    [Parameter(Mandatory=$true)]
    [string]$Destination,
    
    [switch]$DryRun,
    [switch]$Verbose
)

# Build command arguments
$args = @($Source, $Destination)

if ($DryRun) {
    $args += "--dry-run"
}

if ($Verbose) {
    $args += "--verbose"
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Using Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.7 or higher."
    exit 1
}

# Check if rsync_clone.py exists
$scriptPath = Join-Path $PSScriptRoot "rsync_clone.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "rsync_clone.py not found in the same directory as this PowerShell script."
    exit 1
}

# Run the Python script
Write-Host "Running rsync_clone..." -ForegroundColor Yellow
Write-Host "Command: python $scriptPath $($args -join ' ')" -ForegroundColor Gray

try {
    & python $scriptPath $args
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "Synchronization completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "Synchronization completed with errors (exit code: $exitCode)" -ForegroundColor Red
    }
} catch {
    Write-Error "Failed to run rsync_clone: $_"
    exit 1
}

# Pause to show results
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")


# rsync_clone.py

A beginner-friendly guide for `rsync_clone.py` — a small, Windows-focused, "rsync-like" Python script that synchronizes a source folder into a destination folder and only overwrites files that have changed, using SHA-256 file hashing to detect differences.

This README is written for new Python users and explains, step-by-step, how to run the script in Windows PowerShell, how options work, what files the script creates, and troubleshooting tips.

---

## Quick summary

- Purpose: Synchronize files from a source directory to a destination directory on Windows.
- How it decides to copy: compares SHA-256 hashes (and falls back to size/mtime when hashes are missing).
- Safety: Use `--dry-run` to preview changes before modifying files.
- No external dependencies: script uses the Python standard library.

---

## What the script does (contract)

- Inputs:
	- `source` (required): path to the folder you want to copy from.
	- `destination` (required): path to the folder you want to copy to.
	- `--dry-run` / `-n` (optional): show what would be copied without performing copy.
	- `--verbose` / `-v` (optional): show more detailed logs.

- Outputs:
	- Files copied to the destination (only those that are different).
	- `rsync_clone.log` — a log file (created/appended in the current working directory).
	- `.rsync_cache.json` — a small cache file that stores file sizes, mtimes, and hashes to speed up subsequent runs.

- Error modes:
	- The script prints errors to the console and logs them to `rsync_clone.log`.
	- Exit code `0` on success, `1` on error or if an exception occurred (the script prints a message and exits with code 1).

- Success criteria:
	- Destination contains up-to-date copies of files that are present in the source.

---

## Requirements

- Python 3.6+ installed on Windows. (The script uses only the standard library.)
- Basic familiarity with PowerShell or the Windows Command Prompt.

If you do not have Python installed, download it from https://www.python.org/downloads/ and follow the installer instructions. Make sure to check "Add Python to PATH".

---

## Files the script uses/creates

- `rsync_clone.log` — text log with INFO/DEBUG messages. Created in the current working directory.
- `.rsync_cache.json` — JSON cache to avoid re-hashing unchanged files between runs. Created in the current working directory. Delete this file to force re-hash of all files.

Note: Both files will be created in whatever directory you run the script from.

---

## How to run (step-by-step for new users)

1. Open PowerShell:
	 - Press Start, type `powershell`, and open "Windows PowerShell".

2. Change to the folder that contains the script (example below assumes the repository is in `D:\python-scripts`):

```powershell
cd D:\python-scripts
```

3. Run the script with Python. Basic usage:

```powershell
python .\rsync_clone.py C:\path\to\source C:\path\to\destination
```

- If either path contains spaces, wrap it in quotes:

```powershell
python .\rsync_clone.py "C:\My Files\source folder" "D:\Backups\My Files backup"
```

4. Helpful options:

- Dry-run (preview what would happen, no files are modified):

```powershell
python .\rsync_clone.py C:\source C:\backup --dry-run
```

- Verbose (more logging to console and `rsync_clone.log`):

```powershell
python .\rsync_clone.py C:\source C:\backup --verbose
```

- Dry-run + verbose:

```powershell
python .\rsync_clone.py C:\source C:\backup -n -v
```

The script prints a progress bar (unless `--verbose` is used), and a final summary including files copied, skipped, excluded, directories created, bytes copied, and errors.

---

## Examples (concrete)

1) Basic sync (overwrite changed files):

```powershell
python .\rsync_clone.py C:\Users\Alice\Documents C:\Backups\Documents_backup
```

2) Preview only (dry-run):

```powershell
python .\rsync_clone.py "C:\Work Projects" "D:\Backups\Work Projects" --dry-run
```

3) Verbose logging for debugging:

```powershell
python .\rsync_clone.py C:\source C:\backup --verbose
```

What you will see:
- During a dry-run: the script reports `Would copy` messages for files that would be copied.
- During a real run: the script reports `Copied` for each file (and writes to `rsync_clone.log`).

---

## What is excluded

The script automatically excludes common macOS metadata files and folders (e.g. `.DS_Store`, `__MACOSX`, `.Trashes`) so they are not copied. This is useful if your source contains macOS artifacts.

---

## Cache behavior

To speed up repeated runs, the script stores a cache file named `.rsync_cache.json` in the directory you run the script from. It stores size, mtime, and the file hash for files it has already scanned.

- To force the script to re-check all files (recompute all hashes), delete `.rsync_cache.json` and rerun.
- The script writes the cache when the run completes.

---

## Logs and troubleshooting

- Check `rsync_clone.log` for detailed messages and error traces.
- Common issues:
	- "Source path does not exist": check your `source` path spelling and that the path exists.
	- Permissions errors when writing to the destination: run PowerShell with sufficient permissions or choose a destination you can write to.
	- Unicode path issues: the script tries to handle Unicode paths safely and will fall back to safe string representations in logs if an encoding error occurs.

If you see errors, attach the relevant part of `rsync_clone.log` when asking for help.

---

## Using on Linux

Although the script was written with Windows usage examples, it is pure Python and works on Linux with a few small differences. This section explains how to run `rsync_clone.py` on a Linux system and important platform-specific notes for beginners.

1. Install Python 3 if you don't have it. On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y python3
```

On Fedora/CentOS/RHEL (modern systems):

```bash
sudo dnf install -y python3
```

2. Change to the folder that contains the script (example):

```bash
cd ~/projects/python-scripts
```

3. Make the script executable (optional) and run it:

```bash
chmod +x ./rsync_clone.py     # optional, allows running as ./rsync_clone.py
./rsync_clone.py /path/to/source /path/to/destination
# or explicitly with python3
python3 ./rsync_clone.py /path/to/source /path/to/destination
```

4. Use the same options as on Windows:

```bash
python3 ./rsync_clone.py /path/source /path/backup --dry-run
python3 ./rsync_clone.py /path/source /path/backup --verbose
```

Linux-specific notes and tips:

- Paths use forward slashes (`/`) and are case-sensitive. Make sure you type exact filenames and directory names.
- Permissions: if your source or destination requires elevated permissions, run the command with `sudo` (careful with `sudo` when using `--dry-run` vs a real run).
- File metadata: `shutil.copy2` (used by the script) copies file metadata such as modification time and permission bits on Unix-like systems; this helps preserve file timestamps and mode bits.
- Log and cache files (`rsync_clone.log` and `.rsync_cache.json`) are created in the current working directory. If you run the script from a different directory (for example, from a cron job), these files will be created there—use absolute paths or `cd` in your job to control where logs go.

Scheduling (cron) example (run daily at 02:30):

```bash
# Edit your crontab: 
crontab -e

# Add a line like this (adjust paths):
30 2 * * * /usr/bin/python3 /home/youruser/projects/python-scripts/rsync_clone.py /home/youruser/data /mnt/backup/data --dry-run >> /home/youruser/rsync_clone_cron.log 2>&1
```

When scheduling, prefer absolute paths for Python and for the script and provide a working directory or full paths for the log/cache so you can find them later.

Security tip: if the destination is a mounted network filesystem, ensure it is mounted with the proper options and that file ownership/permissions are what you expect before running a non-dry-run job.

---

## Safety suggestions

- Always run with `--dry-run` first for a new source/destination, to confirm what will happen.
- Keep an independent backup until you are confident the first run behaves as you expect.

---

## Scheduling on Windows (optional)

If you want to run the script regularly, you can use Windows Task Scheduler. In the Task Scheduler action, call Python with the script path and the two folder arguments. Make sure the account you use has permission to access both folders and to write logs in the working directory.

---

## Limitations & notes

- This script is a simplified, Windows-focused approach to synchronization. It is not a full replacement for `rsync` on Unix systems (does not handle remote sync over the network, ACLs, etc.).
- File comparison is done via SHA-256 hashing for correctness; hashing can be CPU- and I/O-intensive on very large numbers of files.
- The script copies files with `shutil.copy2` which attempts to preserve metadata like modification times.

---

## Next steps / improvements (ideas)

- Add an option to remove destination files that no longer exist in the source (mirroring).
- Add include/exclude patterns via command-line.
- Add optional multithreaded hashing for large datasets.

---

## Where to get help

Open an issue in the repository or contact the maintainer. When reporting problems, include:
- The exact command you ran
- Contents of `rsync_clone.log` (or the relevant portion)
- A short description of the source/destination layout and any special filesystem (network drive, cloud-mounted folder, etc.)

---

## License

The repository includes a `LICENSE` file—check it for license details.

---

Thanks for using `rsync_clone.py`! If you're new to Python and want help modifying the script or adding features (like pattern-based excludes), tell me what you'd like and I can add it.
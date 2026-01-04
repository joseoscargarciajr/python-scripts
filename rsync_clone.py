#!/usr/bin/env python3
"""
Windows rsync-like program for folder synchronization
Only overwrites files that have changed based on file hash comparison
"""

import os
import sys
import shutil
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Tuple, List
import json


class RsyncClone:
    def __init__(self, source: str, destination: str, dry_run: bool = False, verbose: bool = False):
        """
        Initialize the rsync clone
        
        Args:
            source: Source directory path
            destination: Destination directory path
            dry_run: If True, only show what would be done without actually doing it
            verbose: If True, show detailed output
        """
        self.source = Path(source).resolve()
        self.destination = Path(destination).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Mac hidden folders to exclude
        self.mac_exclusions = {'.DS_Store', '__MACOSX', '.AppleDouble', '.LSOverride', '.Spotlight-V100', '.Trashes', '.fseventsd'}
        
        # Statistics
        self.stats = {
            'files_checked': 0,
            'files_copied': 0,
            'files_skipped': 0,
            'files_excluded': 0,
            'directories_created': 0,
            'bytes_copied': 0,
            'errors': 0
        }
        
        # Progress tracking
        self.total_files = 0
        self.processed_files = 0
        
        # File cache for performance
        self.cache_file = Path('.rsync_cache.json')
        self.file_cache = self.load_cache()
        
        # Setup logging
        self.setup_logging()
        
        # Validate paths
        self.validate_paths()
    
    def load_cache(self) -> Dict:
        """Load file cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_cache(self):
        """Save file cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_cache, f, indent=2)
        except IOError:
            pass
    
    def get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for file"""
        return str(file_path.resolve())
    
    def is_file_cached_and_unchanged(self, file_path: Path) -> bool:
        """Check if file is in cache and unchanged"""
        cache_key = self.get_cache_key(file_path)
        if cache_key not in self.file_cache:
            return False
        
        try:
            stat = file_path.stat()
            cached = self.file_cache[cache_key]
            return (cached['size'] == stat.st_size and 
                   abs(cached['mtime'] - stat.st_mtime) <= 1.0)
        except (OSError, KeyError):
            return False
    
    def update_file_cache(self, file_path: Path, file_info: Dict):
        """Update cache with file information"""
        cache_key = self.get_cache_key(file_path)
        self.file_cache[cache_key] = {
            'size': file_info['size'],
            'mtime': file_info['mtime'],
            'hash': file_info['hash']
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
        
        # Create console handler with UTF-8 encoding
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Create file handler with UTF-8 encoding
        file_handler = logging.FileHandler('rsync_clone.log', mode='a', encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def safe_log(self, level, message, path=None):
        """Safe logging that handles Unicode paths"""
        try:
            if path:
                log_message = f"{message}: {path}"
            else:
                log_message = message
            getattr(self.logger, level)(log_message)
        except UnicodeEncodeError:
            # Fallback to safe representation
            if path:
                safe_path = path.name if hasattr(path, 'name') else str(path)
                log_message = f"{message}: {safe_path} (Unicode path)"
            else:
                log_message = message
            getattr(self.logger, level)(log_message)
    
    def validate_paths(self):
        """Validate source and destination paths"""
        if not self.source.exists():
            raise ValueError(f"Source path does not exist: {self.source}")
        
        if not self.source.is_dir():
            raise ValueError(f"Source path is not a directory: {self.source}")
        
        # Create destination if it doesn't exist
        if not self.destination.exists():
            if not self.dry_run:
                self.destination.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created destination directory: {self.destination}")
            else:
                self.logger.info(f"Would create destination directory: {self.destination}")
            self.stats['directories_created'] += 1
    
    def calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate SHA256 hash of a file
        
        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read at a time
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except (IOError, OSError) as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            self.stats['errors'] += 1
            return ""
    
    def get_file_info(self, file_path: Path) -> Dict:
        """
        Get file information including hash, size, and modification time
        Uses cache to avoid re-reading unchanged files
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            stat = file_path.stat()
            
            # Check if file is cached and unchanged
            if self.is_file_cached_and_unchanged(file_path):
                cache_key = self.get_cache_key(file_path)
                cached = self.file_cache[cache_key]
                return {
                    'path': file_path,
                    'size': cached['size'],
                    'mtime': cached['mtime'],
                    'hash': cached['hash']
                }
            
            # File changed or not cached, calculate hash
            file_hash = self.calculate_file_hash(file_path)
            file_info = {
                'path': file_path,
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'hash': file_hash
            }
            
            # Update cache
            self.update_file_cache(file_path, file_info)
            
            return file_info
            
        except (IOError, OSError) as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            self.stats['errors'] += 1
            return None
    
    def files_are_different(self, source_info: Dict, dest_info: Dict) -> bool:
        """
        Compare two files to determine if they are different
        
        Args:
            source_info: Source file information
            dest_info: Destination file information
            
        Returns:
            True if files are different, False if they are the same
        """
        if dest_info is None:
            return True
        
        # Compare by hash first (most reliable)
        if source_info['hash'] and dest_info['hash']:
            return source_info['hash'] != dest_info['hash']
        
        # Fallback to size and modification time
        if source_info['size'] != dest_info['size']:
            return True
        
        # Allow for small time differences due to filesystem precision
        time_diff = abs(source_info['mtime'] - dest_info['mtime'])
        return time_diff > 1.0  # More than 1 second difference
    
    def copy_file(self, source_path: Path, dest_path: Path) -> bool:
        """
        Copy a file from source to destination
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create destination directory if it doesn't exist
            dest_dir = dest_path.parent
            if not dest_dir.exists():
                if not self.dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created directory: {dest_dir}")
                else:
                    self.logger.debug(f"Would create directory: {dest_dir}")
                self.stats['directories_created'] += 1
            
            # Copy the file
            if not self.dry_run:
                shutil.copy2(source_path, dest_path)
                self.safe_log('info', "Copied", f"{source_path} -> {dest_path}")
            else:
                self.safe_log('info', "Would copy", f"{source_path} -> {dest_path}")
            
            # Update statistics
            file_size = source_path.stat().st_size
            self.stats['files_copied'] += 1
            self.stats['bytes_copied'] += file_size
            
            return True
            
        except (IOError, OSError) as e:
            self.logger.error(f"Error copying {source_path} to {dest_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def should_exclude_path(self, path: Path) -> bool:
        """Check if path should be excluded (Mac hidden folders/files)"""
        return any(part in self.mac_exclusions for part in path.parts)
    
    def count_files(self) -> int:
        """Count total files to process for progress tracking"""
        count = 0
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs if d not in self.mac_exclusions]
            for file_name in files:
                source_file = Path(root) / file_name
                if not self.should_exclude_path(source_file):
                    count += 1
        return count
    
    def show_progress(self, current_file: str = ""):
        """Display progress bar"""
        if self.total_files == 0:
            return
        
        progress = self.processed_files / self.total_files
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
        
        percent = progress * 100
        status = f"\r[{bar}] {percent:.1f}% ({self.processed_files}/{self.total_files})"
        
        if current_file:
            # Truncate filename if too long
            display_file = current_file if len(current_file) <= 50 else f"...{current_file[-47:]}"
            status += f" - {display_file}"
        
        print(status, end='', flush=True)
    
    def sync_directory(self):
        """Main synchronization method"""
        self.logger.info(f"Starting sync: {self.source} -> {self.destination}")
        self.logger.info(f"Dry run mode: {self.dry_run}")
        
        # Count total files for progress tracking
        print("Counting files...")
        self.total_files = self.count_files()
        print(f"Found {self.total_files:,} files to process\n")
        
        start_time = datetime.now()
        
        # Walk through source directory
        for root, dirs, files in os.walk(self.source):
            source_root = Path(root)
            # Calculate relative path from source
            rel_path = source_root.relative_to(self.source)
            dest_root = self.destination / rel_path
            
            # Skip Mac hidden directories
            dirs[:] = [d for d in dirs if d not in self.mac_exclusions]
            
            # Process files in current directory
            for file_name in files:
                source_file = source_root / file_name
                dest_file = dest_root / file_name
                
                # Skip Mac hidden files
                if self.should_exclude_path(source_file):
                    self.stats['files_excluded'] += 1
                    if self.verbose:
                        self.safe_log('debug', "Excluded (Mac hidden)", source_file)
                    continue
                
                self.stats['files_checked'] += 1
                self.processed_files += 1
                
                # Show progress
                if not self.verbose:
                    self.show_progress(str(source_file.name))
                
                if self.verbose:
                    self.safe_log('debug', "Checking", source_file)
                
                # Get file information
                source_info = self.get_file_info(source_file)
                if source_info is None:
                    continue
                
                dest_info = None
                if dest_file.exists():
                    dest_info = self.get_file_info(dest_file)
                
                # Check if files are different
                if self.files_are_different(source_info, dest_info):
                    self.copy_file(source_file, dest_file)
                else:
                    self.stats['files_skipped'] += 1
                    if self.verbose:
                        self.safe_log('debug', "Skipped (unchanged)", source_file)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Save cache and print summary
        self.save_cache()
        if not self.verbose:
            print()  # New line after progress bar
        self.print_summary(duration)
    
    def print_summary(self, duration):
        """Print synchronization summary"""
        print("\n" + "="*60)
        print("SYNCHRONIZATION SUMMARY")
        print("="*60)
        print(f"Source:      {self.source}")
        print(f"Destination: {self.destination}")
        print(f"Duration:    {duration}")
        print(f"Dry run:     {self.dry_run}")
        print("-"*60)
        print(f"Files checked:    {self.stats['files_checked']:,}")
        print(f"Files copied:     {self.stats['files_copied']:,}")
        print(f"Files skipped:    {self.stats['files_skipped']:,}")
        print(f"Files excluded:   {self.stats['files_excluded']:,}")
        print(f"Directories created: {self.stats['directories_created']:,}")
        print(f"Bytes copied:     {self.stats['bytes_copied']:,} ({self.format_bytes(self.stats['bytes_copied'])})")
        print(f"Errors:           {self.stats['errors']:,}")
        print("="*60)
        
        if self.stats['errors'] > 0:
            print(f"\nWARNING: {self.stats['errors']} errors occurred during synchronization!")
            print("Check the log file 'rsync_clone.log' for details.")
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Windows rsync-like program for folder synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rsync_clone.py C:\\source C:\\backup
  python rsync_clone.py C:\\source C:\\backup --dry-run
  python rsync_clone.py C:\\source C:\\backup --verbose
  python rsync_clone.py C:\\source C:\\backup --dry-run --verbose
        """
    )
    
    parser.add_argument('source', help='Source directory path')
    parser.add_argument('destination', help='Destination directory path')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be done without actually doing it')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    parser.add_argument('--version', action='version', version='rsync_clone 1.0.0')
    
    args = parser.parse_args()
    
    try:
        rsync = RsyncClone(
            source=args.source,
            destination=args.destination,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        rsync.sync_directory()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


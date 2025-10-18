import os
import hashlib
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger('Sortify.DuplicateFinder')


class DuplicateFinder:
    """Find and manage duplicate files based on content hash"""
    
    def __init__(self):
        self.hash_cache = {}
        self.chunk_size = 8192  # 8KB chunks for reading files
        
    def calculate_file_hash(self, file_path: Path, algorithm='md5') -> Optional[str]:
        """Calculate hash of file contents
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (md5, sha1, sha256)
            
        Returns:
            str: Hexadecimal hash string or None if error
        """
        try:
            # Check cache first
            cache_key = str(file_path)
            if cache_key in self.hash_cache:
                return self.hash_cache[cache_key]
            
            # Choose hash algorithm
            if algorithm == 'sha1':
                hasher = hashlib.sha1()
            elif algorithm == 'sha256':
                hasher = hashlib.sha256()
            else:
                hasher = hashlib.md5()
            
            # Read file in chunks to handle large files
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            
            file_hash = hasher.hexdigest()
            
            # Cache the result
            self.hash_cache[cache_key] = file_hash
            
            return file_hash
            
        except (IOError, OSError) as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def find_duplicates(self, directory: Path, recursive: bool = True, 
                       min_size: int = 0, extensions: Optional[List[str]] = None) -> Dict[str, List[Path]]:
        """Find duplicate files in a directory
        
        Args:
            directory: Directory to search
            recursive: Search subdirectories
            min_size: Minimum file size in bytes (skip smaller files)
            extensions: List of file extensions to check (e.g., ['.jpg', '.png'])
            
        Returns:
            Dict mapping hash to list of duplicate file paths
        """
        logger.info(f"Searching for duplicates in {directory} (recursive={recursive})")
        
        # First pass: Group files by size (quick pre-filter)
        size_groups = defaultdict(list)
        
        try:
            if recursive:
                files = directory.rglob('*')
            else:
                files = directory.glob('*')
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                # Skip files smaller than min_size
                try:
                    file_size = file_path.stat().st_size
                    if file_size < min_size:
                        continue
                except OSError:
                    continue
                
                # Filter by extension if specified
                if extensions and file_path.suffix.lower() not in extensions:
                    continue
                
                size_groups[file_size].append(file_path)
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            return {}
        
        # Second pass: Calculate hashes only for files with matching sizes
        hash_groups = defaultdict(list)
        
        for size, file_list in size_groups.items():
            # Skip if only one file with this size
            if len(file_list) < 2:
                continue
            
            logger.debug(f"Checking {len(file_list)} files of size {size} bytes")
            
            for file_path in file_list:
                file_hash = self.calculate_file_hash(file_path)
                if file_hash:
                    hash_groups[file_hash].append(file_path)
        
        # Filter to only keep groups with actual duplicates
        duplicates = {
            hash_val: paths 
            for hash_val, paths in hash_groups.items() 
            if len(paths) > 1
        }
        
        logger.info(f"Found {len(duplicates)} groups of duplicate files")
        
        return duplicates
    
    def find_duplicates_by_name(self, directory: Path, recursive: bool = True) -> Dict[str, List[Path]]:
        """Find files with duplicate names (regardless of content)
        
        Args:
            directory: Directory to search
            recursive: Search subdirectories
            
        Returns:
            Dict mapping filename to list of paths with that name
        """
        logger.info(f"Searching for duplicate names in {directory}")
        
        name_groups = defaultdict(list)
        
        try:
            if recursive:
                files = directory.rglob('*')
            else:
                files = directory.glob('*')
            
            for file_path in files:
                if file_path.is_file():
                    name_groups[file_path.name].append(file_path)
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            return {}
        
        # Filter to only keep groups with duplicates
        duplicates = {
            name: paths 
            for name, paths in name_groups.items() 
            if len(paths) > 1
        }
        
        logger.info(f"Found {len(duplicates)} duplicate filenames")
        
        return duplicates
    
    def get_duplicate_statistics(self, duplicates: Dict[str, List[Path]]) -> Dict:
        """Calculate statistics about duplicate files
        
        Args:
            duplicates: Dictionary from find_duplicates()
            
        Returns:
            Dictionary with statistics
        """
        total_files = sum(len(paths) for paths in duplicates.values())
        total_groups = len(duplicates)
        
        # Calculate wasted space (keeping one copy of each group)
        wasted_space = 0
        for paths in duplicates.values():
            if paths:
                try:
                    file_size = paths[0].stat().st_size
                    # Space wasted is (n-1) copies
                    wasted_space += file_size * (len(paths) - 1)
                except OSError:
                    pass
        
        return {
            'total_duplicate_files': total_files,
            'duplicate_groups': total_groups,
            'wasted_space_bytes': wasted_space,
            'wasted_space_mb': round(wasted_space / (1024 * 1024), 2),
            'wasted_space_gb': round(wasted_space / (1024 * 1024 * 1024), 2)
        }
    
    def delete_duplicates(self, duplicates: Dict[str, List[Path]], keep_first: bool = True,
                         dry_run: bool = True) -> Tuple[int, int]:
        """Delete duplicate files, keeping one copy
        
        Args:
            duplicates: Dictionary from find_duplicates()
            keep_first: Keep the first file in each group (by path)
            dry_run: If True, don't actually delete files
            
        Returns:
            Tuple of (files_deleted, errors)
        """
        deleted_count = 0
        error_count = 0
        
        for file_hash, paths in duplicates.items():
            if len(paths) < 2:
                continue
            
            # Sort paths to ensure consistent behavior
            sorted_paths = sorted(paths, key=lambda p: str(p))
            
            # Keep first or last based on keep_first parameter
            if keep_first:
                to_keep = sorted_paths[0]
                to_delete = sorted_paths[1:]
            else:
                to_keep = sorted_paths[-1]
                to_delete = sorted_paths[:-1]
            
            logger.info(f"Keeping {to_keep}")
            
            for file_path in to_delete:
                try:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete {file_path}")
                    else:
                        file_path.unlink()
                        logger.info(f"Deleted {file_path}")
                    
                    deleted_count += 1
                    
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
                    error_count += 1
        
        if dry_run:
            logger.info(f"Dry run complete: {deleted_count} files would be deleted")
        else:
            logger.info(f"Deleted {deleted_count} duplicate files with {error_count} errors")
        
        return deleted_count, error_count
    
    def clear_cache(self):
        """Clear the hash cache"""
        self.hash_cache.clear()
        logger.info("Hash cache cleared")

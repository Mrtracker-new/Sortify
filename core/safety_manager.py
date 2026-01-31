import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger('Sortify.SafetyManager')

class SafetyManager:
    """Manages safety features for file operations including confirmations and backups"""
    
    def __init__(self, data_dir=None, config=None):
        """
        Initialize SafetyManager
        
        Args:
            data_dir (Path): Directory for storing safety-related data
            config (dict): Configuration options for safety features
        """
        self.data_dir = data_dir or Path.home() / '.sortify' / 'safety'
        self.backup_dir = self.data_dir / 'backups'
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.config = {
            'enable_confirmations': False,
            'enable_backups': False,
            'backup_retention_days': 7,
            'confirm_move': True,
            'confirm_delete': True,
            'confirm_batch': True,
            'skip_confirmations': False  # For --yes flag support
        }
        
        # Update with user config
        if config:
            self.config.update(config)
        
        logger.info(f"SafetyManager initialized with backup dir: {self.backup_dir}")
    
    def confirm_operation(self, operation_type, file_path, parent=None):
        """
        Show confirmation dialog for file operation
        
        Args:
            operation_type (str): Type of operation ('move', 'copy', 'delete', 'rename')
            file_path (str or Path): Path to the file
            parent (QWidget): Parent widget for the dialog
            
        Returns:
            bool: True if user confirmed, False otherwise
        """
        # Skip confirmation if skip_confirmations flag is set (--yes flag)
        if self.config.get('skip_confirmations', False):
            return True
        
        # Skip confirmation if disabled in config
        if not self.config.get('enable_confirmations', False):
            return True
        
        # Check specific operation confirmation settings
        confirm_key = f'confirm_{operation_type}'
        if not self.config.get(confirm_key, True):
            return True
        
        file_path = Path(file_path)
        file_name = file_path.name
        
        # Create confirmation message
        messages = {
            'move': f"Are you sure you want to move '{file_name}'?",
            'copy': f"Are you sure you want to copy '{file_name}'?",
            'delete': f"⚠️ Are you sure you want to delete '{file_name}'?\n\nThis action cannot be undone!",
            'rename': f"Are you sure you want to rename '{file_name}'?",
            'batch': f"Are you sure you want to perform this operation on multiple files?"
        }
        
        message = messages.get(operation_type, f"Are you sure you want to perform this operation on '{file_name}'?")
        
        # Show confirmation dialog
        response = QMessageBox.question(
            parent,
            f"Confirm {operation_type.title()}",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )
        
        return response == QMessageBox.StandardButton.Yes
    
    def create_backup(self, file_path):
        """
        Create a backup copy of a file before performing operations
        
        Args:
            file_path (str or Path): Path to the file to backup
            
        Returns:
            Path: Path to the backup file, or None if backup failed
        """
        if not self.config.get('enable_backups', False):
            return None
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.warning(f"Cannot backup non-existent file: {file_path}")
                return None
            
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Create backup
            shutil.copy2(str(file_path), str(backup_path))
            logger.info(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def cleanup_old_backups(self, days=None):
        """
        Remove backup files older than specified days
        
        Args:
            days (int): Number of days to retain backups (default from config)
            
        Returns:
            tuple: (number of files deleted, total space freed in bytes)
        """
        days = days or self.config.get('backup_retention_days', 7)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = 0
        space_freed = 0
        
        try:
            for backup_file in self.backup_dir.iterdir():
                if backup_file.is_file():
                    # Get file modification time
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        deleted_count += 1
                        space_freed += file_size
                        logger.info(f"Deleted old backup: {backup_file}")
            
            if deleted_count > 0:
                logger.info(f"Cleanup complete: Deleted {deleted_count} backups, freed {space_freed / (1024*1024):.2f} MB")
            
            return deleted_count, space_freed
            
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            return deleted_count, space_freed
    
    def verify_undo_possible(self, original_path, new_path):
        """
        Verify if an undo operation is safe to perform
        
        Args:
            original_path (str or Path): Original file location
            new_path (str or Path): Current file location
            
        Returns:
            tuple: (bool: is_safe, str: reason/error message)
        """
        try:
            original_path = Path(original_path)
            new_path = Path(new_path)
            
            # Check if file exists at new location
            if not new_path.exists():
                return False, f"File no longer exists at {new_path}"
            
            # Check if original directory exists
            if not original_path.parent.exists():
                return False, f"Original directory no longer exists: {original_path.parent}"
            
            # Check if a file already exists at original location
            if original_path.exists():
                return False, f"A file already exists at original location: {original_path}"
            
            # Check write permissions on original directory
            if not os.access(original_path.parent, os.W_OK):
                return False, f"No write permission for directory: {original_path.parent}"
            
            # All checks passed
            return True, "Undo operation is safe"
            
        except Exception as e:
            return False, f"Error verifying undo: {str(e)}"
    
    def get_backup_info(self):
        """
        Get information about current backups
        
        Returns:
            dict: Backup statistics including count, total size, oldest and newest
        """
        try:
            backups = list(self.backup_dir.iterdir())
            
            if not backups:
                return {
                    'count': 0,
                    'total_size': 0,
                    'oldest': None,
                    'newest': None
                }
            
            total_size = sum(b.stat().st_size for b in backups if b.is_file())
            dates = [datetime.fromtimestamp(b.stat().st_mtime) for b in backups if b.is_file()]
            
            return {
                'count': len(backups),
                'total_size': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'oldest': min(dates) if dates else None,
                'newest': max(dates) if dates else None,
                'backup_dir': str(self.backup_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return {
                'count': 0,
                'total_size': 0,
                'error': str(e)
            }
    
    def update_config(self, new_config):
        """
        Update safety configuration
        
        Args:
            new_config (dict): Dictionary of configuration updates
        """
        self.config.update(new_config)
        logger.info(f"Updated safety configuration: {new_config}")
    
    def get_config(self):
        """Get current safety configuration"""
        return self.config.copy()

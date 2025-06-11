import logging
import re
from pathlib import Path
import datetime

class CommandParser:
    """Class for parsing natural language commands for file operations"""
    
    def __init__(self):
        """Initialize the command parser"""
        self.commands = {
            'move': self._parse_move_command,
            'copy': self._parse_copy_command,
            'organize': self._parse_organize_command,
            'sort': self._parse_sort_command,
            'find': self._parse_find_command,
            'search': self._parse_find_command,  # Alias for find
            'delete': self._parse_delete_command,
            'rename': self._parse_rename_command
        }
        
        self.time_patterns = {
            'today': self._get_today,
            'yesterday': self._get_yesterday,
            'last week': self._get_last_week,
            'last month': self._get_last_month,
            r'older than (\d+) days': self._get_older_than_days
        }
        
        logging.info("CommandParser initialized")
    
    def parse_command(self, command_text):
        """Parse a natural language command
        
        Args:
            command_text: The natural language command text
            
        Returns:
            dict: Parsed command with action and parameters
        """
        command_text = command_text.lower().strip()
        
        # Try to identify the command type
        for cmd_type, parser in self.commands.items():
            if cmd_type in command_text:
                return parser(command_text)
        
        # If no command type is found
        return {
            'action': 'unknown',
            'error': 'Could not understand command. Please try again with a different wording.'
        }
    
    def _parse_move_command(self, command_text):
        """Parse a move command
        
        Example: "Move all PDFs to Archive folder"
        """
        result = {'action': 'move'}
        
        # Try to extract file type
        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types
        
        # Try to extract time constraints
        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint
        
        # Try to extract destination
        destination = self._extract_destination(command_text)
        if destination:
            result['destination'] = destination
        else:
            result['error'] = 'No destination folder specified'
        
        return result
    
    def _parse_copy_command(self, command_text):
        """Parse a copy command
        
        Example: "Copy all images to Backup folder"
        """
        # Similar to move but with different action
        result = self._parse_move_command(command_text)
        result['action'] = 'copy'
        return result
    
    def _parse_organize_command(self, command_text):
        """Parse an organize command
        
        Example: "Organize Downloads folder"
        """
        result = {'action': 'organize'}
        
        # Try to extract source folder
        source = self._extract_source(command_text)
        if source:
            result['source'] = source
        
        # Try to extract organization method
        if 'by type' in command_text:
            result['method'] = 'type'
        elif 'by date' in command_text:
            result['method'] = 'date'
        elif 'by size' in command_text:
            result['method'] = 'size'
        else:
            result['method'] = 'type'  # Default
        
        return result
    
    def _parse_sort_command(self, command_text):
        """Parse a sort command (alias for organize)"""
        result = self._parse_organize_command(command_text)
        result['action'] = 'sort'
        return result
    
    def _parse_find_command(self, command_text):
        """Parse a find/search command
        
        Example: "Find all documents modified last week"
        """
        result = {'action': 'find'}
        
        # Try to extract file type
        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types
        
        # Try to extract time constraints
        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint
        
        # Try to extract search location
        source = self._extract_source(command_text)
        if source:
            result['source'] = source
        
        return result
    
    def _parse_delete_command(self, command_text):
        """Parse a delete command
        
        Example: "Delete temporary files older than 30 days"
        """
        result = {'action': 'delete'}
        
        # Try to extract file type
        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types
        else:
            result['error'] = 'No file types specified for deletion'
            return result
        
        # Try to extract time constraints (required for safety)
        time_constraint = self._extract_time_constraint(command_text)
        if time_constraint:
            result['time_constraint'] = time_constraint
        else:
            result['error'] = 'Time constraint required for deletion commands'
        
        return result
    
    def _parse_rename_command(self, command_text):
        """Parse a rename command
        
        Example: "Rename all screenshots to include date"
        """
        result = {'action': 'rename'}
        
        # Try to extract file type
        file_types = self._extract_file_types(command_text)
        if file_types:
            result['file_types'] = file_types
        
        # Try to extract rename pattern
        if 'include date' in command_text:
            result['pattern'] = 'date'
        elif 'sequential' in command_text:
            result['pattern'] = 'sequential'
        elif 'lowercase' in command_text:
            result['pattern'] = 'lowercase'
        elif 'uppercase' in command_text:
            result['pattern'] = 'uppercase'
        else:
            result['error'] = 'No rename pattern specified'
        
        return result
    
    def _extract_file_types(self, command_text):
        """Extract file types from command text"""
        file_types = []
        
        # Common file type keywords
        type_keywords = {
            'pdfs': '.pdf',
            'pdf': '.pdf',
            'documents': ['doc', 'docx', 'pdf', 'txt'],
            'document': ['doc', 'docx', 'pdf', 'txt'],
            'images': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'photos': ['jpg', 'jpeg', 'png'],
            'photo': ['jpg', 'jpeg', 'png'],
            'videos': ['mp4', 'avi', 'mov', 'mkv'],
            'video': ['mp4', 'avi', 'mov', 'mkv'],
            'music': ['mp3', 'wav', 'flac', 'ogg'],
            'audio': ['mp3', 'wav', 'flac', 'ogg'],
            'archives': ['zip', 'rar', '7z', 'tar', 'gz'],
            'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
            'executables': ['exe', 'msi', 'app'],
            'executable': ['exe', 'msi', 'app']
        }
        
        for keyword, extensions in type_keywords.items():
            if keyword in command_text:
                if isinstance(extensions, list):
                    file_types.extend(extensions)
                else:
                    file_types.append(extensions)
        
        # Look for specific extensions
        ext_matches = re.findall(r'\.([a-zA-Z0-9]+)', command_text)
        if ext_matches:
            file_types.extend(ext_matches)
        
        return list(set(file_types)) if file_types else None
    
    def _extract_time_constraint(self, command_text):
        """Extract time constraints from command text"""
        for pattern, time_func in self.time_patterns.items():
            match = re.search(pattern, command_text)
            if match:
                if len(match.groups()) > 0:
                    # Pattern with capture group like "older than X days"
                    return time_func(int(match.group(1)))
                else:
                    # Simple pattern like "today"
                    return time_func()
        
        return None
    
    def _extract_destination(self, command_text):
        """Extract destination folder from command text"""
        # Look for "to X folder" pattern
        match = re.search(r'to\s+([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()
        
        # Look for "to X directory" pattern
        match = re.search(r'to\s+([\w\s]+)\s+directory', command_text)
        if match:
            return match.group(1).strip()
        
        # Look for "to X" pattern at the end
        match = re.search(r'to\s+([\w\s]+)$', command_text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_source(self, command_text):
        """Extract source folder from command text"""
        # Look for "in X folder" pattern
        match = re.search(r'in\s+([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()
        
        # Look for "from X folder" pattern
        match = re.search(r'from\s+([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()
        
        # Look for "X folder" pattern at the beginning
        match = re.search(r'^([\w\s]+)\s+folder', command_text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _get_today(self):
        """Get today's date constraint"""
        today = datetime.date.today()
        return {
            'type': 'date',
            'operator': '==',
            'value': today
        }
    
    def _get_yesterday(self):
        """Get yesterday's date constraint"""
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        return {
            'type': 'date',
            'operator': '==',
            'value': yesterday
        }
    
    def _get_last_week(self):
        """Get last week's date constraint"""
        one_week_ago = datetime.date.today() - datetime.timedelta(days=7)
        return {
            'type': 'date',
            'operator': '>',
            'value': one_week_ago
        }
    
    def _get_last_month(self):
        """Get last month's date constraint"""
        one_month_ago = datetime.date.today() - datetime.timedelta(days=30)
        return {
            'type': 'date',
            'operator': '>',
            'value': one_month_ago
        }
    
    def _get_older_than_days(self, days):
        """Get date constraint for files older than X days"""
        x_days_ago = datetime.date.today() - datetime.timedelta(days=days)
        return {
            'type': 'date',
            'operator': '<',
            'value': x_days_ago
        }
    
    def execute_command(self, parsed_command, file_ops):
        """Execute a parsed command using the file operations
        
        Args:
            parsed_command: The parsed command dictionary
            file_ops: FileOperations instance
            
        Returns:
            tuple: (success, message)
        """
        try:
            action = parsed_command.get('action')
            
            if action == 'move':
                return self._execute_move_command(parsed_command, file_ops)
            elif action == 'copy':
                return self._execute_copy_command(parsed_command, file_ops)
            elif action in ['organize', 'sort']:
                return self._execute_organize_command(parsed_command, file_ops)
            elif action == 'find':
                return self._execute_find_command(parsed_command, file_ops)
            elif action == 'delete':
                return self._execute_delete_command(parsed_command, file_ops)
            elif action == 'rename':
                return self._execute_rename_command(parsed_command, file_ops)
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            logging.error(f"Error executing command: {e}")
            return False, f"Error: {str(e)}"
    
    def _execute_move_command(self, command, file_ops):
        """Execute a move command"""
        # Get destination folder
        destination = command.get('destination')
        if not destination:
            return False, "No destination specified"
            
        # Create destination path
        dest_path = Path(file_ops.base_dir) / destination
        dest_path.mkdir(exist_ok=True, parents=True)
        
        # Get files to move based on file types and time constraints
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        
        if not files:
            return False, "No matching files found"
            
        # Move files
        moved_count = 0
        for file in files:
            try:
                file_ops.move_file(file, str(dest_path))
                moved_count += 1
            except Exception as e:
                logging.error(f"Error moving file {file}: {e}")
                
        return True, f"Moved {moved_count} files to {destination}"
    
    def _execute_copy_command(self, command, file_ops):
        """Execute a copy command"""
        # Similar to move but copy instead
        destination = command.get('destination')
        if not destination:
            return False, "No destination specified"
            
        dest_path = Path(file_ops.base_dir) / destination
        dest_path.mkdir(exist_ok=True, parents=True)
        
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        
        if not files:
            return False, "No matching files found"
            
        copied_count = 0
        for file in files:
            try:
                file_ops.copy_file(file, str(dest_path))
                copied_count += 1
            except Exception as e:
                logging.error(f"Error copying file {file}: {e}")
                
        return True, f"Copied {copied_count} files to {destination}"
    
    def _execute_organize_command(self, command, file_ops):
        """Execute an organize command"""
        source = command.get('source')
        method = command.get('method', 'type')
        
        if not source:
            return False, "No source folder specified"
            
        source_path = Path(file_ops.base_dir) / source
        if not source_path.exists() or not source_path.is_dir():
            return False, f"Source folder '{source}' not found"
            
        files = [f for f in source_path.glob('**/*') if f.is_file()]
        
        if not files:
            return False, "No files found in source folder"
            
        organized_count = 0
        for file in files:
            try:
                if method == 'type':
                    category = file_ops.categorize_file(file)
                elif method == 'date':
                    # Organize by date (YYYY-MM)
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                    category = f"By Date/{mtime.strftime('%Y-%m')}"
                elif method == 'size':
                    # Organize by size
                    size_kb = file.stat().st_size / 1024
                    if size_kb < 100:
                        category = "By Size/Small (< 100KB)"
                    elif size_kb < 1024:
                        category = "By Size/Medium (100KB - 1MB)"
                    elif size_kb < 10240:
                        category = "By Size/Large (1MB - 10MB)"
                    else:
                        category = "By Size/Very Large (> 10MB)"
                else:
                    category = "Unsorted"
                    
                file_ops.move_file(file, category)
                organized_count += 1
            except Exception as e:
                logging.error(f"Error organizing file {file}: {e}")
                
        return True, f"Organized {organized_count} files from {source}"
    
    def _execute_find_command(self, command, file_ops):
        """Execute a find command"""
        # This would typically return results rather than moving files
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        
        if not files:
            return False, "No matching files found"
            
        # For now, just return the count and some example files
        examples = [f.name for f in files[:5]]
        examples_str = ", ".join(examples)
        
        if len(files) > 5:
            examples_str += f" and {len(files) - 5} more"
            
        return True, f"Found {len(files)} files: {examples_str}"
    
    def _execute_delete_command(self, command, file_ops):
        """Execute a delete command"""
        # This is potentially dangerous, so we require time constraints
        if not command.get('time_constraint'):
            return False, "Time constraint required for deletion commands"
            
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        
        if not files:
            return False, "No matching files found"
            
        # For safety, we'll just return what would be deleted
        examples = [f.name for f in files[:5]]
        examples_str = ", ".join(examples)
        
        if len(files) > 5:
            examples_str += f" and {len(files) - 5} more"
            
        return True, f"Would delete {len(files)} files: {examples_str}"
    
    def _execute_rename_command(self, command, file_ops):
        """Execute a rename command"""
        pattern = command.get('pattern')
        if not pattern:
            return False, "No rename pattern specified"
            
        files = self._get_files_matching_criteria(command, file_ops.base_dir)
        
        if not files:
            return False, "No matching files found"
            
        renamed_count = 0
        for file in files:
            try:
                if pattern == 'date':
                    # Add date to filename
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
                    date_str = mtime.strftime('%Y-%m-%d')
                    new_name = f"{file.stem}_{date_str}{file.suffix}"
                elif pattern == 'sequential':
                    # Add sequential number
                    new_name = f"{file.stem}_{renamed_count+1:03d}{file.suffix}"
                elif pattern == 'lowercase':
                    # Convert to lowercase
                    new_name = file.name.lower()
                elif pattern == 'uppercase':
                    # Convert to uppercase
                    new_name = file.name.upper()
                else:
                    continue
                    
                new_path = file.parent / new_name
                file.rename(new_path)
                renamed_count += 1
            except Exception as e:
                logging.error(f"Error renaming file {file}: {e}")
                
        return True, f"Renamed {renamed_count} files"
    
    def _get_files_matching_criteria(self, command, base_dir):
        """Get files matching the criteria in the command"""
        # Start with all files in the base directory
        all_files = list(Path(base_dir).glob('**/*'))
        matching_files = [f for f in all_files if f.is_file()]
        
        # Filter by file types if specified
        file_types = command.get('file_types')
        if file_types:
            matching_files = [f for f in matching_files if any(f.name.lower().endswith(f'.{ext.lower()}') for ext in file_types)]
        
        # Filter by time constraint if specified
        time_constraint = command.get('time_constraint')
        if time_constraint:
            operator = time_constraint.get('operator')
            value = time_constraint.get('value')
            
            filtered_files = []
            for file in matching_files:
                try:
                    mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime).date()
                    
                    if operator == '==' and mtime == value:
                        filtered_files.append(file)
                    elif operator == '>' and mtime > value:
                        filtered_files.append(file)
                    elif operator == '<' and mtime < value:
                        filtered_files.append(file)
                except Exception as e:
                    logging.error(f"Error checking file time for {file}: {e}")
                    
            matching_files = filtered_files
        
        # Filter by source if specified
        source = command.get('source')
        if source:
            source_path = Path(base_dir) / source
            matching_files = [f for f in matching_files if source_path in f.parents or f.parent == source_path]
        
        return matching_files
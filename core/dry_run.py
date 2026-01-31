"""
Dry-run mode functionality for previewing file operations without executing them.
"""

from pathlib import Path
from typing import List, Dict, Any
from tabulate import tabulate


class DryRunManager:
    """Manages dry-run preview operations"""
    
    def __init__(self):
        """Initialize the dry-run manager"""
        self.planned_operations = []
    
    def add_operation(self, operation_type: str, source: Path, destination: Path, category: str = None):
        """
        Add a planned operation to the preview list
        
        Args:
            operation_type: Type of operation ('move', 'copy', 'rename', 'delete')
            source: Source file path
            destination: Destination file path
            category: Category/subcategory path (optional)
        """
        self.planned_operations.append({
            'operation': operation_type,
            'source': str(source),
            'destination': str(destination),
            'category': category or '',
            'filename': source.name
        })
    
    def clear_operations(self):
        """Clear all planned operations"""
        self.planned_operations = []
    
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get all planned operations"""
        return self.planned_operations
    
    def has_operations(self) -> bool:
        """Check if there are any planned operations"""
        return len(self.planned_operations) > 0
    
    def print_operations_table(self):
        """Print a formatted table of all planned operations"""
        if not self.has_operations():
            print("\n📋 No operations planned.")
            return
        
        print(f"\n📋 Dry-Run Preview - {len(self.planned_operations)} operations planned:")
        print("=" * 80)
        
        # Prepare table data
        table_data = []
        for op in self.planned_operations:
            operation_icon = {
                'move': '📦',
                'copy': '📄',
                'rename': '✏️',
                'delete': '🗑️'
            }.get(op['operation'], '📌')
            
            # Format the arrow
            arrow = '→'
            
            # Create row
            row = [
                f"{operation_icon} {op['operation'].upper()}",
                op['filename'],
                arrow,
                op['destination']
            ]
            table_data.append(row)
        
        # Print table
        headers = ['Operation', 'File', '', 'Destination']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        print("=" * 80)
        print(f"\n✨ Total: {len(self.planned_operations)} files would be processed")
        print("💡 These changes have NOT been applied (dry-run mode)")
        print("   Remove --dry-run flag to execute these operations.\n")
    
    def print_summary(self):
        """Print a summary of operations by type and category"""
        if not self.has_operations():
            return
        
        # Count by operation type
        ops_by_type = {}
        for op in self.planned_operations:
            op_type = op['operation']
            ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1
        
        # Count by category
        ops_by_category = {}
        for op in self.planned_operations:
            if op['category']:
                ops_by_category[op['category']] = ops_by_category.get(op['category'], 0) + 1
        
        print("\n📊 Summary by Operation Type:")
        for op_type, count in ops_by_type.items():
            print(f"  • {op_type.capitalize()}: {count} files")
        
        if ops_by_category:
            print("\n📁 Summary by Category:")
            for category, count in sorted(ops_by_category.items()):
                print(f"  • {category}: {count} files")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

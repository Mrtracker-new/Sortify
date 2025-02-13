import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .history import HistoryManager

class FileOperations:
    @staticmethod
    def setup_organization():
        """
        Prompt user for organization folder details and validate the path
        
        Returns:
            tuple: (base_path, folder_name) containing validated path and folder name
        """
        while True:
            try:
                print("\n" + "="*50)
                print("📂 File Organization Setup")
                print("="*50)
                
                # Get base path from user
                print("\n📍 Step 1: Choose Location")
                print("Where would you like to create your organization folder?")
                print("\nCommon locations:")
                print("  1. Desktop       (~/Desktop)")
                print("  2. Documents     (~/Documents)")
                print("  3. Custom Path   (e.g., D:/MyFiles)")
                print("  4. Root Drive    (C:/)")
                
                choice = input("\nEnter choice (1-4) or directly type your path: ").strip()
                
                # Handle numbered choices
                if choice in ['1', '2', '3', '4']:
                    if choice == '1':
                        base_path = os.path.expanduser("~/Desktop")
                    elif choice == '2':
                        base_path = os.path.expanduser("~/Documents")
                    elif choice == '3':
                        base_path = input("\nEnter your custom path: ").strip()
                    else:
                        base_path = "C:/"
                else:
                    base_path = choice if choice else "C:/"
                
                # Expand user path if using ~
                base_path = os.path.expanduser(base_path)
                
                # Get folder name
                print("\n📝 Step 2: Name Your Organization Folder")
                print("\nSuggested names:")
                print("  1. Organized Files")
                print("  2. My Files")
                print("  3. File System")
                print("  4. Custom Name")
                
                name_choice = input("\nEnter choice (1-4) or directly type your folder name: ").strip()
                
                if name_choice in ['1', '2', '3', '4']:
                    if name_choice == '1':
                        folder_name = "Organized Files"
                    elif name_choice == '2':
                        folder_name = "My Files"
                    elif name_choice == '3':
                        folder_name = "File System"
                    else:
                        folder_name = input("\nEnter your custom folder name: ").strip()
                else:
                    folder_name = name_choice if name_choice else "Organized Files"
                
                # Validate path
                full_path = Path(base_path) / folder_name
                
                # Check if folder exists
                if full_path.exists():
                    print("\n⚠️  Folder Already Exists")
                    response = input(f"Folder '{folder_name}' already exists at {base_path}. Use existing folder? (y/n): ").lower()
                    if response != 'y':
                        continue
                else:
                    # Test if we can create the directory
                    try:
                        full_path.mkdir(parents=True)
                        full_path.rmdir()  # Remove test directory
                    except PermissionError:
                        print(f"\n❌ Error: No permission to create folder at {base_path}")
                        print("Please choose a different location or run with appropriate permissions.")
                        continue
                    except Exception as e:
                        print(f"\n❌ Error: {str(e)}")
                        print("Please choose a different location.")
                        continue
                
                print("\n✅ Success!")
                print(f"Organization folder will be created at: {full_path}")
                print("="*50)
                return base_path, folder_name
                
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("Please try again.")

    def __init__(self, base_path=None, folder_name=None):
        """
        Initialize FileOperations with customizable base path and folder name
        
        Args:
            base_path (str or Path, optional): Base directory path. If None, will prompt user
            folder_name (str, optional): Name of the organization folder. If None, will prompt user
        """
        # If either parameter is None, run setup
        if base_path is None or folder_name is None:
            base_path, folder_name = self.setup_organization()
        
        self.base_dir = Path(base_path) / folder_name
        self.history = HistoryManager()  # Initialize history manager
        
        # Create the directory
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(
                f"Unable to create folder at {self.base_dir}. Please ensure you have "
                "appropriate permissions or choose a different location."
            )

        # Simplified categories with most common use cases
        self.categories = {
            'documents': ['word', 'pdf', 'text', 'ebooks'],
            'images': ['photos', 'screenshots', 'artwork'],
            'videos': ['movies', 'recordings', 'tutorials'],
            'audio': ['music', 'podcasts', 'recordings'],
            'code': ['python', 'javascript', 'web', 'data'],
            'archives': ['compressed', 'backups', 'installers'],
            'office': ['templates', 'spreadsheets', 'presentations'],
            'downloads': ['software', 'media', 'temporary'],
            'personal': ['documents', 'finance', 'records'],
            'misc': ['other']
        }

    def create_category_folders(self):
        """Create all category folders"""
        try:
            for category, subcategories in self.categories.items():
                category_path = self.base_dir / category
                category_path.mkdir(exist_ok=True)
                
                for subcategory in subcategories:
                    subcategory_path = category_path / subcategory
                    subcategory_path.mkdir(exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating category folders: {e}")
            return False

    def move_file(self, source_path, category_path):
        """Move file to appropriate category folder"""
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {source_path}")

            category, subcategory = category_path.split('/')
            dest_dir = self.base_dir / category / subcategory
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / source_path.name

            # Handle file name conflicts
            if dest_path.exists():
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{dest_path.stem}_{counter}{dest_path.suffix}"
                    counter += 1

            shutil.move(str(source_path), str(dest_path))
            self.history.log_operation(str(source_path), str(dest_path))
            return dest_path
        except Exception as e:
            self.history.log_operation(str(source_path), "failed", metadata={'error': str(e)})
            raise

    def rename_file(self, file_path, new_name=None, options=None):
        """
        Enhanced file renaming with multiple options
        
        Args:
            file_path (str): Path to the file
            new_name (str, optional): New name for the file
            options (dict, optional): Dictionary of renaming options:
                - add_date (bool): Add date prefix (default: False)
                - add_time (bool): Add time prefix (default: False)
                - date_format (str): Custom date format (default: "%Y%m%d")
                - case (str): 'lower', 'upper', 'title', or None
                - remove_spaces (bool): Replace spaces with underscores
                - add_sequence (bool): Add sequence number for similar files
                - custom_prefix (str): Add custom prefix
                - custom_suffix (str): Add custom suffix
                - remove_special_chars (bool): Remove special characters
        
        Returns:
            Path: New file path
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Default options
            default_options = {
                'add_date': False,
                'add_time': False,
                'date_format': "%Y%m%d",
                'case': None,
                'remove_spaces': False,
                'add_sequence': True,
                'custom_prefix': '',
                'custom_suffix': '',
                'remove_special_chars': False
            }

            # Update options with user provided values
            options = {**default_options, **(options or {})}

            # Start with original name or provided new name
            original_name = file_path.stem
            extension = file_path.suffix
            final_name = new_name if new_name else original_name

            # Apply text transformations
            if options['remove_special_chars']:
                final_name = ''.join(c for c in final_name if c.isalnum() or c in '- _')

            if options['remove_spaces']:
                final_name = final_name.replace(' ', '_')

            if options['case']:
                if options['case'] == 'lower':
                    final_name = final_name.lower()
                elif options['case'] == 'upper':
                    final_name = final_name.upper()
                elif options['case'] == 'title':
                    final_name = final_name.title()

            # Add date/time if requested
            prefix_parts = []
            
            if options['add_date'] or options['add_time']:
                if options['add_date'] and options['add_time']:
                    date_str = datetime.now().strftime(f"{options['date_format']}_%H%M%S")
                elif options['add_date']:
                    date_str = datetime.now().strftime(options['date_format'])
                else:
                    date_str = datetime.now().strftime("%H%M%S")
                prefix_parts.append(date_str)

            # Add custom prefix if provided
            if options['custom_prefix']:
                prefix_parts.append(options['custom_prefix'])

            # Combine prefix with name
            if prefix_parts:
                final_name = f"{('_'.join(prefix_parts))}_{final_name}"

            # Add custom suffix if provided
            if options['custom_suffix']:
                final_name = f"{final_name}_{options['custom_suffix']}"

            # Create new path
            new_path = file_path.parent / f"{final_name}{extension}"

            # Handle duplicates if needed
            if options['add_sequence'] and new_path.exists():
                counter = 1
                while new_path.exists():
                    sequence_name = f"{final_name}_{counter}{extension}"
                    new_path = file_path.parent / sequence_name
                    counter += 1

            # Perform the rename
            file_path.rename(new_path)

            # Log the operation with metadata
            metadata = {
                'original_name': str(file_path),
                'new_name': str(new_path),
                'options_used': options
            }
            self.history.log_operation(
                str(file_path),
                str(new_path),
                operation_type="rename",
                metadata=metadata
            )

            return new_path

        except Exception as e:
            error_msg = f"Error renaming file: {str(e)}"
            self.history.log_operation(
                str(file_path),
                "failed",
                operation_type="rename",
                metadata={'error': error_msg}
            )
            raise RuntimeError(error_msg)

    def batch_rename(self, file_paths, pattern=None, options=None):
        """
        Rename multiple files at once
        
        Args:
            file_paths (list): List of file paths to rename
            pattern (str, optional): Naming pattern with placeholders:
                {n} - sequential number
                {date} - current date
                {time} - current time
                {orig} - original filename
            options (dict, optional): Same options as rename_file
        
        Returns:
            dict: Mapping of original paths to new paths
        """
        results = {}
        
        try:
            for index, file_path in enumerate(file_paths, 1):
                if pattern:
                    # Replace placeholders in pattern
                    new_name = pattern.format(
                        n=index,
                        date=datetime.now().strftime("%Y%m%d"),
                        time=datetime.now().strftime("%H%M%S"),
                        orig=Path(file_path).stem
                    )
                    new_path = self.rename_file(file_path, new_name, options)
                else:
                    new_path = self.rename_file(file_path, None, options)
                
                results[str(file_path)] = str(new_path)
                
            return results
            
        except Exception as e:
            error_msg = f"Error in batch rename: {str(e)}"
            self.history.log_operation(
                "batch_rename",
                "failed",
                operation_type="batch_rename",
                metadata={'error': error_msg, 'files': file_paths}
            )
            raise RuntimeError(error_msg)

    def categorize_file(self, file_path):
        """
        Categorize a file based on its extension
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: category/subcategory path
        """
        file_ext = Path(file_path).suffix.lower().replace('.', '')
        
        # Extension to category mapping
        ext_mapping = {
            # Documents
            'pdf': 'documents/pdf',
            'doc': 'documents/word',
            'docx': 'documents/word',
            'txt': 'documents/text',
            'rtf': 'documents/text',
            'epub': 'documents/ebooks',
            'mobi': 'documents/ebooks',
            
            # Images
            'jpg': 'images/photos',
            'jpeg': 'images/photos',
            'png': 'images/photos',
            'gif': 'images/photos',
            'bmp': 'images/photos',
            'svg': 'images/artwork',
            'ai': 'images/artwork',
            'psd': 'images/artwork',
            
            # Videos
            'mp4': 'videos/movies',
            'avi': 'videos/movies',
            'mkv': 'videos/movies',
            'mov': 'videos/movies',
            'wmv': 'videos/movies',
            
            # Audio
            'mp3': 'audio/music',
            'wav': 'audio/music',
            'flac': 'audio/music',
            'm4a': 'audio/music',
            
            # Code
            'py': 'code/python',
            'js': 'code/javascript',
            'html': 'code/web',
            'css': 'code/web',
            'java': 'code/java',
            'cpp': 'code/cpp',
            'c': 'code/cpp',
            
            # Archives
            'zip': 'archives/compressed',
            'rar': 'archives/compressed',
            '7z': 'archives/compressed',
            'tar': 'archives/compressed',
            'gz': 'archives/compressed',
            
            # Office
            'xlsx': 'office/spreadsheets',
            'xls': 'office/spreadsheets',
            'pptx': 'office/presentations',
            'ppt': 'office/presentations',
            
            # Downloads
            'exe': 'downloads/software',
            'msi': 'downloads/software',
            'dmg': 'downloads/software',
            'iso': 'downloads/software',
        }
        
        # Get category path or use misc if extension not found
        category_path = ext_mapping.get(file_ext, 'misc/other')
        
        return category_path

class FileOrganizationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Organization System")
        self.root.geometry("600x400")
        self.root.configure(bg="#f0f0f0")
        
        self.file_ops = None
        self.setup_ui()

    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Setup section
        ttk.Label(main_frame, text="File Organization Setup", font=('Helvetica', 16, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)

        # Base path selection
        ttk.Label(main_frame, text="Select Base Location:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(main_frame, textvariable=self.path_var, width=40)
        path_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_path).grid(row=1, column=2, padx=5)

        # Folder name
        ttk.Label(main_frame, text="Organization Folder Name:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.folder_var = tk.StringVar(value="Organized Files")
        ttk.Entry(main_frame, textvariable=self.folder_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Create button
        ttk.Button(main_frame, text="Create Organization System", command=self.create_system).grid(row=3, column=0, columnspan=3, pady=20)

        # Status section
        self.status_var = tk.StringVar()
        ttk.Label(main_frame, textvariable=self.status_var, wraplength=500).grid(row=4, column=0, columnspan=3, pady=10)

        # File organization section (initially hidden)
        self.org_frame = ttk.Frame(main_frame)
        self.org_frame.grid(row=5, column=0, columnspan=3, pady=10)
        self.org_frame.grid_remove()

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def create_system(self):
        try:
            base_path = self.path_var.get()
            folder_name = self.folder_var.get()

            if not base_path or not folder_name:
                messagebox.showerror("Error", "Please provide both base path and folder name")
                return

            self.file_ops = FileOperations(base_path, folder_name)
            self.file_ops.create_category_folders()
            
            self.status_var.set(f"✅ Successfully created organization system at:\n{self.file_ops.base_dir}")
            self.show_organization_options()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_organization_options(self):
        # Clear existing widgets
        for widget in self.org_frame.winfo_children():
            widget.destroy()

        self.org_frame.grid()

        # Add file organization options
        ttk.Label(self.org_frame, text="Organize Files", font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Button(self.org_frame, text="Select Files to Organize", command=self.organize_files).grid(row=1, column=0, pady=5)
        ttk.Button(self.org_frame, text="View Categories", command=self.view_categories).grid(row=1, column=1, pady=5)

    def organize_files(self):
        files = filedialog.askopenfilenames()
        if files:
            for file in files:
                self.show_category_dialog(file)

    def view_categories(self):
        category_window = tk.Toplevel(self.root)
        category_window.title("Available Categories")
        category_window.geometry("400x500")

        ttk.Label(category_window, text="Categories and Subcategories", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        for category, subcategories in self.file_ops.categories.items():
            ttk.Label(category_window, text=f"\n{category.title()}:", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
            for sub in subcategories:
                ttk.Label(category_window, text=f"  • {sub}").pack(anchor=tk.W)

    def show_category_dialog(self, file_path):
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose Category")
        dialog.geometry("300x400")

        ttk.Label(dialog, text=f"Choose category for:\n{os.path.basename(file_path)}").pack(pady=10)

        category_var = tk.StringVar()
        subcategory_var = tk.StringVar()

        # Category selection
        category_frame = ttk.Frame(dialog)
        category_frame.pack(fill=tk.X, padx=10)
        
        for category in self.file_ops.categories.keys():
            ttk.Radiobutton(category_frame, text=category.title(), value=category, 
                           variable=category_var, command=lambda: self.update_subcategories(subcategory_list, category_var.get())
                           ).pack(anchor=tk.W)

        # Subcategory selection
        ttk.Label(dialog, text="Select Subcategory:").pack(pady=5)
        subcategory_list = ttk.Combobox(dialog, textvariable=subcategory_var)
        subcategory_list.pack(pady=5)

        def move_file():
            if category_var.get() and subcategory_var.get():
                try:
                    self.file_ops.move_file(file_path, f"{category_var.get()}/{subcategory_var.get()}")
                    messagebox.showinfo("Success", "File moved successfully!")
                    dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
            else:
                messagebox.showerror("Error", "Please select both category and subcategory")

        ttk.Button(dialog, text="Move File", command=move_file).pack(pady=10)

    def update_subcategories(self, subcategory_list, category):
        subcategory_list['values'] = self.file_ops.categories.get(category, [])
        subcategory_list.set('')

    def run(self):
        self.root.mainloop()

# Usage
if __name__ == "__main__":
    app = FileOrganizationApp()
    app.run()
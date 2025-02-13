from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLineEdit, QLabel, QFileDialog, QListWidget,
                           QProgressBar, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from core.file_operations import FileOperations
from pathlib import Path
import logging
import shutil
import os

class ProcessingThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, files, file_ops):
        super().__init__()
        self.files = files
        self.file_ops = file_ops

    def run(self):
        try:
            total = len(self.files)
            for i, file in enumerate(self.files, 1):
                # Process each file
                self.file_ops.move_file(file, self.file_ops.categorize_file(file))
                self.progress.emit(int((i / total) * 100))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, history_manager):
        super().__init__()
        self.history_manager = history_manager
        self.selected_files = []
        
        # detailed organization categories
        self.categories = {
            'Images': {
                'Photos': ['.jpg', '.jpeg', '.heic', '.jfif'],
                'PNG': ['.png'],
                'Graphics': ['.gif', '.bmp', '.webp', '.ico'],
                'RAW': ['.raw', '.cr2', '.nef', '.arw', '.dng'],
                'Design': ['.psd', '.ai', '.sketch', '.xcf']
            },
            'Documents': {
                'PDF': ['.pdf'],
                'Word': ['.doc', '.docx', '.docm', '.dot', '.dotx', '.rtf'],
                'Text': ['.txt', '.md', '.log', '.tex'],
                'Spreadsheets': ['.xlsx', '.xls', '.csv', '.xlsm', '.ods'],
                'Presentations': ['.ppt', '.pptx', '.pps', '.ppsx', '.odp'],
                'eBooks': ['.epub', '.mobi', '.azw', '.azw3']
            },
            'Audio': {
                'Music': ['.mp3', '.m4a', '.aac', '.ogg'],
                'Lossless': ['.flac', '.wav', '.alac', '.aiff'],
                'Playlists': ['.m3u', '.pls', '.wpl'],
                'Voice': ['.opus', '.wma', '.voc']
            },
            'Video': {
                'Movies': ['.mp4', '.mov', '.m4v'],
                'TV': ['.mkv', '.avi', '.mpg', '.mpeg'],
                'Mobile': ['.3gp', '.3g2'],
                'Web': ['.webm', '.flv']
            },
            'Archives': {
                'ZIP': ['.zip', '.7z'],
                'RAR': ['.rar'],
                'Disk': ['.iso', '.dmg'],
                'Compressed': ['.gz', '.bz2', '.xz', '.tar', '.tgz']
            },
            'Code': {
                'Python': ['.py', '.pyw', '.ipynb'],
                'Web': ['.html', '.css', '.js', '.php', '.jsx', '.tsx'],
                'Java': ['.java', '.jar', '.class'],
                'C_CPP': ['.c', '.cpp', '.h', '.hpp'],
                'Scripts': ['.sh', '.bash', '.ps1', '.bat', '.cmd'],
                'Data': ['.json', '.xml', '.yaml', '.yml', '.csv']
            },
            'Applications': {
                'Windows': ['.exe', '.msi', '.dll'],
                'Mac': ['.app', '.dmg', '.pkg'],
                'Linux': ['.deb', '.rpm', '.AppImage'],
                'Mobile': ['.apk', '.ipa']
            },
            'Design': {
                'Vector': ['.svg', '.eps', '.ai'],
                'CAD': ['.dwg', '.dxf', '.stl'],
                '3D': ['.obj', '.fbx', '.blend', '.3ds'],
                'Fonts': ['.ttf', '.otf', '.woff', '.woff2']
            }
        }
        
        
        self.flat_categories = {}
        for main_cat, subcats in self.categories.items():
            for subcat, extensions in subcats.items():
                cat_name = f"{main_cat}/{subcat}"
                self.flat_categories[cat_name] = extensions
        
        # UI
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("File Organizer")
        self.setMinimumSize(800, 600)
        
        # Set window icon
        self.setWindowIcon(QIcon(":/icons/app_icon.png"))

        # central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header with search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_input.setMinimumHeight(40)
        search_button = QPushButton("Search")
        search_button.setMinimumHeight(40)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)

        # Action buttons
        button_layout = QHBoxLayout()
        self.select_button = QPushButton("Select Files")
        self.move_button = QPushButton("Move Files")
        self.undo_button = QPushButton("Undo Last Action")
        
        for button in [self.select_button, self.move_button, self.undo_button]:
            button.setMinimumHeight(40)
            button_layout.addWidget(button)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)

        # History section
        history_label = QLabel("Recent Actions")
        history_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
        self.history_list = QListWidget()

        # organization options
        organize_layout = QHBoxLayout()
        self.organize_combo = QComboBox()
        self.organize_combo.addItems(['All Categories'] + list(self.flat_categories.keys()))
        organize_button = QPushButton("Organize Files")
        organize_layout.addWidget(QLabel("Organize by:"))
        organize_layout.addWidget(self.organize_combo)
        organize_layout.addWidget(organize_button)

        # all widgets to main layout
        main_layout.addLayout(search_layout)
        main_layout.addLayout(button_layout)
        main_layout.addLayout(organize_layout)
        main_layout.addWidget(self.file_list)
        main_layout.addWidget(history_label)
        main_layout.addWidget(self.history_list)

        # Connect signals
        self.select_button.clicked.connect(self.select_files)
        self.move_button.clicked.connect(self.move_files)
        self.undo_button.clicked.connect(self.undo_last_action)
        search_button.clicked.connect(self.search_files)
        organize_button.clicked.connect(self.organize_files)

    def select_files(self):
        """Open file dialog to select files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "All Files (*.*)"
        )
        if files:
            self.selected_files = files
            self.file_list.clear()
            self.file_list.addItems([Path(f).name for f in files])
            logging.info(f"Selected {len(files)} files")

    def move_files(self):
        """Move selected files to chosen directory"""
        if not self.selected_files:
            self.show_message("Warning", "Please select files first!", QMessageBox.Icon.Warning)
            return

        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory",
            ""
        )
        
        if dest_dir:
            try:
                dest_path = Path(dest_dir)
                
                
                dest_path.mkdir(parents=True, exist_ok=True)
                
                success_count = 0
                for file_path in self.selected_files:
                    try:
                        source = Path(file_path)
                        if not source.exists():
                            logging.warning(f"Source file not found: {source}")
                            continue
                            
                        target = dest_path / source.name
                        
                        
                        if target.exists():
                            reply = self.show_question("File Exists", f"File {target.name} already exists. Replace it?")
                            if reply == QMessageBox.StandardButton.No:
                                continue
                                
                        
                        shutil.move(str(source), str(target))
                        self.history_manager.add_operation(str(source), str(target))
                        success_count += 1
                        
                    except Exception as e:
                        logging.error(f"Error moving file {source}: {str(e)}")
                        self.show_message("Warning", f"Could not move file {source.name}: {str(e)}", QMessageBox.Icon.Warning)
                
                self.file_list.clear()
                self.selected_files = []
                self.update_history_display()
                
                if success_count > 0:
                    self.show_message("Success", f"Successfully moved {success_count} files!")
                    logging.info(f"Moved {success_count} files to {dest_dir}")
            
            except Exception as e:
                self.show_message("Error", f"Error moving files: {str(e)}", QMessageBox.Icon.Critical)
                logging.error(f"Error moving files: {str(e)}")

    def undo_last_action(self):
        """Undo the last file move operation"""
        try:
            operation = self.history_manager.get_last_operation()
            if operation:
                source = Path(operation['target'])
                target = Path(operation['source'])
                
                if source.exists():
                    try:
                        
                        target.parent.mkdir(parents=True, exist_ok=True)
                        
                        try:
                            
                            import shutil
                            shutil.move(str(source), str(target))
                        except OSError:
                            
                            logging.info("Falling back to copy-then-delete method")
                            shutil.copy2(str(source), str(target))
                            if target.exists() and target.stat().st_size == source.stat().st_size:
                                os.remove(str(source))
                        
                        self.history_manager.remove_last_operation()
                        self.update_history_display()
                        self.show_message("Success", "Last operation undone!")
                        logging.info(f"Undid last operation: {source} -> {target}")
                    
                    except Exception as move_error:
                        error_msg = f"Could not move file back: {str(move_error)}"
                        self.show_message("Error", error_msg, QMessageBox.Icon.Critical)
                        logging.error(error_msg)
                else:
                    self.show_message(
                        "Warning", 
                        f"Source file no longer exists: {source}", 
                        QMessageBox.Icon.Warning
                    )
            else:
                self.show_message("Info", "No operations to undo!")
        
        except Exception as e:
            error_msg = f"Error undoing operation: {str(e)}"
            self.show_message("Error", error_msg, QMessageBox.Icon.Critical)
            logging.error(error_msg)

    def search_files(self):
        """Search for files in a directory"""
        search_text = self.search_input.text().lower()
        if not search_text:
            self.show_message("Warning", "Please enter a search term!", QMessageBox.Icon.Warning)
            return

        # Ask user for directory to search in
        search_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Search",
            ""
        )
        
        if not search_dir:
            return
        
        try:
            search_path = Path(search_dir)
            found_files = []
            
            # Show progress dialog
            progress = QMessageBox(self)
            progress.setIcon(QMessageBox.Icon.Information)
            progress.setWindowTitle("Searching")
            progress.setText("Searching for files...")
            progress.show()
            
            # Search recursively through directories
            for file_path in search_path.rglob('*'):
                if file_path.is_file() and search_text in file_path.name.lower():
                    found_files.append(str(file_path))
            
            progress.close()
            
            if found_files:
                # Update selected files and display
                self.selected_files = found_files
                self.file_list.clear()
                self.file_list.addItems([Path(f).name for f in found_files])
                self.show_message("Search Results", f"Found {len(found_files)} matching files!")
                logging.info(f"Found {len(found_files)} files matching '{search_text}'")
            else:
                self.show_message("Search Results", f"No files found matching '{search_text}'")
                logging.info(f"No files found matching '{search_text}'")
            
        except Exception as e:
            self.show_message("Error", f"Error searching files: {str(e)}", QMessageBox.Icon.Critical)
            logging.error(f"Search error: {str(e)}")

    def update_history_display(self):
        """Update the history list widget with recent operations"""
        self.history_list.clear()
        operations = self.history_manager.get_operations()
        for op in operations:
            self.history_list.addItem(
                f"Moved: {Path(op['source']).name} → {Path(op['target']).parent.name}"
            )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop events"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.process_files(files)

    def organize_files(self):
        """Organize files by their types into appropriate folders"""
        if not self.selected_files:
            self.show_message("Warning", "Please select files first!", QMessageBox.Icon.Warning)
            logging.warning("No files selected for organization")
            return

        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Base Directory for Organization",
            ""
        )
        
        if not dest_dir:
            return
            
        try:
            dest_path = Path(dest_dir)
            selected_category = self.organize_combo.currentText()
            success_count = 0
            
            for file_path in self.selected_files:
                try:
                    source = Path(file_path)
                    if not source.exists():
                        continue
                        
                    file_ext = source.suffix.lower()
                    category_path = None
                    
                    if selected_category == 'All Categories':
                        # Find appropriate subcategory
                        for main_cat, subcats in self.categories.items():
                            for subcat, extensions in subcats.items():
                                if file_ext in extensions:
                                    category_path = dest_path / main_cat / subcat
                                    break
                            if category_path:
                                break
                        if not category_path:
                            category_path = dest_path / 'Others'
                    else:
                        # Use selected category
                        if file_ext in self.flat_categories[selected_category]:
                            category_path = dest_path / selected_category
                        else:
                            continue
                    
                    # Create category folder
                    category_path.mkdir(parents=True, exist_ok=True)
                    
                    # Move file
                    target = category_path / source.name
                    
                    # Handle duplicates
                    if target.exists():
                        base = target.stem
                        ext = target.suffix
                        counter = 1
                        while target.exists():
                            target = category_path / f"{base}_{counter}{ext}"
                            counter += 1
                    
                    shutil.move(str(source), str(target))
                    self.history_manager.add_operation(str(source), str(target))
                    success_count += 1
                    
                except Exception as e:
                    logging.error(f"Error organizing file {source}: {str(e)}")
                    self.show_message("Warning", f"Could not organize file {source.name}: {str(e)}", QMessageBox.Icon.Warning)
            
            self.file_list.clear()
            self.selected_files = []
            self.update_history_display()
            
            if success_count > 0:
                self.show_message("Success", f"Successfully organized {success_count} files!")
                logging.info(f"Successfully organized {success_count} files!")
            else:
                msg = "No files were organized"
                self.show_message("Warning", msg, QMessageBox.Icon.Warning)
                logging.warning(msg)
            
        except Exception as e:
            error_msg = f"Error organizing files: {str(e)}"
            self.show_message("Error", error_msg, QMessageBox.Icon.Critical)
            logging.error(error_msg)

    def show_message(self, title, message, icon_type=QMessageBox.Icon.Information):
        """Show a styled message box"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon_type)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        return msg.exec()

    def show_question(self, title, message):
        """Show a styled question dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        return msg.exec()

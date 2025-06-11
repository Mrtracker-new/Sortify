from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLineEdit, QLabel, QFileDialog, QListWidget,
                           QProgressBar, QMessageBox, QComboBox, QTabWidget, QMenu,
                           QStatusBar, QToolBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QAction
from core.file_operations import FileOperations
from core.watcher import FolderWatcher
from core.scheduler import SortScheduler
from core.ai_categorizer import AIFileClassifier
from core.image_analyzer import ImageAnalyzer
from core.command_parser import CommandParser
from .settings_window import SettingsWindow
from pathlib import Path
from datetime import datetime
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
        
        # Initialize components - set file_ops to None initially
        # It will be initialized only when needed
        self.file_ops = None
        self.watcher = None
        
        # Initialize categorizer
        from core.categorization import FileCategorizationAI
        self.categorizer = FileCategorizationAI()
        
        # Initialize scheduler with required parameters - will initialize file_ops when needed
        self.scheduler = SortScheduler(None, self.categorizer)
        # Don't start scheduler until file_ops is initialized
        # self.scheduler.start()  # Enable auto-start
        
        self.ai_classifier = None
        self.image_analyzer = None
        self.command_parser = None
        
        # detailed organization categories
        self.categories = {
            'Images': {
                'jpg': ['.jpg', '.jpeg', '.jfif'],
                'png': ['.png'],
                'gif': ['.gif'],
                'bmp': ['.bmp'],
                'webp': ['.webp'],
                'heic': ['.heic', '.heif'],
                'tiff': ['.tiff', '.tif'],
                'vector': ['.svg', '.ai', '.eps'],
                'raw': ['.raw', '.cr2', '.nef', '.arw', '.dng'],
                'whatsapp': [],  # WhatsApp images detected by filename pattern
                'telegram': [],  # Telegram images detected by filename pattern
                'instagram': [],  # Instagram images detected by filename pattern
                'facebook': [],  # Facebook images detected by filename pattern
                'ai': []  # AI-generated images detected by filename pattern
            },
            'AI Images': {
                'chatgpt': [],  # ChatGPT/DALL-E images detected by filename pattern
                'midjourney': [],  # Midjourney images detected by filename pattern
                'stable_diffusion': [],  # Stable Diffusion images detected by filename pattern
                'bing': [],  # Bing AI images detected by filename pattern
                'bard': [],  # Google Bard images detected by filename pattern
                'claude': [],  # Claude/Anthropic images detected by filename pattern
                'other_ai': []  # Other AI-generated images detected by filename pattern
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
                'Web': ['.webm', '.flv'],
                'WhatsApp': [],  # WhatsApp videos detected by filename pattern
                'Telegram': [],  # Telegram videos detected by filename pattern
                'Instagram': [],  # Instagram videos detected by filename pattern
                'Facebook': [],  # Facebook videos detected by filename pattern
                'YouTube': []  # YouTube videos detected by filename pattern
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
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Initialize advanced features
        self.init_advanced_features()

    def init_advanced_features(self):
        """Initialize advanced features"""
        try:
            # Initialize AI classifier
            model_path = Path('data/ai_model.pkl')
            if model_path.exists():
                self.ai_classifier = AIFileClassifier(str(model_path))
                logging.info("Loaded AI classifier model")
            else:
                self.ai_classifier = AIFileClassifier()
                logging.info("Created new AI classifier")
                
            # Initialize image analyzer
            self.image_analyzer = ImageAnalyzer()
            logging.info("Initialized image analyzer")
            
            # Initialize command parser
            self.command_parser = CommandParser()
            logging.info("Initialized command parser")
            
        except Exception as e:
            logging.error(f"Error initializing advanced features: {e}")

    def setup_ui(self):
        self.setWindowTitle("Sortify - Smart File Organizer")
        self.setMinimumSize(900, 700)
        
        # Set window icon
        self.setWindowIcon(QIcon(":/icons/app_icon.png"))

        # central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create tabs
        self.tabs = QTabWidget()
        self.main_tab = QWidget()
        self.history_tab = QWidget()
        self.command_tab = QWidget()
        
        self.tabs.addTab(self.main_tab, "Organize")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.command_tab, "Commands")
        
        # Setup each tab
        self.setup_main_tab()
        self.setup_history_tab()
        self.setup_command_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Toolbar
        self.setup_toolbar()

    def setup_toolbar(self):
        """Set up the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        # Auto-sort toggle
        self.auto_sort_action = QAction("Auto-Sort: Off", self)
        self.auto_sort_action.setCheckable(True)
        self.auto_sort_action.toggled.connect(self.toggle_auto_sort)
        toolbar.addAction(self.auto_sort_action)
        
        toolbar.addSeparator()
        
        # Undo action
        undo_action = QAction("Undo Last Action", self)
        undo_action.triggered.connect(self.undo_last_action)
        toolbar.addAction(undo_action)

    def setup_main_tab(self):
        """Set up the main organization tab"""
        layout = QVBoxLayout(self.main_tab)
        
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

        # File list with drag & drop support
        file_list_label = QLabel("Selected Files (Drag & Drop Files Here)")
        file_list_label.setStyleSheet("font-weight: bold;")
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setAcceptDrops(True)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # organization options
        organize_layout = QHBoxLayout()
        self.organize_combo = QComboBox()
        self.organize_combo.addItems(['All Categories'] + list(self.flat_categories.keys()))
        organize_button = QPushButton("Organize Files")
        organize_layout.addWidget(QLabel("Organize by:"))
        organize_layout.addWidget(self.organize_combo)
        organize_layout.addWidget(organize_button)

        # all widgets to main layout
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addLayout(organize_layout)
        layout.addWidget(file_list_label)
        layout.addWidget(self.file_list)
        layout.addWidget(self.progress_bar)

        # Connect signals
        self.select_button.clicked.connect(self.select_files)
        self.move_button.clicked.connect(self.move_files)
        self.undo_button.clicked.connect(self.undo_last_action)
        search_button.clicked.connect(self.search_files)
        organize_button.clicked.connect(self.organize_files)

    def setup_history_tab(self):
        """Set up the history tab"""
        layout = QVBoxLayout(self.history_tab)
        
        # History list
        history_label = QLabel("Recent Actions")
        history_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.history_list = QListWidget()
        
        # Undo buttons
        undo_layout = QHBoxLayout()
        self.undo_selected_button = QPushButton("Undo Selected")
        self.clear_history_button = QPushButton("Clear History")
        
        undo_layout.addWidget(self.undo_selected_button)
        undo_layout.addWidget(self.clear_history_button)
        
        layout.addWidget(history_label)
        layout.addWidget(self.history_list)
        layout.addLayout(undo_layout)
        
        # Connect signals
        self.undo_selected_button.clicked.connect(self.undo_selected_action)
        self.clear_history_button.clicked.connect(self.clear_history)
        
        # Populate history
        self.refresh_history()

    def setup_command_tab(self):
        """Set up the natural language command tab"""
        layout = QVBoxLayout(self.command_tab)
        
        # Command input
        command_label = QLabel("Enter Natural Language Command:")
        command_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("E.g., 'Move all PDFs older than 30 days to Archive folder'")
        self.command_input.setMinimumHeight(40)
        
        self.execute_command_button = QPushButton("Execute Command")
        self.execute_command_button.setMinimumHeight(40)
        
        # Example commands
        examples_label = QLabel("Example Commands:")
        examples_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        
        examples = [
            "Move all PDFs to Archive folder",
            "Move all files older than 30 days to Archive folder",
            "Sort Downloads folder",
            "Organize Documents by type"
        ]
        
        self.examples_list = QListWidget()
        self.examples_list.addItems(examples)
        self.examples_list.itemClicked.connect(self.use_example_command)
        
        # Command output
        output_label = QLabel("Command Output:")
        output_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        
        self.command_output = QListWidget()
        
        layout.addWidget(command_label)
        layout.addWidget(self.command_input)
        layout.addWidget(self.execute_command_button)
        layout.addWidget(examples_label)
        layout.addWidget(self.examples_list)
        layout.addWidget(output_label)
        layout.addWidget(self.command_output)
        
        # Connect signals
        self.execute_command_button.clicked.connect(self.execute_command)

    def select_files(self):
        """Open file dialog to select files"""
        # Get the last file directory from config if available
        last_dir = ''
        if hasattr(self, 'config_manager') and self.config_manager:
            last_dir = self.config_manager.get_last_directory('file')
            
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            last_dir,
            "All Files (*.*)"
        )
        
        if files:
            # Save the selected directory to config
            if hasattr(self, 'config_manager') and self.config_manager:
                # Use the directory of the first selected file
                file_dir = str(Path(files[0]).parent)
                self.config_manager.set_last_directory('file', file_dir)
                
            self.selected_files = files
            self.update_file_list()
            self.status_bar.showMessage(f"Selected {len(files)} files")
            
    def move_files(self):
        """Move selected files to chosen directory"""
        if not self.selected_files:
            self.show_message("Warning", "Please select files first!", QMessageBox.Icon.Warning)
            return

        # Get the last destination directory from config if available
        last_dir = ''
        if hasattr(self, 'config_manager') and self.config_manager:
            last_dir = self.config_manager.get_last_directory('destination')

        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory",
            last_dir
        )
        
        if dest_dir:
            # Save the selected directory to config
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.set_last_directory('destination', dest_dir)
                
            try:
                # Initialize file operations if needed
                if self.file_ops is None:
                    self.file_ops = FileOperations(dest_dir, "Organized Files")
                    
                    # Now that file_ops is initialized, we can start the scheduler
                    if hasattr(self, 'scheduler') and self.scheduler:
                        self.scheduler.file_ops = self.file_ops
                        if not self.scheduler.scheduler.running:
                            self.scheduler.start()
                    
                # Show progress
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # Move files
                total_files = len(self.selected_files)
                
                # Create a processing thread to handle file operations
                self.processing_thread = ProcessingThread(self.selected_files, self.file_ops)
                self.processing_thread.progress.connect(self.update_progress)
                self.processing_thread.finished.connect(self.on_processing_finished)
                self.processing_thread.error.connect(self.on_processing_error)
                self.processing_thread.start()
                
                # Update status
                self.status_bar.showMessage(f"Organizing {total_files} files...")
                
                # These lines are redundant as the thread will handle progress and completion
                # self.progress_bar.setValue(100)
                # self.on_processing_finished()
                
            except Exception as e:
                self.on_processing_error(str(e))

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def on_processing_finished(self):
        """Handle processing completion"""
        self.progress_bar.setVisible(False)
        self.file_list.clear()
        self.selected_files = []
        self.refresh_history()
        self.status_bar.showMessage("Files organized successfully")
        self.show_message("Success", "Files have been organized successfully!")

    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Error organizing files")
        self.show_message("Error", f"Error organizing files: {error_msg}")

    def undo_last_action(self):
        """Undo the last file operation"""
        success, message = self.history_manager.undo_last_operation()
        if success:
            self.refresh_history()
            self.status_bar.showMessage("Last action undone")
            self.show_message("Success", message)
        else:
            self.status_bar.showMessage("Could not undo last action")
            self.show_message("Warning", message, QMessageBox.Icon.Warning)

    def undo_selected_action(self):
        """Undo the selected action from history"""
        selected_items = self.history_list.selectedItems()
        if not selected_items:
            self.show_message("Warning", "Please select an action to undo", QMessageBox.Icon.Warning)
            return
            
        selected_index = self.history_list.row(selected_items[0])
        history_items = self.history_manager.get_operations_with_id()
        
        if selected_index < len(history_items):
            operation_id = history_items[selected_index]['id']
            success, message = self.history_manager.undo_operation_by_id(operation_id)
            
            if success:
                self.refresh_history()
                self.status_bar.showMessage("Selected action undone")
                self.show_message("Success", message)
            else:
                self.status_bar.showMessage("Could not undo selected action")
                self.show_message("Warning", message, QMessageBox.Icon.Warning)
        else:
            self.show_message("Warning", "Could not identify the selected action", QMessageBox.Icon.Warning)

    def clear_history(self):
        """Clear operation history"""
        confirm = QMessageBox.question(
            self,
            "Confirm Clear History",
            "Are you sure you want to clear all history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                cursor = self.history_manager.conn.cursor()
                cursor.execute("DELETE FROM history")
                cursor.execute("DELETE FROM operations")
                self.history_manager.conn.commit()
                self.history_list.clear()
                self.status_bar.showMessage("History cleared")
                self.show_message("Success", "History has been cleared successfully")
            except Exception as e:
                self.status_bar.showMessage("Error clearing history")
                self.show_message("Error", f"Could not clear history: {str(e)}")

    def refresh_history(self):
        """Refresh the history list"""
        self.history_list.clear()
        history_items = self.history_manager.get_operations_with_id()
        
        if not history_items:
            self.history_list.addItem("No history items found. Perform file operations to see them here.")
        else:
            for item in history_items:
                timestamp = item.get('timestamp', '')
                if timestamp:
                    # Format timestamp if it exists
                    try:
                        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_time = timestamp
                else:
                    formatted_time = ''
                
                self.history_list.addItem(f"{item['file_name']} → {Path(item['target']).name} ({formatted_time})")

    def search_files(self):
        """Search for files"""
        search_term = self.search_input.text().strip()
        if not search_term:
            self.show_message("Warning", "Please enter a search term", QMessageBox.Icon.Warning)
            return
            
        # Implementation would depend on file search capabilities
        self.status_bar.showMessage(f"Searching for '{search_term}'...")

    def organize_files(self):
        """Organize selected files by category"""
        if not self.selected_files:
            self.show_message("Warning", "Please select files first!", QMessageBox.Icon.Warning)
            return
            
        category = self.organize_combo.currentText()
        if category == 'All Categories':
            # Use all categories
            self.move_files()
        else:
            # Use specific category
            # Implementation would depend on file operations capabilities
            self.status_bar.showMessage(f"Organizing files by {category}...")

    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """Show a message box"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()  # In PyQt6, exec() is the correct method name for QMessageBox

    def open_settings(self):
        """Open the settings window"""
        try:
            # Create settings window with current components
            settings = SettingsWindow(
                self.file_ops,
                self.history_manager,
                self,
                config_manager=getattr(self, 'config_manager', None)
            )
            
            # Pass current components to settings window
            settings.set_watcher(self.watcher)
            settings.set_scheduler(self.scheduler)
            settings.set_ai_classifier(self.ai_classifier)
            settings.set_image_analyzer(self.image_analyzer)
            settings.set_command_parser(self.command_parser)
            
            # Show settings window
            settings.show()
            
        except Exception as e:
            self.show_message("Error", f"Error opening settings: {str(e)}")
            logging.error(f"Error opening settings: {e}")
            self.show_message("Settings Error", f"Error opening settings: {str(e)}", QMessageBox.Icon.Critical)

    def toggle_auto_sort(self, checked):
        """Toggle auto-sort functionality"""
        if checked:
            # Auto-sort is being turned on
            if not self.watcher or not self.watcher.is_running():
                # Ask for folder to watch
                folder = QFileDialog.getExistingDirectory(
                    self,
                    "Select Folder to Watch",
                    ""
                )
                
                if folder:
                    try:
                        # Initialize file operations if needed
                        if self.file_ops is None:
                            dest_dir = QFileDialog.getExistingDirectory(
                                self,
                                "Select Destination Directory for Sorted Files",
                                ""
                            )
                            if not dest_dir:
                                self.auto_sort_action.setChecked(False)
                                return
                                
                            self.file_ops = FileOperations(dest_dir, "Organized Files")
                            
                            # Now that file_ops is initialized, we can start the scheduler
                            if hasattr(self, 'scheduler') and self.scheduler:
                                self.scheduler.file_ops = self.file_ops
                                if not self.scheduler.scheduler.running:
                                    self.scheduler.start()
                            
                        # Initialize categorizer
                        from core.categorization import FileCategorizationAI
                        categorizer = FileCategorizationAI()
                        
                        # Create and start watcher
                        from core.watcher import FolderWatcher
                        self.watcher = FolderWatcher(folder, self.file_ops, categorizer)
                        self.watcher.start()
                        
                        self.auto_sort_action.setText(f"Auto-Sort: On ({Path(folder).name})")
                        self.status_bar.showMessage(f"Watching folder: {folder}")
                    except Exception as e:
                        self.show_message("Error", f"Error starting auto-sort: {str(e)}")
                        self.auto_sort_action.setChecked(False)
                else:
                    self.auto_sort_action.setChecked(False)
            else:
                # Watcher already exists, check if it's already running
                if not self.watcher.is_running():
                    self.watcher.start()
                self.auto_sort_action.setText(f"Auto-Sort: On ({Path(self.watcher.watch_path).name})")
                self.status_bar.showMessage(f"Watching folder: {self.watcher.watch_path}")
        else:
            # Stop auto-sort watcher
            if self.watcher and self.watcher.is_running():
                self.watcher.stop()
                self.auto_sort_action.setText("Auto-Sort: Off")
                self.status_bar.showMessage("Auto-sort disabled")

    def execute_command(self):
        """Execute natural language command"""
        command = self.command_input.text().strip()
        if not command:
            self.show_message("Warning", "Please enter a command", QMessageBox.Icon.Warning)
            return
            
        if not self.command_parser:
            self.show_message("Error", "Command parser not initialized")
            return
            
        try:
            # Parse command
            parsed_command = self.command_parser.parse_command(command)
            
            if parsed_command.get('action') != 'unknown':
                # Execute command
                if self.file_ops is None:
                    # Need to initialize file operations
                    dest_dir = QFileDialog.getExistingDirectory(
                        self,
                        "Select Destination Directory for Sorted Files",
                        ""
                    )
                    if not dest_dir:
                        return
                        
                    self.file_ops = FileOperations(dest_dir, "Organized Files")
                    
                    # Now that file_ops is initialized, we can start the scheduler
                    if hasattr(self, 'scheduler') and self.scheduler:
                        self.scheduler.file_ops = self.file_ops
                        if not self.scheduler.scheduler.running:
                            self.scheduler.start()
                    
                success, message = self.command_parser.execute_command(parsed_command, self.file_ops)
                
                if success:
                    self.command_output.addItem(f"✅ {message}")
                    self.status_bar.showMessage("Command executed successfully")
                else:
                    self.command_output.addItem(f"❌ {message}")
                    self.status_bar.showMessage("Error executing command")
            else:
                self.command_output.addItem(f"❌ {parsed_command.get('error', 'Unknown error')}")
                self.status_bar.showMessage("Could not parse command")
                
        except Exception as e:
            self.command_output.addItem(f"❌ Error: {str(e)}")
            self.status_bar.showMessage("Error executing command")
            logging.error(f"Error executing command: {e}")

    def use_example_command(self, item):
        """Use an example command"""
        self.command_input.setText(item.text())

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for drag & drop"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop events for drag & drop"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.selected_files = files
            self.file_list.clear()
            self.file_list.addItems([Path(f).name for f in files])
            logging.info(f"Added {len(files)} files via drag and drop")
            self.status_bar.showMessage(f"Added {len(files)} files via drag and drop")

    def update_file_list(self):
        """Update the file list with selected files"""
        self.file_list.clear()
        self.file_list.addItems([Path(f).name for f in self.selected_files])
        logging.info(f"Updated file list with {len(self.selected_files)} files")

    def setup_categories(self):
        """Set up the file categories for organization"""
        self.categories = {
            'Documents': ['Word', 'Excel', 'PowerPoint', 'PDF', 'Text'],
            'Images': ['JPG', 'PNG', 'GIF', 'BMP', 'WebP', 'HEIC', 'TIFF', 'Vector', 'RAW', 'WhatsApp', 'Telegram', 'Instagram', 'Facebook', 'AI'],
            'AI Images': ['ChatGPT', 'Midjourney', 'Stable Diffusion', 'Bing', 'Bard', 'Claude', 'Other AI'],
            'Videos': ['Movies', 'Shorts', 'Streaming', 'WhatsApp', 'Telegram', 'Instagram', 'Facebook', 'YouTube'],
            'Audio': ['Music', 'Voice'],
            'Code': ['Python', 'Web', 'Data', 'Scripts'],
            'Archives': ['Compressed', 'Disk Images'],
            'Office': ['Templates', 'Outlook', 'Database'],
            'Misc': ['Other']
        }
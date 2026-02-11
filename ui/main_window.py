from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLineEdit, QLabel, QFileDialog, QListWidget,
                           QProgressBar, QMessageBox, QComboBox, QTabWidget, QMenu,
                           QStatusBar, QToolBar, QCheckBox, QDialog, QTextEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QAction, QFont
from core.file_operations import FileOperations
from core.watcher import FolderWatcher
from core.scheduler import SortScheduler
from core.ai_categorizer import AIFileClassifier
from core.image_analyzer import ImageAnalyzer
from core.command_parser import CommandParser
from core.config_manager import ConfigManager
from .settings_window import SettingsWindow
from pathlib import Path
from datetime import datetime
import logging
import shutil
import os

# Create module-specific logger
logger = logging.getLogger('Sortify.MainWindow')

class ProcessingThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)  # Now emits results dictionary
    error = pyqtSignal(str)
    cancelled = pyqtSignal()  # Signal emitted when operation is cancelled

    def __init__(self, files, file_ops):
        super().__init__()
        self.files = files
        self.file_ops = file_ops
        self._cancelled = False  # Cancellation flag

    def run(self):
        results = {'success': [], 'failed': []}
        total = len(self.files)
        
        for i, file in enumerate(self.files, 1):
            try:
                # Check for cancellation
                if self._cancelled:
                    logger.info("Operation cancelled by user")
                    self.cancelled.emit()  # Emit cancelled signal
                    return  # Exit early
                
                # Process each file
                category = self.file_ops.categorize_file(file)
                result = self.file_ops.move_file(file, category)
                
                if result:  # move_file returns None if user cancels confirmation
                    results['success'].append((file, str(result)))
                    logger.info(f"Successfully processed: {file}")
                else:
                    results['failed'].append((file, "User cancelled operation"))
                    logger.warning(f"Operation cancelled for: {file}")
                    
            except Exception as e:
                # Log the error but continue processing other files
                error_msg = str(e)
                logger.error(f"Failed to process {file}: {error_msg}")
                results['failed'].append((file, error_msg))
            
            # Update progress regardless of success/failure
            self.progress.emit(int((i / total) * 100))
        
        # Emit results with success and failure details
        self.finished.emit(results)
    
    def cancel(self):
        """Cancel the ongoing operation"""
        self._cancelled = True
        logger.info("Cancellation requested for processing thread")

class ModelLoaderThread(QThread):
    """
    Background thread to load heavy AI models without freezing the UI.
    """
    finished = pyqtSignal(object, object, object, object)  # ai_classifier, image_analyzer, command_parser, spacy_nlp
    progress = pyqtSignal(str)  # Status messages for loading progress
    
    def run(self):
        try:
            import sys
            import os
            from pathlib import Path
            
            # Import here to avoid main thread lag if they do top-level loading
            from core.ai_categorizer import AIFileClassifier
            from core.image_analyzer import ImageAnalyzer
            from core.command_parser import CommandParser
            
            logger.info("Starting background model loading...")
            
            # === Load spaCy model first ===
            spacy_nlp = None
            try:
                self.progress.emit("Loading spaCy model...")
                logger.info("Loading spaCy model in background thread")
                
                import spacy
                import spacy.util
                
                # When running from PyInstaller bundle, set up model paths
                if getattr(sys, '_MEIPASS', None):
                    possible_model_paths = [
                        os.path.join(sys._MEIPASS, 'en_core_web_sm'),
                        os.path.join(os.path.dirname(sys.executable), 'en_core_web_sm'),
                    ]
                    
                    for model_path in possible_model_paths:
                        if os.path.exists(model_path):
                            logger.info(f"Setting spaCy model path to: {model_path}")
                            spacy.util.set_data_path(model_path)
                            break
                
                # Load the model
                spacy_nlp = spacy.load('en_core_web_sm')
                logger.info("✓ spaCy model loaded successfully")
                self.progress.emit("spaCy model loaded")
                
            except ImportError as e:
                logger.warning(f"spaCy import failed: {e}")
                logger.info("Application will use basic pattern-based categorization")
                self.progress.emit("spaCy not available - using basic mode")
            except OSError as e:
                # This catches DLL loading errors from PyTorch/thinc dependencies
                logger.warning(f"spaCy dependencies failed to load (DLL error): {e}")
                logger.info("This is often caused by missing Visual C++ Redistributables")
                logger.info("Application will use basic pattern-based categorization")
                self.progress.emit("spaCy unavailable (DLL error) - using basic mode")
            except Exception as e:
                logger.warning(f"Error loading spaCy: {e}")
                logger.info("Application will use basic pattern-based categorization")
                self.progress.emit("spaCy loading failed - using basic mode")
            
            # === Load other AI models ===
            self.progress.emit("Loading AI classifier...")
            
            # Initialize AI classifier
            ai_classifier = None
            model_path = Path('data/ai_model.pkl')
            if model_path.exists():
                ai_classifier = AIFileClassifier(str(model_path))
                logger.info("Loaded AI classifier model")
            else:
                ai_classifier = AIFileClassifier()
                logger.info("Created new AI classifier")
                
            # Initialize image analyzer
            self.progress.emit("Loading image analyzer...")
            image_analyzer = ImageAnalyzer()
            logger.info("Initialized image analyzer")
            
            # Initialize command parser
            self.progress.emit("Loading command parser...")
            command_parser = CommandParser()
            logger.info("Initialized command parser")
            
            self.progress.emit("All models loaded")
            self.finished.emit(ai_classifier, image_analyzer, command_parser, spacy_nlp)
            
        except Exception as e:
            logger.error(f"Error in model loader thread: {e}")
            # Emit None to signal failure/partial loading
            self.finished.emit(None, None, None, None)

class PreviewDialog(QDialog):
    """Dialog to preview file operations before executing them"""
    
    def __init__(self, dry_run_manager, parent=None):
        super().__init__(parent)
        self.dry_run_manager = dry_run_manager
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the preview dialog UI"""
        self.setWindowTitle("Preview File Operations")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Header label
        operations = self.dry_run_manager.get_operations()
        header_label = QLabel(f"📋 {len(operations)} file operations planned:")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header_label)
        
        # Text area for preview table
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setFont(QFont("Courier New", 9))
        
        # Format operations as text table
        text_content = self._format_operations_table(operations)
        preview_text.setText(text_content)
        
        layout.addWidget(preview_text)
        
        # Summary
        summary_text = self._get_summary()
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px; color: #000000;")
        layout.addWidget(summary_label)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Customize button text
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Continue")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        
        layout.addWidget(button_box)
    
    def _format_operations_table(self, operations):
        """Format operations as a text table"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"{'Operation':<12} {'File':<30} {'→':<3} {'Destination'}")
        lines.append("=" * 80)
        
        for op in operations:
            operation_icon = {
                'move': '📦 MOVE',
                'copy': '📄 COPY',
                'rename': '✏️ RENAME',
                'delete': '🗑️ DELETE'
            }.get(op['operation'], '📌 ' + op['operation'].upper())
            
            filename = op['filename'][:28] + '..' if len(op['filename']) > 30 else op['filename']
            dest = op['destination']
            
            lines.append(f"{operation_icon:<12} {filename:<30} {'→':<3} {dest}")
        
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"✨ Total: {len(operations)} files will be processed")
        lines.append("💡 Click 'Continue' to execute these operations")
        lines.append("   Click 'Cancel' to abort")
        
        return "\n".join(lines)
    
    def _get_summary(self):
        """Get summary of operations"""
        operations = self.dry_run_manager.get_operations()
        
        # Count by operation type
        ops_by_type = {}
        for op in operations:
            op_type = op['operation']
            ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1
        
        # Count by category
        ops_by_category = {}
        for op in operations:
            if op['category']:
                ops_by_category[op['category']] = ops_by_category.get(op['category'], 0) + 1
        
        summary_lines = []
        summary_lines.append("📊 Summary:")
        
        for op_type, count in ops_by_type.items():
            summary_lines.append(f"  • {op_type.capitalize()}: {count} files")
        
        return "\n".join(summary_lines)

class MainWindow(QMainWindow):
    def __init__(self, history_manager):
        super().__init__()
        self.history_manager = history_manager
        self.selected_files = []
        
        # Initialize config manager for persistent settings
        self.config_manager = ConfigManager()
        
        # Initialize components - set file_ops to None initially
        # It will be initialized only when needed
        self.file_ops = None
        self.watcher = None
        
        # Initialize categorizer (lightweight) - spaCy model will be injected later
        from core.categorization import FileCategorizationAI
        self.categorizer = FileCategorizationAI(nlp=None)
        
        # Delay scheduler initialization until file_ops is ready
        # This prevents crashes when scheduled jobs trigger before file_ops exists
        self.scheduler = None
        
        # Advanced features will be loaded in background
        self.ai_classifier = None
        self.image_analyzer = None
        self.command_parser = None
        
        # Load categories from config_manager
        categories_dict = self.config_manager.get_categories()
        
        # Build flat categories for UI dropdowns
        # Convert new format {main: {sub: {extensions: [...], patterns: [...]}}} to flat format
        self.categories = {}
        self.flat_categories = {}
        
        for main_cat, subcats in categories_dict.items():
            self.categories[main_cat] = {}
            for subcat, details in subcats.items():
                cat_name = f"{main_cat}/{subcat}"
                # Extract extensions from the new format
                if isinstance(details, dict) and 'extensions' in details:
                    extensions = details['extensions']
                elif isinstance(details, list):
                    # Backward compatibility with old format
                    extensions = details
                else:
                    extensions = []
                
                self.categories[main_cat][subcat] = extensions
                self.flat_categories[cat_name] = extensions
        
        # UI
        self.setup_ui()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Preview mode state
        self.preview_mode = False
        
        # Initialize advanced features
        self.init_advanced_features()

    def init_advanced_features(self):
        """Start background loading of advanced features"""
        self.status_bar.showMessage("Loading AI models...")
        
        self.loader_thread = ModelLoaderThread()
        self.loader_thread.finished.connect(self.on_models_loaded)
        self.loader_thread.progress.connect(self.on_loading_progress)
        self.loader_thread.start()
    
    def on_loading_progress(self, message):
        """Update status bar with loading progress"""
        self.status_bar.showMessage(message)
        logger.debug(f"Loading progress: {message}")
        
    def on_models_loaded(self, ai_classifier, image_analyzer, command_parser, spacy_nlp):
        """Handle completion of background model loading"""
        self.ai_classifier = ai_classifier
        self.image_analyzer = image_analyzer
        self.command_parser = command_parser
        
        # Inject spaCy model into categorizer
        if spacy_nlp is not None:
            self.categorizer.set_nlp_model(spacy_nlp)
            logger.info("spaCy model injected into categorizer")
        
        # Update status based on what loaded successfully
        if self.ai_classifier and spacy_nlp:
            self.status_bar.showMessage("Ready (AI Enabled)")
            logger.info("All models loaded successfully - full AI features enabled")
        elif spacy_nlp:
            self.status_bar.showMessage("Ready (AI Partially Enabled)")
            logger.info("spaCy loaded but some AI features unavailable")
        elif self.ai_classifier:
            self.status_bar.showMessage("Ready (Basic AI - spaCy Unavailable)")
            logger.warning("spaCy model not available - using basic categorization")
        else:
            self.status_bar.showMessage("Ready (Basic Mode - AI Unavailable)")
            logger.warning("Advanced features failed to load")
            
            # Show warning dialog to inform user about AI unavailability
            QMessageBox.warning(
                self, 
                "AI Features Unavailable",
                "Advanced AI features could not be loaded. "
                "The app will use basic file categorization.\n\n"
                "You can still organize files, but categorization may be less accurate."
            )
        
        # Clean up loader thread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            self.loader_thread.quit()
            self.loader_thread.wait()
            self.loader_thread.deleteLater()
            self.loader_thread = None
        
        # Apply saved settings after models are loaded
        self.apply_saved_settings()
    
    def apply_saved_settings(self):
        """Apply saved settings from config on application startup"""
        if not self.config_manager:
            return
        
        try:
            logger.info("Applying saved settings from config")
            
            # Auto-sort settings
            if self.config_manager.get('auto_sort_enabled', False):
                watch_folder = self.config_manager.get('watch_folder', '')
                if watch_folder and Path(watch_folder).exists():
                    # Ensure file_ops is initialized
                    if not self.file_ops:
                        logger.info("Skipping auto-sort: file_ops not initialized")
                        return
                    
                    # Start watcher
                    try:
                        self.watcher = FolderWatcher(watch_folder, self.file_ops, self.categorizer)
                        self.watcher.start()
                        self.status_bar.showMessage(f"Auto-sort enabled for {Path(watch_folder).name}")
                        logger.info(f"Started auto-sort watcher for: {watch_folder}")
                    except Exception as e:
                        logger.error(f"Error starting watcher: {e}")
            
            # Schedule settings
            if self.config_manager.get('schedule_enabled', False):
                schedule_folder = self.config_manager.get('schedule_folder', '')
                if schedule_folder and Path(schedule_folder).exists():
                    # Ensure file_ops and scheduler are initialized
                    if not self.file_ops:
                        logger.info("Skipping scheduler: file_ops not initialized")
                        return
                    
                    if not self.scheduler:
                        self.scheduler = SortScheduler(self.file_ops, self.categorizer)
                        self.scheduler.start()
                    
                    # Add scheduled job
                    schedule_type = self.config_manager.get('schedule_type', 'daily')
                    hour = self.config_manager.get('schedule_hour', 0)
                    minute = self.config_manager.get('schedule_minute', 0)
                    day = self.config_manager.get('schedule_day', 0)
                    
                    try:
                        self.scheduler.add_job(
                            schedule_folder,
                            schedule_type,
                            hour=hour,
                            minute=minute,
                            day=day
                        )
                        logger.info(f"Added {schedule_type} schedule for: {schedule_folder}")
                    except Exception as e:
                        logger.error(f"Error adding scheduled job: {e}")
            
            # AI settings
            if self.config_manager.get('ai_enabled', False):
                model_path = self.config_manager.get('model_path', '')
                if model_path and Path(model_path).exists():
                    try:
                        from core.ai_categorizer import AIFileClassifier
                        self.ai_classifier = AIFileClassifier(model_path)
                        logger.info(f"Loaded AI classifier from: {model_path}")
                    except Exception as e:
                        logger.error(f"Error loading AI classifier: {e}")
            
            logger.info("Finished applying saved settings")
            
        except Exception as e:
            logger.error(f"Error applying saved settings: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            logger.info("Application closing, cleaning up resources...")
            
            # Close history manager database connection
            if hasattr(self, 'history_manager') and self.history_manager:
                self.history_manager.close()
                logger.info("History manager closed")
            
            # Finalize file operations if active
            if hasattr(self, 'file_ops') and self.file_ops:
                if hasattr(self.file_ops, 'session_active') and self.file_ops.session_active:
                    self.file_ops.finalize_operations()
                    logger.info("File operations finalized")
            
            # Clean up background threads
            if hasattr(self, 'processing_thread') and self.processing_thread:
                if self.processing_thread.isRunning():
                    self.processing_thread.cancel()
                    self.processing_thread.quit()
                    self.processing_thread.wait()
                self.processing_thread.deleteLater()
                logger.info("Processing thread cleaned up")
            
            if hasattr(self, 'loader_thread') and self.loader_thread:
                if self.loader_thread.isRunning():
                    self.loader_thread.quit()
                    self.loader_thread.wait()
                self.loader_thread.deleteLater()
                logger.info("Loader thread cleaned up")
            
            # Stop scheduler
            if hasattr(self, 'scheduler') and self.scheduler:
                self.scheduler.stop()
                logger.info("Scheduler stopped")
            
            # Stop watcher
            if hasattr(self, 'watcher') and self.watcher:
                self.watcher.stop()
                logger.info("Watcher stopped")
            
            logger.info("Resource cleanup completed successfully")
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during window close: {e}")
            # Accept the event anyway to allow the window to close
            event.accept()

    
    def _ensure_file_ops(self, base_path, folder_name):
        """
        Ensure FileOperations is initialized with valid parameters.
        Also initializes scheduler when file_ops is created.
        
        Args:
            base_path: Base directory path
            folder_name: Organization folder name
            
        Returns:
            bool: True if file_ops is ready, False otherwise
        """
        try:
            if self.file_ops is None:
                # Pass config_manager to FileOperations
                self.file_ops = FileOperations(base_path, folder_name, config_manager=self.config_manager)
                
                # Initialize scheduler now that file_ops exists
                if self.scheduler is None:
                    from core.scheduler import SortScheduler
                    self.scheduler = SortScheduler(self.file_ops, self.categorizer)
                    if not self.scheduler.scheduler.running:
                        self.scheduler.start()
                    logger.info("Scheduler initialized with file_ops")
                else:
                    # Scheduler exists, just update file_ops
                    self.scheduler.file_ops = self.file_ops
                    if not self.scheduler.scheduler.running:
                        self.scheduler.start()
            return True
        except ValueError as e:
            self.show_message("Configuration Error", str(e), QMessageBox.Icon.Warning)
            return False
        except Exception as e:
            self.show_message("Error", f"Failed to initialize file operations: {str(e)}", QMessageBox.Icon.Critical)
            return False

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
        
        # Undo last session action
        undo_session_action = QAction("Undo Last Session", self)
        undo_session_action.triggered.connect(self.undo_last_session)
        toolbar.addAction(undo_session_action)

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
        self.move_button.setObjectName("primaryButton")  # Set ID for blue styling
        self.undo_button = QPushButton("Undo Last Action")
        
        for button in [self.select_button, self.move_button, self.undo_button]:
            button.setMinimumHeight(40)
            button_layout.addWidget(button)

        # File list with drag & drop support
        file_list_label = QLabel("Selected Files (Drag & Drop Files Here)")
        file_list_label.setObjectName("sectionHeader")
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setAcceptDrops(True)
        
        # Progress bar and cancel button
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel_operation)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.cancel_button)

        # organization options
        organize_layout = QHBoxLayout()
        self.organize_combo = QComboBox()
        self.organize_combo.addItems(['All Categories'] + list(self.flat_categories.keys()))
        
        # Add preview mode checkbox
        self.preview_checkbox = QCheckBox("Preview Mode")
        self.preview_checkbox.setToolTip("Preview file operations before executing them")
        
        organize_button = QPushButton("Organize Files")
        organize_button.setObjectName("organize_button") # Set ID for styling
        organize_layout.addWidget(QLabel("Organize by:"))
        organize_layout.addWidget(self.organize_combo)
        organize_layout.addWidget(self.preview_checkbox)
        organize_layout.addWidget(organize_button)

        # all widgets to main layout
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addLayout(organize_layout)
        layout.addWidget(file_list_label)
        layout.addWidget(self.file_list)
        layout.addLayout(progress_layout)

        # Connect signals
        self.select_button.clicked.connect(self.select_files)
        self.move_button.clicked.connect(self.move_files)
        self.undo_button.clicked.connect(self.undo_last_action)
        search_button.clicked.connect(self.search_files)
        organize_button.clicked.connect(self.organize_files)

    def setup_history_tab(self):
        """Set up the history tab"""
        layout = QVBoxLayout(self.history_tab)
        
        # Tab widget for History and Sessions
        tabs = QTabWidget()
        
        # --- History Tab ---
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        
        # History list
        history_label = QLabel("Recent Actions")
        history_label.setObjectName("sectionHeader")
        self.history_list = QListWidget()
        
        # Undo buttons
        undo_layout = QHBoxLayout()
        self.undo_selected_button = QPushButton("Undo Selected")
        self.clear_history_button = QPushButton("Clear History")
        
        undo_layout.addWidget(self.undo_selected_button)
        undo_layout.addWidget(self.clear_history_button)
        
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_list)
        history_layout.addLayout(undo_layout)
        
        # --- Sessions Tab ---
        sessions_widget = QWidget()
        sessions_layout = QVBoxLayout(sessions_widget)
        
        sessions_label = QLabel("Operation Sessions")
        sessions_label.setObjectName("sectionHeader")
        self.sessions_list = QListWidget()
        
        # Session buttons
        session_button_layout = QHBoxLayout()
        self.view_session_button = QPushButton("View Session Details")
        self.undo_session_button = QPushButton("Undo Selected Session")
        self.refresh_sessions_button = QPushButton("Refresh")
        
        session_button_layout.addWidget(self.view_session_button)
        session_button_layout.addWidget(self.undo_session_button)
        session_button_layout.addWidget(self.refresh_sessions_button)
        
        sessions_layout.addWidget(sessions_label)
        sessions_layout.addWidget(self.sessions_list)
        sessions_layout.addLayout(session_button_layout)
        
        # Add tabs
        tabs.addTab(history_widget, "History")
        tabs.addTab(sessions_widget, "Sessions")
        layout.addWidget(tabs)
        
        # Connect signals
        self.undo_selected_button.clicked.connect(self.undo_selected_action)
        self.clear_history_button.clicked.connect(self.clear_history)
        self.view_session_button.clicked.connect(self.view_session_details)
        self.undo_session_button.clicked.connect(self.undo_selected_session)
        self.refresh_sessions_button.clicked.connect(self.refresh_sessions)
        
        # Populate history and sessions
        self.refresh_history()
        self.refresh_sessions()

    def setup_command_tab(self):
        """Set up the natural language command tab"""
        layout = QVBoxLayout(self.command_tab)
        
        # Command input
        command_label = QLabel("Enter Natural Language Command:")
        command_label.setObjectName("sectionHeader")
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("E.g., 'Move all PDFs older than 30 days to Archive folder'")
        self.command_input.setMinimumHeight(40)
        
        self.execute_command_button = QPushButton("Execute Command")
        self.execute_command_button.setObjectName("primaryButton")
        self.execute_command_button.setMinimumHeight(40)
        
        # Example commands
        examples_label = QLabel("Example Commands:")
        examples_label.setObjectName("sectionHeader")
        # Add margin top using QSS if possible, or keep simple
        
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
        output_label.setObjectName("sectionHeader")
        
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
                
            # Ensure file operations is initialized
            if not self._ensure_file_ops(dest_dir, "Organized Files"):
                return  # Failed to initialize
            
            try:
                # Show progress and cancel button
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.cancel_button.setVisible(True)
                
                # Clean up previous thread if it exists
                if hasattr(self, 'processing_thread') and self.processing_thread:
                    if self.processing_thread.isRunning():
                        self.processing_thread.quit()
                        self.processing_thread.wait()
                    self.processing_thread.deleteLater()
                
                # Create a processing thread to handle file operations
                self.processing_thread = ProcessingThread(self.selected_files, self.file_ops)
                self.processing_thread.progress.connect(self.update_progress)
                self.processing_thread.finished.connect(self.on_processing_finished)
                self.processing_thread.error.connect(self.on_processing_error)
                self.processing_thread.cancelled.connect(self.on_processing_cancelled)
                self.processing_thread.start()
                
                # Update status
                self.status_bar.showMessage(f"Organizing {len(self.selected_files)} files...")
                
            except Exception as e:
                self.on_processing_error(str(e))

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def on_processing_finished(self, results):
        """Handle processing completion with detailed results
        
        Args:
            results (dict): Dictionary with 'success' and 'failed' lists
        """
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.file_list.clear()
        self.selected_files = []
        self.refresh_history()
        
        # Calculate counts
        success_count = len(results.get('success', []))
        failed_count = len(results.get('failed', []))
        total_count = success_count + failed_count
        
        # Build status message
        if failed_count == 0:
            # All successful
            self.status_bar.showMessage(f"All {success_count} files organized successfully")
            self.show_message("Success", f"✅ Successfully processed {success_count} file(s)!")
        elif success_count == 0:
            # All failed
            self.status_bar.showMessage("Failed to organize files")
            error_details = "\n".join([f"• {Path(file).name}: {error}" for file, error in results['failed'][:5]])
            if failed_count > 5:
                error_details += f"\n... and {failed_count - 5} more"
            self.show_message(
                "Error", 
                f"❌ Failed to process all {failed_count} file(s):\n\n{error_details}",
                QMessageBox.Icon.Critical
            )
        else:
            # Partial success
            self.status_bar.showMessage(f"Processed {success_count}/{total_count} files successfully")
            
            # Build detailed message
            msg = f"📊 Operation Summary:\n\n"
            msg += f"✅ Successfully processed: {success_count} file(s)\n"
            msg += f"❌ Failed: {failed_count} file(s)\n\n"
            
            # Show details of failures (limit to first 5)
            if failed_count > 0:
                msg += "Failed files:\n"
                for file, error in results['failed'][:5]:
                    msg += f"• {Path(file).name}\n  Error: {error}\n"
                
                if failed_count > 5:
                    msg += f"\n... and {failed_count - 5} more failures"
            
            self.show_message("Partial Success", msg, QMessageBox.Icon.Warning)
        
        # Clean up thread
        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()
            self.processing_thread.deleteLater()
            self.processing_thread = None

    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.status_bar.showMessage("Error organizing files")
        self.show_message("Error", f"Error organizing files: {error_msg}")
        
        # Clean up thread
        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()
            self.processing_thread.deleteLater()
            self.processing_thread = None
    
    def on_processing_cancelled(self):
        """Handle processing cancellation"""
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.status_bar.showMessage("Operation cancelled by user")
        self.show_message("Cancelled", "File operation was cancelled", QMessageBox.Icon.Information)
        
        # Clean up thread
        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait()
            self.processing_thread.deleteLater()
            self.processing_thread = None
    
    def _cancel_operation(self):
        """Cancel the current file operation"""
        if hasattr(self, 'processing_thread') and self.processing_thread:
            self.processing_thread.cancel()
            logging.info("User requested operation cancellation")

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
                # Use HistoryManager methods to clear data
                success1 = self.history_manager.clear_operations()
                success2 = self.history_manager.clear_all_history()
                
                if success1 and success2:
                    self.history_list.clear()
                    self.status_bar.showMessage("History cleared")
                    self.show_message("Success", "History has been cleared successfully")
                else:
                    raise Exception("Failed to clear history tables")
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
        
        # Check if preview mode is enabled
        preview_mode = self.preview_checkbox.isChecked()
        
        # Get the last destination directory from config if available
        last_dir = ''
        if hasattr(self, 'config_manager') and self.config_manager:
            last_dir = self.config_manager.get_last_directory('destination')
        
        dest_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Directory for Organized Files",
            last_dir
        )
        
        if not dest_dir:
            return
        
        try:
            # Save the selected directory to config
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.set_last_directory('destination', dest_dir)
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            if preview_mode:
                # DRY-RUN MODE: Create FileOperations in dry-run mode
                # and use background thread to build the preview
                self.preview_file_ops = FileOperations(
                    base_path=dest_dir,
                    folder_name="Organized Files",
                    dry_run=True
                )
                
                # Ensure FileOperations is properly initialized
                if not self.preview_file_ops:
                    self.progress_bar.setVisible(False)
                    self.show_message("Error", "Failed to initialize file operations", QMessageBox.Icon.Critical)
                    return
                
                # Clean up previous thread if it exists
                if hasattr(self, 'processing_thread') and self.processing_thread:
                    if self.processing_thread.isRunning():
                        self.processing_thread.quit()
                        self.processing_thread.wait()
                    self.processing_thread.deleteLater()
                
                # Create a processing thread for dry-run
                self.processing_thread = ProcessingThread(self.selected_files, self.preview_file_ops)
                self.processing_thread.progress.connect(self.update_progress)
                self.processing_thread.finished.connect(lambda results: self._on_preview_finished(dest_dir))
                self.processing_thread.error.connect(self.on_processing_error)
                self.processing_thread.start()
                
                # Update status
                self.status_bar.showMessage(f"Generating preview for {len(self.selected_files)} files...")
                
            else:
                # NORMAL MODE: Execute immediately using background thread
                self._execute_organization(dest_dir)
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.show_message("Error", f"Error organizing files: {str(e)}", QMessageBox.Icon.Critical)
            logging.error(f"Error in organize_files: {e}")
    
    def _on_preview_finished(self, dest_dir):
        """Handle preview processing completion - show preview dialog"""
        try:
            # Hide progress bar
            self.progress_bar.setVisible(False)
            
            # Show preview dialog with the dry-run results
            if hasattr(self, 'preview_file_ops') and self.preview_file_ops.dry_run_manager and self.preview_file_ops.dry_run_manager.has_operations():
                dialog = PreviewDialog(self.preview_file_ops.dry_run_manager, self)
                result = dialog.exec()
                
                if result == QDialog.DialogCode.Accepted:
                    # User clicked Continue - execute operations for real
                    self._execute_organization(dest_dir)
                else:
                    # User cancelled
                    self.status_bar.showMessage("Preview cancelled")
            else:
                self.show_message("Info", "No files to organize.", QMessageBox.Icon.Information)
                self.status_bar.showMessage("No files to organize")
        except Exception as e:
            self.show_message("Error", f"Error showing preview: {str(e)}", QMessageBox.Icon.Critical)
            logging.error(f"Error in _on_preview_finished: {e}")
    
    def _execute_organization(self, dest_dir):
        """Execute the actual file organization (extracted for reuse)"""
        try:
            # Ensure file operations is initialized
            if not self._ensure_file_ops(dest_dir, "Organized Files"):
                return  # Failed to initialize
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Clean up previous thread if it exists
            if hasattr(self, 'processing_thread') and self.processing_thread:
                if self.processing_thread.isRunning():
                    self.processing_thread.quit()
                    self.processing_thread.wait()
                self.processing_thread.deleteLater()
            
            # Create a processing thread to handle file operations
            self.processing_thread = ProcessingThread(self.selected_files, self.file_ops)
            self.processing_thread.progress.connect(self.update_progress)
            self.processing_thread.finished.connect(self.on_processing_finished)
            self.processing_thread.error.connect(self.on_processing_error)
            self.processing_thread.start()
            
            # Update status
            self.status_bar.showMessage(f"Organizing {len(self.selected_files)} files...")
            
        except Exception as e:
            self.on_processing_error(str(e))

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
                                
                            # Use _ensure_file_ops to properly initialize file_ops and scheduler
                            if not self._ensure_file_ops(dest_dir, "Organized Files"):
                                self.auto_sort_action.setChecked(False)
                                return
                            
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
        
        # Check if command parser is available
        if not self.command_parser:
            self.command_output.addItem("⚠️ Command parser not available")
            self.command_output.addItem("   The AI models may still be loading. Please wait a moment and try again.")
            self.status_bar.showMessage("Command parser not initialized")
            return
        
        try:
            # Show processing indicator
            self.command_output.addItem(f"⏳ Processing: {command}")
            self.status_bar.showMessage("Parsing command...")
            
            # Parse command
            parsed_command = self.command_parser.parse_command(command)
            
            # Check if command was understood
            if parsed_command.get('action') == 'unknown':
                error_msg = parsed_command.get('error', 'Could not understand command')
                self.command_output.addItem(f"❌ {error_msg}")
                self.command_output.addItem("   Try rephrasing or use one of the example commands below.")
                self.status_bar.showMessage("Could not parse command")
                return
            
            # Display parsed command details
            action = parsed_command.get('action', 'unknown')
            self.command_output.addItem(f"📝 Parsed as: {action} command")
            
            # Ensure file operations is initialized
            if self.file_ops is None:
                self.command_output.addItem("🗂️ No base directory set. Please select one...")
                
                # Get last directory from config
                last_dir = ''
                if hasattr(self, 'config_manager') and self.config_manager:
                    last_dir = self.config_manager.get_last_directory('destination')
                
                dest_dir = QFileDialog.getExistingDirectory(
                    self,
                    "Select Base Directory for File Operations",
                    last_dir
                )
                
                if not dest_dir:
                    self.command_output.addItem("❌ Operation cancelled - no directory selected")
                    return
                
                # Save directory to config
                if hasattr(self, 'config_manager') and self.config_manager:
                    self.config_manager.set_last_directory('destination', dest_dir)
                
                # Use _ensure_file_ops to properly initialize file_ops and scheduler
                if not self._ensure_file_ops(dest_dir, "Organized Files"):
                    self.command_output.addItem("❌ Failed to initialize file operations")
                    return
                
                self.command_output.addItem(f"✅ Base directory: {dest_dir}")
            
            # Execute command
            self.status_bar.showMessage("Executing command...")
            success, message = self.command_parser.execute_command(parsed_command, self.file_ops)
            
            if success:
                self.command_output.addItem(f"✅ {message}")
                self.status_bar.showMessage("Command executed successfully")
                
                # Clear input on success
                self.command_input.clear()
                
                # Refresh history
                self.refresh_history()
            else:
                self.command_output.addItem(f"❌ {message}")
                self.status_bar.showMessage("Command execution failed")
        
        except Exception as e:
            self.command_output.addItem(f"❌ Error: {str(e)}")
            self.command_output.addItem(f"   Please try again or report this issue.")
            self.status_bar.showMessage("Error executing command")
            logging.error(f"Error executing command '{command}': {e}", exc_info=True)


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
    
    def undo_last_session(self):
        """Undo the last complete operation session"""
        sessions = self.history_manager.get_sessions(limit=1)
        
        if not sessions:
            self.show_message("Info", "No sessions found to undo", QMessageBox.Icon.Information)
            return
        
        last_session = sessions[0]
        session_id = last_session['session_id']
        op_count = last_session['operation_count']
        
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            "Confirm Undo Session",
            f"Are you sure you want to undo the last session?\n\n"
            f"Session: {session_id}\n"
            f"Operations: {op_count}\n\n"
            f"This will reverse all operations from this session.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success, message = self.history_manager.undo_session(session_id)
            if success:
                self.refresh_history()
                self.refresh_sessions()
                self.status_bar.showMessage(f"Session {session_id} undone")
                self.show_message("Success", message)
            else:
                self.status_bar.showMessage("Failed to undo session")
                self.show_message("Warning", message, QMessageBox.Icon.Warning)
    
    def refresh_sessions(self):
        """Refresh the sessions list"""
        self.sessions_list.clear()
        sessions = self.history_manager.get_sessions()
        
        if not sessions:
            self.sessions_list.addItem("No sessions found. Sessions track groups of file operations.")
        else:
            for session in sessions:
                session_id = session['session_id']
                op_count = session['operation_count']
                start_time = session['start_time']
                successful = session.get('successful_ops', 0)
                undone = session.get('undone_ops', 0)
                
                # Format display
                display_text = f"{session_id} | {op_count} ops ({successful} success, {undone} undone) | {start_time}"
                self.sessions_list.addItem(display_text)
    
    def view_session_details(self):
        """View detailed information about selected session"""
        selected_items = self.sessions_list.selectedItems()
        if not selected_items:
            self.show_message("Warning", "Please select a session to view", QMessageBox.Icon.Warning)
            return
        
        # Extract session_id from the display text
        display_text = selected_items[0].text()
        session_id = display_text.split('|')[0].strip()
        
        # Get session operations
        operations = self.history_manager.get_session_operations(session_id)
        
        if not operations:
            self.show_message("Info", "No operations found in this session", QMessageBox.Icon.Information)
            return
        
        # Create detailed view dialog
        detail_window = QMessageBox(self)
        detail_window.setWindowTitle(f"Session Details: {session_id}")
        detail_window.setIcon(QMessageBox.Icon.Information)
        
        # Build detail text
        detail_text = f"Session ID: {session_id}\n"
        detail_text += f"Total Operations: {len(operations)}\n\n"
        detail_text += "Operations:\n"
        detail_text += "-" * 50 + "\n"
        
        for i, op in enumerate(operations, 1):
            detail_text += f"{i}. {op['file_name']}\n"
            detail_text += f"   {op['original_path']} → {op['new_path']}\n"
            detail_text += f"   Status: {op['status']} | {op['timestamp']}\n\n"
        
        detail_window.setText(detail_text)
        detail_window.exec()
    
    def undo_selected_session(self):
        """Undo the selected session"""
        selected_items = self.sessions_list.selectedItems()
        if not selected_items:
            self.show_message("Warning", "Please select a session to undo", QMessageBox.Icon.Warning)
            return
        
        # Extract session_id from the display text
        display_text = selected_items[0].text()
        session_id = display_text.split('|')[0].strip()
        op_count_text = display_text.split('|')[1].split('ops')[0].strip()
        
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            "Confirm Undo Session",
            f"Are you sure you want to undo this session?\n\n"
            f"Session: {session_id}\n"
            f"Operations: {op_count_text}\n\n"
            f"This will reverse all operations from this session.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success, message = self.history_manager.undo_session(session_id)
            if success:
                self.refresh_history()
                self.refresh_sessions()
                self.status_bar.showMessage(f"Session {session_id} undone")
                self.show_message("Success", message)
            else:
                self.status_bar.showMessage("Failed to undo session")
                self.show_message("Warning", message, QMessageBox.Icon.Warning)
    
    def closeEvent(self, event):
        """Clean up threads before closing the application"""
        # Clean up processing thread
        if hasattr(self, 'processing_thread') and self.processing_thread:
            if self.processing_thread.isRunning():
                self.processing_thread.quit()
                self.processing_thread.wait()
            self.processing_thread.deleteLater()
        
        # Clean up loader thread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            if self.loader_thread.isRunning():
                self.loader_thread.quit()
                self.loader_thread.wait()
            self.loader_thread.deleteLater()
        
        # Clean up watcher
        if self.watcher:
            self.watcher.stop()
        
        # Clean up scheduler
        if self.scheduler:
            self.scheduler.stop()
        
        event.accept()
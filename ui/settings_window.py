from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                           QTabWidget, QLineEdit, QFileDialog, QCheckBox, QComboBox,
                           QSpinBox, QTimeEdit, QListWidget, QMessageBox, QGroupBox, QProgressDialog,
                           QFormLayout, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QTime, QThread, pyqtSignal, QTimer
from pathlib import Path
import logging

# Import required modules for settings functionality
from core.file_operations import FileOperations
from core.watcher import FolderWatcher
from core.scheduler import SortScheduler
from core.categorization import FileCategorizationAI
from core.image_analyzer import ImageAnalyzer
from core.command_parser import CommandParser

class SettingsWindow(QWidget):
    """Settings window for configuring Sortify features"""
    def __init__(self, file_ops, history_manager, parent=None, config_manager=None):
        super().__init__(parent)
        self.file_ops = file_ops
        self.history_manager = history_manager
        self.config_manager = config_manager
        self.watcher = None
        self.scheduler = None
        self.ai_classifier = None
        self.image_analyzer = None
        self.command_parser = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the settings UI"""
        self.setWindowTitle("Sortify Settings")
        self.setMinimumSize(700, 540)

        # Apply a lightweight modern style
        self.setMinimumSize(700, 540)

        # Ensure stylesheet backgrounds are applied (prevents transparency)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.auto_sort_tab = QWidget()
        self.schedule_tab = QWidget()
        self.ai_tab = QWidget()
        self.commands_tab = QWidget()
        
        self.tabs.addTab(self.auto_sort_tab, "Auto Sort")
        self.tabs.addTab(self.schedule_tab, "Scheduled Sorting")
        self.tabs.addTab(self.ai_tab, "AI Categorization")
        self.tabs.addTab(self.commands_tab, "Commands")
        
        # Set up each tab
        self.setup_auto_sort_tab()
        self.setup_schedule_tab()
        self.setup_ai_tab()
        self.setup_commands_tab()
        
        # Add tabs to main layout
        main_layout.addWidget(self.tabs)
        
        # Footer buttons
        footer = QHBoxLayout()
        footer.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)
        footer.addWidget(cancel_button)
        footer.addWidget(save_button)
        main_layout.addLayout(footer)

        # Apply styles after all widgets are created
        self.apply_styles()
        
    def setup_auto_sort_tab(self):
        """Set up the auto sort tab"""
        layout = QVBoxLayout(self.auto_sort_tab)
        
        # Enable auto sort
        self.auto_sort_enabled = QCheckBox("Enable Real-time Auto Sort")
        layout.addWidget(self.auto_sort_enabled)
        
        # Watch folder selection
        folder_group = QGroupBox("Watched Folder")
        folder_layout = QHBoxLayout(folder_group)
        
        self.watch_folder_path = QLineEdit()
        self.watch_folder_path.setPlaceholderText("Select folder to watch...")
        self.watch_folder_path.setReadOnly(True)
        
        self.browse_watch_folder = QPushButton("Browse...")
        self.browse_watch_folder.clicked.connect(self.select_watch_folder)
        
        folder_layout.addWidget(self.watch_folder_path)
        folder_layout.addWidget(self.browse_watch_folder)
        
        layout.addWidget(folder_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.recursive_watch = QCheckBox("Watch subfolders recursively")
        self.recursive_watch.setChecked(True)
        
        self.delay_sort = QCheckBox("Delay sorting (wait for file to be fully written)")
        self.delay_sort.setChecked(True)
        
        options_layout.addWidget(self.recursive_watch)
        options_layout.addWidget(self.delay_sort)
        
        layout.addWidget(options_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.watcher_status = QLabel("Watcher is not running")
        self.start_stop_watcher = QPushButton("Start Watcher")
        self.start_stop_watcher.clicked.connect(self.toggle_watcher)
        
        status_layout.addWidget(self.watcher_status)
        status_layout.addWidget(self.start_stop_watcher)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
    def setup_schedule_tab(self):
        """Set up the schedule tab"""
        layout = QVBoxLayout(self.schedule_tab)
        
        # Enable scheduling
        self.schedule_enabled = QCheckBox("Enable Scheduled Sorting")
        layout.addWidget(self.schedule_enabled)
        
        # Folder selection
        folder_group = QGroupBox("Folder to Sort")
        folder_layout = QHBoxLayout(folder_group)
        
        self.schedule_folder_path = QLineEdit()
        self.schedule_folder_path.setPlaceholderText("Select folder to sort...")
        self.schedule_folder_path.setReadOnly(True)
        
        self.browse_schedule_folder = QPushButton("Browse...")
        self.browse_schedule_folder.clicked.connect(self.select_schedule_folder)
        
        folder_layout.addWidget(self.schedule_folder_path)
        folder_layout.addWidget(self.browse_schedule_folder)
        
        layout.addWidget(folder_group)
        
        # Schedule settings
        schedule_group = QGroupBox("Schedule Settings")
        schedule_layout = QVBoxLayout(schedule_group)
        
        # Schedule type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Schedule Type:"))
        self.schedule_type = QComboBox()
        self.schedule_type.addItems(["Daily", "Weekly", "Monthly"])
        type_layout.addWidget(self.schedule_type)
        
        # Time settings
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time:"))
        self.schedule_time = QTimeEdit()
        self.schedule_time.setTime(QTime(0, 0))
        self.schedule_time.setDisplayFormat("HH:mm")
        time_layout.addWidget(self.schedule_time)
        
        # Day settings (for weekly/monthly)
        day_layout = QHBoxLayout()
        day_layout.addWidget(QLabel("Day:"))
        self.schedule_day = QComboBox()
        self.schedule_day.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        day_layout.addWidget(self.schedule_day)
        
        schedule_layout.addLayout(type_layout)
        schedule_layout.addLayout(time_layout)
        schedule_layout.addLayout(day_layout)
        
        layout.addWidget(schedule_group)
        
        # Scheduled jobs
        jobs_group = QGroupBox("Scheduled Jobs")
        jobs_layout = QVBoxLayout(jobs_group)
        
        self.jobs_list = QListWidget()
        self.add_job_button = QPushButton("Add Job")
        self.remove_job_button = QPushButton("Remove Job")
        
        jobs_layout.addWidget(self.jobs_list)
        
        job_buttons_layout = QHBoxLayout()
        job_buttons_layout.addWidget(self.add_job_button)
        job_buttons_layout.addWidget(self.remove_job_button)
        jobs_layout.addLayout(job_buttons_layout)
        
        # Connect signals
        self.add_job_button.clicked.connect(self.add_scheduled_job)
        self.remove_job_button.clicked.connect(self.remove_scheduled_job)
        
        layout.addWidget(jobs_group)
        
    def setup_ai_tab(self):
        """Set up the AI categorization tab"""
        layout = QVBoxLayout(self.ai_tab)

        header = QLabel("AI Categorization")
        header.setObjectName("sectionHeader")
        layout.addWidget(header)
        
        # Enable AI categorization
        self.ai_enabled = QCheckBox("Enable AI-Based Categorization")
        self.ai_enabled.setToolTip("Use the trained model to improve file categorization beyond simple rules")
        layout.addWidget(self.ai_enabled)
        
        # Model settings
        model_group = QGroupBox("AI Model")
        model_layout = QVBoxLayout(model_group)
        
        # Model path
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        model_path_layout = QHBoxLayout()
        self.model_path = QLineEdit()
        self.model_path.setPlaceholderText("Path to trained model (ai_model.pkl)")
        self.model_path.setReadOnly(True)
        self.model_path.setToolTip("Location where the trained model is saved")
        
        self.browse_model = QPushButton("Browse…")
        self.browse_model.clicked.connect(self.select_model_path)
        
        model_path_layout.addWidget(self.model_path)
        model_path_layout.addWidget(self.browse_model)
        form.addRow("Model file:", model_path_layout)
        
        # Model status
        self.model_status_label = QLabel("No model loaded")
        self.model_status_label.setObjectName("statusLabel")
        form.addRow("Status:", self.model_status_label)
        
        # Training
        training_layout = QHBoxLayout()
        self.train_model_button = QPushButton("Train New Model")
        self.train_model_button.setObjectName("primaryButton")
        self.train_model_button.setToolTip("Select a root folder organized by subfolders (categories) to train a classifier")
        self.train_model_button.clicked.connect(self.train_ai_model)
        training_layout.addWidget(self.train_model_button)
        
        model_layout.addLayout(form)
        model_layout.addLayout(training_layout)

        # Training metrics
        self.training_metrics_label = QLabel("")
        self.training_metrics_label.setObjectName("subtleLabel")
        self.training_metrics_label.setWordWrap(True)
        model_layout.addWidget(self.training_metrics_label)
        
        layout.addWidget(model_group)
        
        # Image analysis
        image_group = QGroupBox("Image Content Analysis")
        image_layout = QVBoxLayout(image_group)
        
        self.enable_image_analysis = QCheckBox("Enable Image Content Analysis")
        self.enable_image_analysis.setToolTip("Analyze image content (faces, screenshots, AI hints) to assist categorization")
        image_layout.addWidget(self.enable_image_analysis)
        
        # Image categories
        self.image_categories = QListWidget()
        self.image_categories.addItems([
            "People/Faces", 
            "Documents", 
            "Screenshots", 
            "Nature", 
            "Graphics"
        ])
        
        image_layout.addWidget(QLabel("Detected Categories:"))
        image_layout.addWidget(self.image_categories)
        
        layout.addWidget(image_group)
        layout.addStretch()
        
    def apply_styles(self):
        """
        Apply object IDs to widgets so they can be targeted by the global stylesheet.
        The styles themselves are now in resources/theme.qss.
        """
        # Assign object names for specific styling
        self.ai_enabled.setObjectName("aiCheckbox")
        self.model_status_label.setObjectName("statusLabel")
        self.training_metrics_label.setObjectName("subtleLabel")
        
        # Primary buttons are already set in setup_ui but let's ensure consistency
        # Find children and apply if needed, though they are set in other methods.
        pass
        
    def setup_commands_tab(self):
        """Set up the natural language commands tab"""
        layout = QVBoxLayout(self.commands_tab)
        
        # Enable commands
        self.commands_enabled = QCheckBox("Enable Natural Language Commands")
        layout.addWidget(self.commands_enabled)
        
        # Command input
        command_group = QGroupBox("Command Input")
        command_layout = QVBoxLayout(command_group)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command (e.g., 'Move all PDFs to Archive folder')")
        
        self.execute_command_button = QPushButton("Execute Command")
        self.execute_command_button.clicked.connect(self.execute_command)
        
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.execute_command_button)
        
        layout.addWidget(command_group)
        
        # Example commands
        examples_group = QGroupBox("Example Commands")
        examples_layout = QVBoxLayout(examples_group)
        
        examples = [
            "Move all PDFs to Archive folder",
            "Move all files older than 30 days to Archive folder",
            "Organize Downloads folder by type",
            "Organize Documents folder by type"
        ]
        
        for example in examples:
            example_button = QPushButton(example)
            example_button.clicked.connect(lambda _, cmd=example: self.command_input.setText(cmd))
            examples_layout.addWidget(example_button)
        
        layout.addWidget(examples_group)
        layout.addStretch()
        
    def select_watch_folder(self):
        """Select folder to watch for auto-sorting"""
        # Get the last watch directory from config if available
        last_dir = ''
        if self.config_manager:
            last_dir = self.config_manager.get_last_directory('watch')
            
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Watch",
            last_dir
        )
        if folder:
            self.watch_folder_path.setText(folder)
            # Save the selected directory to config
            if self.config_manager:
                self.config_manager.set_last_directory('watch', folder)
            
    def select_schedule_folder(self):
        """Select folder for scheduled sorting"""
        # Get the last schedule directory from config if available
        last_dir = ''
        if self.config_manager:
            last_dir = self.config_manager.get_last_directory('schedule')
            
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Sort",
            last_dir
        )
        if folder:
            self.schedule_folder_path.setText(folder)
            # Save the selected directory to config
            if self.config_manager:
                self.config_manager.set_last_directory('schedule', folder)
            
    def select_model_path(self):
        """Select AI model path"""
        # Get the last model directory from config if available
        last_dir = ''
        if self.config_manager:
            last_dir = self.config_manager.get_last_directory('model')
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            last_dir,
            "Model Files (*.pkl);;All Files (*.*)"
        )
        if file_path:
            self.model_path.setText(file_path)
            # Save the selected directory to config
            if self.config_manager and file_path:
                # Save the directory, not the file path
                model_dir = str(Path(file_path).parent)
                self.config_manager.set_last_directory('model', model_dir)
            
    def save_settings(self):
        """Save all settings"""
        try:
            # Auto-sort tab settings
            if self.auto_sort_enabled.isChecked():
                watch_folder = self.watch_folder_path.text()
                if watch_folder and Path(watch_folder).exists():
                    # Initialize file operations if needed
                    if not hasattr(self, 'file_ops') or self.file_ops is None:
                        self.file_ops = FileOperations()
                    
                    # Initialize categorizer if needed
                    if not hasattr(self, 'categorizer') or self.categorizer is None:
                        self.categorizer = FileCategorizationAI()
                    
                    # Configure and start the watcher
                    if self.watcher:
                        self.watcher.stop()  # Stop if already running
                        self.watcher = FolderWatcher(watch_folder, self.file_ops, self.categorizer)
                        self.watcher.start()
                        logging.info(f"Started auto-sort watcher for {watch_folder}")
            else:
                # Stop the watcher if it's running
                if self.watcher and self.watcher.is_running():
                    self.watcher.stop()
                    logging.info("Stopped auto-sort watcher")
            
            # Schedule tab settings
            if self.schedule_enabled.isChecked():
                schedule_folder = self.schedule_folder_path.text()
                if schedule_folder and Path(schedule_folder).exists():
                    # Initialize scheduler if needed
                    if not self.scheduler:
                        self.scheduler = SortScheduler(self.file_ops, self.categorizer)
                        self.scheduler.start()
                    
                    # Configure schedule
                    schedule_type = self.schedule_type.currentText().lower()  # Get from combo box
                    
                    # Get time settings
                    time = self.schedule_time.time()
                    hour = time.hour()
                    minute = time.minute()
                    day = 0  # Default for weekly (Monday)
                    if schedule_type == 'weekly':
                        # Convert day name to number (0=Monday, 6=Sunday)
                        day_name = self.schedule_day.currentText()
                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        day = days.index(day_name)
                    elif schedule_type == 'monthly':
                        # For monthly, we need a day of month (1-31)
                        day = 1  # Default to first day of month
                    
                    # Add the job
                    self.scheduler.add_job(
                        schedule_folder,
                        schedule_type,
                        hour=hour,
                        minute=minute,
                        day=day
                    )
                    logging.info(f"Added {schedule_type} schedule for {schedule_folder}")
            else:
                # Stop the scheduler if it's running
                if self.scheduler:
                    self.scheduler.stop()
                    logging.info("Stopped scheduler")
            
            # AI categorization tab settings
            if self.ai_enabled.isChecked():
                model_path = self.model_path.text()
                if model_path and Path(model_path).exists():
                    # Configure AI classifier
                    try:
                        from core.ai_categorizer import AIFileClassifier
                        self.ai_classifier = AIFileClassifier(model_path)
                        logging.info(f"Configured AI classifier with model: {model_path}")
                    except Exception as e:
                        logging.error(f"Error loading AI model: {e}")
            
            # Commands tab settings
            if self.commands_enabled.isChecked():
                # Enable command parser
                if self.command_parser:
                    logging.info("Enabled natural language commands")
            
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            self.close()
            
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def set_watcher(self, watcher):
        """Set the folder watcher instance"""
        self.watcher = watcher
        
    def set_scheduler(self, scheduler):
        """Set the scheduler instance"""
        self.scheduler = scheduler
        
    def set_ai_classifier(self, classifier):
        """Set the AI classifier instance"""
        self.ai_classifier = classifier
        
    def set_image_analyzer(self, analyzer):
        """Set the image analyzer instance"""
        self.image_analyzer = analyzer
        
    def set_command_parser(self, parser):
        """Set the command parser instance"""
        self.command_parser = parser
        
    def add_scheduled_job(self):
        """Add a new scheduled job"""
        folder = self.schedule_folder_path.text()
        if not folder:
            QMessageBox.warning(self, "Missing Folder", "Please select a folder to sort first.")
            return
            
        schedule_type = self.schedule_type.currentText()
        time = self.schedule_time.time().toString("HH:mm")
        day = self.schedule_day.currentText() if schedule_type != "Daily" else ""
        
        job_text = f"{schedule_type} at {time}"
        if day:
            job_text += f" on {day}"
        job_text += f": {Path(folder).name}"
        
        self.jobs_list.addItem(job_text)
        
    def remove_scheduled_job(self):
        """Remove the selected scheduled job"""
        selected_items = self.jobs_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a job to remove.")
            return
            
        for item in selected_items:
            row = self.jobs_list.row(item)
            self.jobs_list.takeItem(row)
            
    def train_ai_model(self):
        """Train a new AI model from a directory of categorized files (runs in background)"""
        # Get the last training directory from config if available
        last_dir = ''
        if self.config_manager:
            last_dir = self.config_manager.get_last_directory('training')
            
        # Prompt user for training directory
        training_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory with Categorized Files for Training",
            last_dir
        )
        
        if not training_dir:
            return
            
        # Save the selected directory to config
        if self.config_manager:
            self.config_manager.set_last_directory('training', training_dir)
            
        try:
            # Disable button to prevent double clicks
            self.train_model_button.setEnabled(False)
            
            # Show progress dialog (non-blocking, busy indicator)
            self._training_progress = QProgressDialog("Training AI model. This may take a few minutes...", None, 0, 0, self)
            self._training_progress.setWindowTitle("Training Model")
            self._training_progress.setWindowModality(Qt.WindowModality.WindowModal)
            self._training_progress.setCancelButton(None)
            self._training_progress.setMinimumDuration(0)
            self._training_progress.show()
            
            # Background worker
            class TrainWorker(QThread):
                finished_ok = pyqtSignal(dict, object)
                failed = pyqtSignal(str)
                def __init__(self, root):
                    super().__init__()
                    self.root = root
                def run(self):
                    try:
                        from core.ai_categorizer import AIFileClassifier
                        clf = AIFileClassifier()
                        metrics = clf.train_from_directory(self.root, recursive=True)
                        self.finished_ok.emit(metrics, clf)
                    except Exception as e:
                        self.failed.emit(str(e))
            
            self._train_worker = TrainWorker(training_dir)
            self._train_worker.finished_ok.connect(self._on_training_done)
            self._train_worker.failed.connect(self._on_training_error)
            # Always close the dialog when the thread finishes, even if signals fail
            self._train_worker.finished.connect(self._on_training_finalize_anyway)
            self._train_worker.start()

            # Start a watchdog timer to ensure the dialog closes when the worker stops
            self._train_watchdog = QTimer(self)
            self._train_watchdog.setInterval(1000)
            self._train_watchdog.timeout.connect(self._check_training_watchdog)
            self._train_watchdog.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Training Error", f"Error starting training: {str(e)}")
            logging.error(f"Error starting training: {e}")

    def _on_training_done(self, metrics, classifier):
        """Handle training completion from background thread"""
        try:
            # Assign the trained classifier
            self.ai_classifier = classifier
            
            # Save the model
            save_path = Path('data/ai_model.pkl')
            save_path.parent.mkdir(exist_ok=True)
            self.ai_classifier.save_model(str(save_path))
            self.model_path.setText(str(save_path))
            self.model_status_label.setText(f"Loaded • {save_path}")
            
            # Close progress and re-enable UI
            if hasattr(self, '_training_progress') and self._training_progress:
                self._training_progress.close()
                self._training_progress.deleteLater()
                self._training_progress = None
            self.train_model_button.setEnabled(True)
            
            # Show metrics summary
            if metrics and metrics.get('success'):
                acc = metrics.get('accuracy', 0.0)
                prec = metrics.get('precision', 0.0)
                rec = metrics.get('recall', 0.0)
                f1 = metrics.get('f1_score', 0.0)
                cats = metrics.get('categories', metrics.get('categories_count', []))
                cats_count = len(cats) if isinstance(cats, list) else int(cats)
                summary = f"Accuracy {acc:.3f} • Precision {prec:.3f} • Recall {rec:.3f} • F1 {f1:.3f} • Categories {cats_count}"
                self.training_metrics_label.setText(summary)
                QMessageBox.information(self, "Training Complete", f"Saved to {save_path}\n\n{summary}")
            else:
                err = metrics.get('error', 'Unknown error') if isinstance(metrics, dict) else 'Unknown error'
                self.training_metrics_label.setText(f"Training warning: {err}")
                QMessageBox.warning(self, "Training Finished with Warnings", f"Model saved to {save_path}\nBut training reported: {err}")
        except Exception as e:
            QMessageBox.critical(self, "Training Error", f"Error finalizing training: {str(e)}")
            logging.error(f"Error finalizing training: {e}")
        finally:
            self._train_worker = None
            if hasattr(self, '_train_watchdog') and self._train_watchdog:
                self._train_watchdog.stop()
                self._train_watchdog = None

    def _on_training_error(self, error_msg):
        """Handle training error from background thread"""
        try:
            if hasattr(self, '_training_progress') and self._training_progress:
                self._training_progress.close()
                self._training_progress.deleteLater()
                self._training_progress = None
            self.train_model_button.setEnabled(True)
            QMessageBox.critical(self, "Training Error", error_msg)
            logging.error(f"Training error: {error_msg}")
        finally:
            self._train_worker = None

    def _on_training_finalize_anyway(self):
        """Fail-safe: ensure progress dialog is closed and UI re-enabled when thread finishes."""
        try:
            if hasattr(self, '_training_progress') and self._training_progress:
                self._training_progress.close()
                self._training_progress.deleteLater()
                self._training_progress = None
            self.train_model_button.setEnabled(True)
            if hasattr(self, '_train_watchdog') and self._train_watchdog:
                self._train_watchdog.stop()
                self._train_watchdog = None
        except Exception:
            pass

    def _check_training_watchdog(self):
        """Timer-based watchdog to close the dialog if the worker has stopped."""
        try:
            running = self._train_worker.isRunning() if hasattr(self, '_train_worker') and self._train_worker else False
            if not running:
                if hasattr(self, '_training_progress') and self._training_progress:
                    self._training_progress.close()
                    self._training_progress.deleteLater()
                    self._training_progress = None
                self.train_model_button.setEnabled(True)
                if hasattr(self, '_train_watchdog') and self._train_watchdog:
                    self._train_watchdog.stop()
                    self._train_watchdog = None
        except Exception:
            # Stop watchdog silently on any unexpected error
            if hasattr(self, '_train_watchdog') and self._train_watchdog:
                self._train_watchdog.stop()
                self._train_watchdog = None
            
    def execute_command(self):
        """Execute a natural language command"""
        command = self.command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "Empty Command", "Please enter a command to execute.")
            return
            
        try:
            # Initialize command parser if needed
            if not self.command_parser:
                from core.command_parser import CommandParser
                self.command_parser = CommandParser()
                
            # Check if the command is an organize command without a source folder
            if "organize" in command.lower() and not any(folder in command.lower() for folder in ["downloads", "documents", "desktop", "pictures", "videos", "music"]):
                QMessageBox.warning(self, "Command Error", 
                                 "Please specify a source folder in your organize command.\n\nExample: 'Organize Downloads folder by type'")
                return
                
            # Initialize file operations if needed
            if not hasattr(self, 'file_ops') or self.file_ops is None:
                self.file_ops = FileOperations()
                
            # Parse and execute the command
            parsed_command = self.command_parser.parse_command(command)
            success, message = self.command_parser.execute_command(parsed_command, self.file_ops)
            
            # Show result
            if success:
                QMessageBox.information(self, "Command Executed", 
                                      f"Command executed successfully:\n{message}")
            else:
                QMessageBox.warning(self, "Command Error", 
                                 f"Error executing command:\n{message}")
            
        except Exception as e:
            QMessageBox.critical(self, "Command Error", 
                               f"Error executing command: {str(e)}")
            logging.error(f"Error executing command: {e}")
            
    def toggle_watcher(self):
        """Toggle the folder watcher on/off"""
        watch_folder = self.watch_folder_path.text()
        
        if not watch_folder:
            QMessageBox.warning(self, "Missing Folder", "Please select a folder to watch first.")
            return
            
        if not Path(watch_folder).exists():
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
            
        try:
            # Check if watcher is running
            if self.watcher and self.watcher.is_running():
                # Stop the watcher
                self.watcher.stop()
                self.watcher_status.setText("Watcher is not running")
                self.start_stop_watcher.setText("Start Watcher")
                logging.info(f"Stopped watching folder: {watch_folder}")
            else:
                # Initialize file operations if needed
                if not hasattr(self, 'file_ops') or self.file_ops is None:
                    self.file_ops = FileOperations()
                    
                # Initialize categorizer
                from core.categorization import FileCategorizationAI
                categorizer = FileCategorizationAI()
                
                # Create and start watcher
                from core.watcher import FolderWatcher
                self.watcher = FolderWatcher(watch_folder, self.file_ops, categorizer)
                self.watcher.start()
                
                self.watcher_status.setText(f"Watching folder: {Path(watch_folder).name}")
                self.start_stop_watcher.setText("Stop Watcher")
                logging.info(f"Started watching folder: {watch_folder}")
                
        except Exception as e:
            QMessageBox.critical(self, "Watcher Error", 
                               f"Error toggling watcher: {str(e)}")
            logging.error(f"Error toggling watcher: {e}")
import sys
import traceback
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from core.history import HistoryManager

# Set up logging
def setup_logging():
    log_path = Path('debug.log')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_path

def exception_hook(exctype, value, tb):
    """Handle uncaught exceptions"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error(error_msg)
    QMessageBox.critical(None, 'Error',
                        f'An unexpected error occurred:\n{str(value)}\n\nCheck debug.log for details.')
    sys.exit(1)

def main():
    try:
        log_path = setup_logging()
        logging.info("Starting application...")
        logging.info(f"Current working directory: {Path.cwd()}")
        
        # Set exception hook
        sys.excepthook = exception_hook
        
        # Initialize application
        logging.info("Initializing QApplication...")
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Load CSS
        css_path = Path(__file__).parent / 'ui' / 'styles.css'
        logging.info(f"Looking for CSS at: {css_path}")
        if css_path.exists():
            logging.info("CSS file found")
            with open(css_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
        else:
            logging.warning(f"CSS file not found at: {css_path}")
        
        try:
            # Initialize database
            logging.info("Initializing database...")
            history = HistoryManager()
            
            # Create main window
            logging.info("Creating main window...")
            window = MainWindow(history)
            window.show()
            
        except (PermissionError, OSError) as e:
            error_msg = ('Cannot access the database file. '
                        'Please ensure no other instance of the application is running '
                        'and you have write permissions to the data directory.')
            logging.error(f"Database error: {str(e)}")
            QMessageBox.critical(None, 'Database Error', error_msg)
            sys.exit(1)
        
        logging.info("Starting event loop...")
        sys.exit(app.exec())
        
    except Exception as e:
        logging.error(f"Error during startup: {str(e)}")
        logging.error(traceback.format_exc())
        QMessageBox.critical(None, 'Startup Error',
                           f'Error during startup: {str(e)}\n\nCheck {log_path} for details.')
        sys.exit(1)

if __name__ == "__main__":
    logging.info("Script started...")
    main()
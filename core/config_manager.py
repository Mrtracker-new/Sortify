import os
import json
from pathlib import Path
import logging

class ConfigManager:
    """Manages application configuration settings"""
    def __init__(self, config_file=None):
        # Default config file location
        if config_file is None:
            self.config_file = Path(os.path.expanduser('~')) / '.sortify' / 'config.json'
        else:
            self.config_file = Path(config_file)
            
        # Create directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.config = {
            'last_training_directory': '',
            'last_watch_directory': '',
            'last_schedule_directory': '',
            'last_destination_directory': '',
            'model_path': '',
            'auto_sort_enabled': False,
            'schedule_enabled': False,
            'ai_enabled': False,
            'commands_enabled': False
        }
        
        # Load existing configuration if available
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Update config with loaded values
                    self.config.update(loaded_config)
                logging.info(f"Loaded configuration from {self.config_file}")
            else:
                logging.info("No configuration file found, using defaults")
                self.save_config()  # Create default config file
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            # If loading fails, save the default configuration
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Saved configuration to {self.config_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value and save"""
        self.config[key] = value
        return self.save_config()
    
    def get_last_directory(self, directory_type):
        """Get the last used directory of a specific type"""
        key = f'last_{directory_type}_directory'
        return self.get(key, '')
    
    def set_last_directory(self, directory_type, path):
        """Set the last used directory of a specific type"""
        key = f'last_{directory_type}_directory'
        return self.set(key, path)
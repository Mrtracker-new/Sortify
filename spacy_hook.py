# Runtime hook for spaCy
import os
import sys
import spacy
import site
import importlib.util

# Print debug information
print("SpaCy runtime hook executing...")

# Set spaCy's data path to the bundled model directory
try:
    # When running from PyInstaller bundle, _MEIPASS is defined
    if hasattr(sys, '_MEIPASS'):
        # Set the data path to the bundled model directory
        model_path = os.path.join(sys._MEIPASS, 'en_core_web_sm')
        print(f"Checking PyInstaller bundle path: {model_path}")
        
        if os.path.exists(model_path):
            # Override spaCy's model loading mechanism to use the bundled model
            spacy.util.set_data_path(model_path)
            print(f"SpaCy data path set to: {model_path}")
        else:
            print(f"Warning: SpaCy model directory not found at {model_path}")
            
            # Try to find the model in the executable directory
            exe_dir = os.path.dirname(sys.executable)
            model_path = os.path.join(exe_dir, 'en_core_web_sm')
            print(f"Checking executable directory: {model_path}")
            
            if os.path.exists(model_path):
                spacy.util.set_data_path(model_path)
                print(f"SpaCy data path set to: {model_path}")
            else:
                # Try to find the model in site-packages
                for site_path in site.getsitepackages():
                    model_path = os.path.join(site_path, 'en_core_web_sm')
                    print(f"Checking site-packages: {model_path}")
                    if os.path.exists(model_path):
                        spacy.util.set_data_path(model_path)
                        print(f"SpaCy data path set to: {model_path}")
                        break
    else:
        print("Not running from PyInstaller bundle")
        
    # Print the current spaCy data path
    print(f"Current spaCy data path: {spacy.util.get_data_path()}")
    
except Exception as e:
    print(f"Error setting spaCy data path: {e}")
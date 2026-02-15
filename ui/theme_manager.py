import os
import logging
from pathlib import Path

# Create module-specific logger
logger = logging.getLogger('Sortify.ThemeManager')

class ThemeManager:
    """
    Manages application logic for applying themes.
    Injects variables into the generic .qss file to support dynamic palettes.
    """
    def __init__(self):
        # Define the centralized color palette (Modern Dark Theme)
        self.palette = {
            # Application
            "@bg_primary": "#1e1e1e",
            "@bg_secondary": "#252526",
            "@bg_tertiary": "#333333",
            
            # Text
            "@text_primary": "#ffffff",
            "@text_secondary": "#cccccc",
            "@text_muted": "#858585",
            
            # Interactive / Accents
            "@primary": "#0d6efd",         # Bootstrap Blue
            "@primary_hover": "#0b5ed7",
            "@primary_pressed": "#0a58ca",
            "@accent": "#3498db",
            
            # Borders & Dividers
            "@border_color": "#3e3e42",
            "@border_light": "#555555",
            
            # Status
            "@success": "#2ecc71",
            "@error": "#e74c3c",
            "@warning": "#f1c40f",
            
            # Components
            "@input_bg": "#3c3c3c",
            "@list_item_hover": "rgba(255, 255, 255, 0.08)",
            "@list_item_selected": "#37373d"
        }

    def get_stylesheet(self) -> str:
        """
        Reads the QSS template and replaces variables with palette values.
        """
        try:
            # Determine path to qss file
            # Assuming resources/theme.qss relative to project root
            # Or calculate relative to this file
            base_dir = Path(__file__).parent.parent
            qss_path = base_dir / "resources" / "theme.qss"
            
            if not qss_path.exists():
                logger.warning(f"Stylesheet not found at {qss_path}")
                return ""

            with open(qss_path, "r", encoding="utf-8") as f:
                stylesheet = f.read()

            # Inject variables - sort by length (longest first) to prevent partial matches
            # e.g., replace "@primary_hover" before "@primary" to avoid "#0d6efd_hover"
            sorted_palette = sorted(self.palette.items(), key=lambda x: len(x[0]), reverse=True)
            for key, value in sorted_palette:
                stylesheet = stylesheet.replace(key, value)
            
            return stylesheet

        except Exception as e:
            logger.error(f"Error loading theme: {e}")
            return ""

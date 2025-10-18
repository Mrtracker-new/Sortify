<div align="center">

<img src="screenshots/Sortify.jpg" alt="Sortify Logo" width="200"/>

# 🗂️ Sortify

**A smart file organization tool with AI-powered categorization**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/Mrtracker-new/Sortify)](https://github.com/Mrtracker-new/Sortify/issues)
[![GitHub stars](https://img.shields.io/github/stars/Mrtracker-new/Sortify)](https://github.com/Mrtracker-new/Sortify/stargazers)

<img src="screenshots/Main_interface.png" alt="Sortify Main Interface" width="600"/>

[Installation](#-installation) • [Features](#-key-features) • [User Guide](#-user-guide) • [Technical Details](#-technical-details) • [Contributing](#-contributing)

</div>

## 📋 Overview

Sortify is an intelligent file organization tool that automatically categorizes and organizes your files based on their formats, content, and metadata. It leverages AI and machine learning to understand file content and context, going beyond simple extension-based sorting.

### 🎯 Why Sortify?

- **Save Time**: Automate tedious file organization tasks
- **Reduce Clutter**: Keep your digital workspace organized automatically
- **Smart Categorization**: Files are sorted based on what they actually contain, not just their extension
- **Flexible Rules**: Create custom organization rules using natural language
- **Set & Forget**: Configure once and let Sortify handle organization in the background

## ✨ Key Features

### 🔄 Real-time Auto Sort
Automatically monitor folders and sort new files as they arrive.
- Uses the watchdog library to detect file system changes
- Configurable watched folders with recursive monitoring
- Background processing that works even when the app is minimized

### ↩️ Undo Last Sort
Easily revert file operations with a comprehensive undo system.
- One-click undo for the most recent operation
- Detailed history tracking of all file movements
- Ability to undo specific operations from the history

### 🖱️ Drag & Drop Support
Simply drag files directly into the application window.
- Intuitive interface for adding files
- Support for multiple files at once
- Visual feedback during drag operations

### ⏰ Scheduled Sorting
Set up automatic sorting to run on a schedule.
- Daily, weekly, or monthly scheduling options
- Multiple scheduled jobs for different folders
- Configurable time settings

### 🧠 AI-Based File Categorization
Intelligent categorization beyond simple file extensions.
- Machine learning model to categorize files based on content and name
- Trainable classifier that improves over time
- Detects document types like resumes, invoices, etc.

### 🖼️ Image Content Sorting
Automatically categorize images based on their visual content.
- Detects faces for sorting photos of people
- Identifies screenshots vs. photographs
- Recognizes document images

### 📱 Social Media Content Organization
Automatically categorize media files from popular social platforms.
- Detects and sorts media from WhatsApp, Telegram, Instagram, Facebook, and YouTube
- Organizes videos into platform-specific folders (videos/whatsapp, videos/telegram, etc.)
- Categorizes images by source platform (images/instagram, images/facebook, etc.)

### 💬 Natural Language Command Parsing
Define sorting rules using plain English commands.
- Process commands like "Move all PDFs older than 30 days to Archive folder"
- Intuitive interface with example commands
- Support for time-based, extension-based, and location-based rules

## 🚀 Getting Started

### 💻 System Requirements

- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+, Fedora 30+)
- **Python**: Version 3.8 or higher
- **Disk Space**: ~150MB for installation (including dependencies)
- **RAM**: Minimum 4GB recommended (8GB+ for optimal performance with AI features)
- **Additional**: Internet connection required for initial setup and AI model downloads

### 📥 Installation

#### Option 1: Windows Installer (Recommended for Windows Users)

1. Download the latest installer from the [Releases](https://github.com/Mrtracker-new/Sortify/releases) page
2. Run the installer and follow the on-screen instructions
3. Launch Sortify from the Start menu or desktop shortcut

> **Note**: If Windows Defender flags the installer, you may need to add an exception for the application.

#### Option 2: From Source (For Developers or All Platforms)

1. Clone the repository:
   ```bash
   git clone https://github.com/Mrtracker-new/Sortify.git
   cd Sortify
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # Linux/macOS
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

#### Option 3: Build Your Own Installer

For instructions on building your own installer, see the build scripts in the `build_tools/` directory.

### 📚 User Guide

Sortify offers multiple ways to organize your files. Here's how to use each feature:

<details>
<summary><b>🔄 Real-time Auto Sort</b></summary>
<br>

1. Click the "Auto-Sort" toggle in the toolbar
2. Select a folder to watch
3. Choose a destination for sorted files
4. Files added to the watched folder will be automatically sorted
</details>

<details>
<summary><b>🖱️ Drag & Drop</b></summary>
<br>

1. Simply drag files from your file explorer
2. Drop them into the main window
3. Use the organize button to sort them
</details>

<details>
<summary><b>⏰ Scheduled Sorting</b></summary>
<br>

1. Open Settings from the toolbar
2. Go to the "Scheduled Sorting" tab
3. Configure your schedule and select folders
4. Add the job to the scheduler
</details>

<details>
<summary><b>📱 Social Media Content Organization</b></summary>
<br>

1. No additional setup required - works automatically
2. Media files with names containing platform identifiers (e.g., "whatsapp", "telegram", "instagram") will be sorted into dedicated folders
3. Supports common video formats (mp4, avi, 3gp, mov) and image formats (jpg, jpeg, png)
</details>

<details>
<summary><b>💬 Natural Language Commands</b></summary>
<br>

1. Go to the "Commands" tab
2. Enter a command like "Move all PDFs to Archive folder"
3. Click "Execute Command"
4. You can also use the example commands provided

**Example Commands:**
- "Move all images to Pictures folder"
- "Sort PDFs older than 30 days into Archive folder"
- "Organize downloads by file type"
- "Move videos larger than 1GB to External Drive"
- "Find duplicate files in Documents folder"
</details>

## ❓ Troubleshooting

<details>
<summary><b>Application Won't Start</b></summary>
<br>

1. Ensure you have Python 3.8+ installed
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Check for error messages in the console
4. Try running with administrator privileges
</details>

<details>
<summary><b>Files Not Being Sorted</b></summary>
<br>

1. Verify the source and destination folders exist and are accessible
2. Check if you have write permissions for the destination folder
3. Ensure the file types you're trying to sort are supported
4. Check if any other application has locked the files
</details>

<details>
<summary><b>AI Categorization Not Working</b></summary>
<br>

1. Ensure you have an internet connection for the initial model download
2. Verify that the AI model files exist in the application directory
3. Try restarting the application
4. Check if your system meets the minimum RAM requirements (4GB+)
</details>

<details>
<summary><b>Windows Defender Warnings</b></summary>
<br>

1. Add an exclusion for the Sortify executable in Windows Defender
2. Consider using the signed installer from the releases page
3. Check that the download source is the official GitHub repository
</details>

## 🔧 Technical Details

<details>
<summary><b>Architecture</b></summary>
<br>

The application uses a modular architecture with these key components:

- **Core Modules**:
  - `watcher.py`: Implements real-time folder monitoring
  - `scheduler.py`: Manages scheduled sorting tasks
  - `ai_categorizer.py`: Provides machine learning-based file classification
  - `image_analyzer.py`: Analyzes image content and detects social media sources
  - `categorization.py`: Handles file categorization including social media detection
  - `file_operations.py`: Manages file sorting and organization with platform-specific rules
  - `command_parser.py`: Parses natural language commands

- **UI Components**:
  - `main_window.py`: Main interface with tabs
  - `settings_window.py`: Configuration interface for all features
</details>

<details>
<summary><b>Dependencies</b></summary>
<br>

### Key Libraries

- **watchdog**: Real-time file system monitoring
  - Detects file system events (creation, modification, deletion)
  - Provides event handlers for custom actions
  - Used in the watcher module for auto-sorting

- **apscheduler**: Advanced Python scheduler
  - Supports cron-like scheduling
  - Persists jobs between application restarts
  - Handles background task execution

- **scikit-learn**: Machine learning library
  - Powers the AI-based file categorization
  - Provides classification algorithms for file type prediction
  - Used for training custom categorization models

- **opencv-python**: Computer vision library
  - Analyzes image content for intelligent sorting
  - Detects faces, documents, and screenshots
  - Extracts visual features for categorization

- **nltk**: Natural Language Toolkit
  - Processes natural language commands
  - Performs text tokenization and parsing
  - Extracts meaning from user instructions

- **spaCy**: Advanced NLP library
  - Provides named entity recognition
  - Understands semantic relationships in commands
  - Enhances natural language command parsing

- **PyQt6**: GUI framework
  - Creates the modern user interface
  - Handles drag & drop functionality
  - Manages application windows and dialogs

### Full Dependencies

See [requirements.txt](requirements.txt) for a complete list of dependencies and version requirements.
</details>

## 👥 Contributing

Contributions are welcome! Here's how you can help:

### Ways to Contribute

- 🐛 **Report bugs and issues**: Use the [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues) page to report bugs
- 💡 **Suggest new features**: Have an idea? Share it in the [Discussions](https://github.com/Mrtracker-new/Sortify/discussions) section
- 🧪 **Add tests**: Help improve reliability by adding tests for existing functionality
- 📝 **Improve documentation**: Fix typos, clarify explanations, or add examples
- 🔧 **Submit code**: Fix bugs or implement new features through pull requests
- 🌐 **Localization**: Help translate the application to other languages

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment as described in the Installation section
4. Create a new branch for your feature or bugfix
5. Make your changes and add appropriate tests
6. Run the test suite to ensure everything works
7. Submit a pull request with a clear description of the changes

### Coding Guidelines

- Follow PEP 8 style guidelines for Python code
- Write meaningful commit messages
- Include docstrings for all functions, classes, and modules
- Add unit tests for new functionality
- Update documentation to reflect your changes

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.

## 📬 Contact

<div align="center">

👤 **Author**: Rolan Lobo  
📧 **Email**: [rolanlobo901@gmail.com](mailto:rolanlobo901@gmail.com)  
🐞 **Issues**: [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues)

</div>
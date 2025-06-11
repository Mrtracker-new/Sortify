<div align="center">

# 🗂️ Sortify

**A smart file organization tool with AI-powered categorization**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

<img src="screenshots/Sortify.png" alt="Sortify Screenshot" width="600"/>

</div>

## 📋 Overview

Sortify is an intelligent file organization tool that automatically categorizes and organizes your files based on their formats, content, and metadata. This enhanced version includes powerful features to make file organization more efficient and intelligent.

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

### 📥 Installation

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

### 📚 User Guide

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
  - `nlp_parser.py`: Parses natural language commands

- **UI Components**:
  - `main_window.py`: Main interface with tabs
  - `settings_window.py`: Configuration interface for all features
</details>

<details>
<summary><b>Dependencies</b></summary>
<br>

Key dependencies:
- watchdog: For real-time file monitoring
- apscheduler: For scheduled tasks
- scikit-learn: For machine learning classification
- opencv-python: For image analysis
- nltk: For natural language processing
- spaCy: For advanced text analysis
</details>

## 👥 Contributing

Contributions are welcome! Here's how you can help:

- 🐛 Report bugs and issues
- 💡 Suggest new features or improvements
- 🧪 Add tests for existing functionality
- 📝 Improve documentation
- 🔧 Submit pull requests with bug fixes or features

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.

## 📬 Contact

<div align="center">

👤 **Author**: Rolan Lobo  
📧 **Email**: [rolanlobo901@gmail.com](mailto:rolanlobo901@gmail.com)  
🐞 **Issues**: [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues)

</div>
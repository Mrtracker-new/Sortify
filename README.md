# Sortify 📂✨

![Sortify Banner](screenshots/app_screenshot.png) 

**Your Smart File Organization Companion**  
*A PyQt6-powered desktop app that automates file sorting with military precision*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platforms: Win|Mac|Linux](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/Mrtracker-new/Sortify/releases)

---

## 🚀 Features That Will Blow Your Mind

### 📦 Smart Organization
- **Auto-categorization** for 100+ file types
- **Custom folder hierarchies** with nested subcategories
- **Drag & Drop** support for effortless file management

### ⚡ Power Tools
- **Time Machine** (Undo last action)
- **Operation History** with timestamp tracking
- **Deep Search** across multiple directories
- **Cross-platform** performance

### 🎯 Precision Sorting
| Category      | Supported Formats                          | Icon |
|---------------|--------------------------------------------|------|
| **Documents** | PDF, DOCX, TXT, ODT, EPUB, CSV, XLSX       | 📄   |
| **Media**     | MP4, MKV, MOV, MP3, FLAC, WAV              | 🎵   |
| **Images**    | JPG, PNG, WEBP, RAW, SVG, PSD              | 📸   |
| **Code**      | PY, JS, JAVA, CPP, HTML, CSS               | 👨💻 |
| **Archives**  | ZIP, RAR, 7Z, TAR.GZ                       | 🗃️  |

---

## ⚙️ Installation Made Easy

### For Everyone
1. [Download Latest Release](https://github.com/Mrtracker-new/Sortify/releases)
2. Unzip package
3. Run executable:
   - **Windows**: `Sortify.exe`
   - **macOS**: `./Sortify.app`
   - **Linux**: `./Sortify`

### For Developers

# Clone repo
git clone https://github.com/Mrtracker-new/Sortify.git
cd Sortify

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Launch application
python main.py
🎮 Usage Guide
Basic Workflow
Select Files
Drag & Drop Demo
Drag files or click "Add Files"

Choose Strategy

python
Copy
# Sample organization rules
RULES = {
    'Documents': ['.pdf', '.docx', '.txt'],
    'Code': ['.py', '.js', '.java'],
    # ... 100+ more rules
}
Execute Organization
Organization Demo

Pro Tips
Quick Undo: Ctrl+Z reverses last action

Deep Search: Use regex patterns for complex queries

Custom Rules: Edit config/rules.yaml to add new file types

🏗️ Folder Structure
bash
Copy
Organized_Folder/
├── Documents/
│   ├── PDF/           # All PDF files
│   ├── Word/          # DOC, DOCX, ODT
│   └── Spreadsheets/  # XLSX, CSV, ODS
├── Media/
│   ├── Music/         # MP3, FLAC, WAV
│   └── Videos/        # MP4, MKV, MOV
└── ... # 15+ categories
🛠️ Troubleshooting
Issue	Solution
File not recognized	Add extension to rules.yaml
Permission denied	Run as admin/root
Undo not working	Check history.log for errors
🤝 Contributing PRs Welcome
We ❤️ contributions! Here's how to help:

Fork the repository

Create your feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add some magic')

Push to branch (git push origin feature/AmazingFeature)

Open a Pull Request

📜 License
MIT License - See LICENSE for details.
"With great sorting power comes great responsibility" - Sortify Manifesto

📬 Contact
Author: Rolan Lobo
Email
Twitter <!-- Replace with actual -->

Made with ❤️ and ☕ by developers who hate messy folders

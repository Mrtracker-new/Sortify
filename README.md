<div align="center">

<img src="screenshots/Sortify.jpg" alt="Sortify Logo" width="200"/>

# 🗂️ Sortify

**Your Files Are a Mess. We Get It. Let's Fix That.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/Mrtracker-new/Sortify)](https://github.com/Mrtracker-new/Sortify/stargazers)

<img src="screenshots/Main_interface.png" alt="Sortify Main Interface" width="600"/>

[Features](#-features) • [Install](#-quick-start) • [Use It](#-how-to-use) • [Help](#-troubleshooting)

</div>

---

## 🤔 What Is This?

Your Downloads folder is a disaster. Your Desktop looks like a digital tornado hit it. "New Folder (47)" is mocking you.

**Sortify** is Marie Kondo for your computer (but less judgmental). It's a smart file organizer that:
- Actually **understands** your files (not just "ends in .jpg = image")
- Uses **AI** to categorize stuff intelligently
- **Watches folders** and sorts automatically
- Speaks **plain English** - just tell it what to do
- Has a **time machine** for when you mess up

---

## ✨ Features

### 🎯 Core Stuff
- **🔄 Auto-Sort** - Watches folders, sorts new files instantly
- **↩️ Full Undo/Redo** - Undo last action, entire sessions, or cherry-pick specific files
- **👀 Preview Mode** - See exactly what happens before files move
- **🛑 Cancel Button** - Changed your mind? Hit cancel mid-operation
- **🖱️ Drag & Drop** - Works exactly like you think
- **💬 Natural Language** - "Move all PDFs older than 30 days to Archive" ← it gets this

### 🧠 Smart Features
- **AI Categorization** - Reads file contents, not just extensions
- **Image Analysis** - Detects faces, screenshots, scanned docs
- **Social Media Sorting** - WhatsApp, Instagram, Telegram, etc. auto-sorted
- **Duplicate Finder** - Find and delete duplicate files safely
- **Session Management** - Groups operations for easy bulk undo

### 🔒 Reliability
- **Database Protection** - Triple-layer safety (even survives power loss)
- **Thread Safety** - No more crashes or database locks
- **Clean Exits** - Proper cleanup even when task-manager-murdered
- **Memory Management** - Zero leaks, background threads handled properly

---

## 🚀 Quick Start

### Requirements
- Python 3.8+ or Windows/macOS
- 4GB RAM (8GB for AI features)
- 150MB disk space

### Installation

**Option 1: Windows Installer** (Easiest)
1. Download from [Releases](https://github.com/Mrtracker-new/Sortify/releases)
2. Run installer
3. Find in Start menu

> Windows might complain about "unknown publisher" - we're just small and broke, not malicious.

**Option 2: From Source**
```bash
git clone https://github.com/Mrtracker-new/Sortify.git
cd Sortify
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```

**Option 3: CLI Mode** (For automation nerds)
```bash
# Preview first (dry run)
python main.py --dry-run --source "C:\Downloads" --organize

# Do it for real  
python main.py --yes --source "C:\Downloads" --organize
```

---

## 💡 How to Use

### GUI Mode (Point and Click)

**Quick Start:**
1. Launch Sortify
2. Drag files into the window OR click "Select Files"
3. Enable "Preview Mode" to see what happens (recommended first time)
4. Click "Organize Files"
5. Review preview → Click "Continue"

**Auto-Sort (Set and Forget):**
1. Click "Auto-Sort" toggle in toolbar
2. Select folder to watch
3. Choose destination
4. New files auto-organize instantly

**Undo Mistakes:**
- **Last action**: Click "Undo Last Action" in toolbar
- **Entire session**: History tab → Sessions → Select → "Undo"
- **Specific files**: History tab → Select operations → "Undo Selected"

**Natural Language:**
1. Go to Commands tab
2. Type: "Move all PDFs to Archive folder"
3. Hit Execute

### CLI Mode (For Scripts)

```bash
# Dry run (see what would happen)
python main.py --dry-run --source "/path/to/folder" --organize

# Auto-confirm everything
python main.py --yes --source "/path/to/folder" --organize

# Custom destination
python main.py --source "/downloads" --dest "/organized" --folder "MyFiles" --organize
```

---

## ❓ Troubleshooting

**Won't open?**
- Check Python version: `python --version` (need 3.8+)
- Reinstall dependencies: `pip install -r requirements.txt`
- Windows DLL errors? Install [Visual C++ Redistributables](https://aka.ms/vs/17/release/vc_redist.x64.exe)

**Not sorting files?**
- Check folder permissions (can you create files there?)
- File in use by another program? Close it
- Check if file type is supported

**AI seems dumb?**
- First run needs internet to download models
- Need 4GB+ RAM for AI features
- Try restarting the app

**Windows freaking out?**
- Add Sortify to Windows Defender exclusions
- We're not malware, Windows just hates unsigned software

---

## 👥 Contributing

Found a bug? Got an idea? Want to help?
- 🐛 [Report bugs](https://github.com/Mrtracker-new/Sortify/issues)
- 💡 [Share ideas](https://github.com/Mrtracker-new/Sortify/discussions)
- 🔧 Submit pull requests
- ⭐ Star the repo (it's free and makes us happy)

---

## 📄 License

MIT License - do whatever you want, just don't sue us. See [LICENSE](LICENSE) for legal stuff.

---

<div align="center">

👤 **Made by**: Rolan Lobo  
📧 **Email**: [rolanlobo901@gmail.com](mailto:rolanlobo901@gmail.com)  
🐞 **Report Bugs**: [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues)

---

*If this saved you from digital chaos, star the repo. Stars are free and we're broke.*

*Made with ❤️, ☕, and way too much Stack Overflow*

</div>

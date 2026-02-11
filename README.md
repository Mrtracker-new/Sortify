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

Your Downloads folder is a disaster zone. "New Folder (47)" is mocking you. Finding that one receipt from 2023 is a quest.

**Sortify** is your digital butler. It's a smart file organizer that uses **Local AI** to actually understand what your files are—not just "oh look, a .pdf".

- 🧠 **Smart & Private**: Uses **Sentence Transformers** directly on your PC. No data leaves your machine.
- 👁️ **Visual Intelligence**: Detects screenshots, documents, and even **AI-generated images** (Midjourney, ChatGPT, etc.).
- 🧹 **Social Media Tamer**: Automatically sorts those chaotic WhatsApp, Telegram, and Instagram filenames.
- 🛡️ **Safe & Sound**: Full **Undo** support and crash recovery. If it breaks, it cleans up after itself.

---

## ✨ Features

### 🧠 The Big Brain Stuff (AI)
- **Semantic Sorting** - Uses `all-MiniLM-L6-v2` to understand file context (e.g., invoices vs. recipes).
- **Privacy First** - Models run **locally**. No cloud uploads. Your data stays yours.
- **AI Image Detector** - Spots images made by DALL-E, Midjourney, or Stable Diffusion.
- **Smart Text Extraction** - Reads inside PDFs, Docs, and Images (OCR capable) to categorize correctly.

### 🛡️ The Safety Stuff
- **Undo/Redo** - Didn't mean to move that? One click fixes it.
- **Dry Run** - Preview exactly what will happen *before* it happens.
- **Conflict Handling** - Handles duplicates and collision gracefully.
- **Resilience** - Tracks extraction failures so you know if something wasn't read correctly.

### ⚡ The "Just Works" Stuff
- **Auto-Watch** - Set it to watch your Downloads folder and forget it exists.
- **Natural Language** - Type "Move all old screenshots to Trash" and it obeys.
- **Social Media Sorting** - Knows that `VID-2024...` belongs in "WhatsApp Video".

---

## 🚀 Quick Start

### Requirements
- Python 3.8+ (Windows/macOS/Linux)
- 4GB RAM (8GB recommended for AI features)
- ~500MB disk space (for AI models)

### Installation

**Option 1: Windows Installer** (Easiest)
1. Download from [Releases](https://github.com/Mrtracker-new/Sortify/releases)
2. Run it. (Ignore Windows Defender properly complaining about us being unsigned/broke).

**Option 2: From Source** (For the techies)
```bash
git clone https://github.com/Mrtracker-new/Sortify.git
cd Sortify
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

---

## 💡 How to Use

### 🖥️ GUI Mode
1. **Drag & Drop** files or pick a folder.
2. Click **"Organize Files"**.
3. Review the **Preview** (we insist!).
4. Hit **"Go"**.

To enable **Auto-Sort**, just toggle the switch in the toolbar and pick a folder to watch.

### 💻 CLI Mode (For Automation)
Want to run it on a server or cron job? We got you.

```bash
# Preview what would happen (Dry Run) - SAFE
python main.py --dry-run --source "C:\Downloads" --organize

# Actually do it (Auto-confirm) - YOLO
python main.py --yes --source "C:\Downloads" --organize
```

---

## ❓ Troubleshooting

- **AI Model Downloading...**: The first run might take a minute to download the Sentence Transformer model (~80MB). It's a one-time thing.
- **Textract Errors**: If some PDFs aren't reading, install `poppler` (check the docs).
- **Windows Warnings**: Yes, we know trying to run unsigned code scares Windows. Add an exclusion if it blocks us.

---

## 👥 Contributing
Found a bug? Want to add a feature?
- 🐛 [Report bugs](https://github.com/Mrtracker-new/Sortify/issues)
- ⭐ Star the repo (it validates our existence)

---

## 📄 License
MIT License. Do whatever, just don't blame us if you lose your homework (but you won't, because: Undo).

---

<div align="center">

👤 **Made by**: Rolan Lobo
📧 **Email**: [rolanlobo901@gmail.com](mailto:rolanlobo901@gmail.com)

*Made with ❤️, ☕, and local AI.*

</div>

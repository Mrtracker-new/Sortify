# Contributing to Sortify

**So You Want to Make Sortify Even Better? Awesome! Let's Do This! 🎉**

Thank you for considering contributing to Sortify! We're genuinely thrilled to have you here. This guide will help you get started without pulling your hair out.

---

## 📋 What's in This Guide

- [The Basics (Be Cool)](#-the-basics-be-cool)
- [Getting Your Dev Environment Ready](#-getting-your-dev-environment-ready)
- [How We Code (No Chaos Allowed)](#-how-we-code-no-chaos-allowed)
- [Testing Your Stuff](#-testing-your-stuff)
- [Submitting Your Masterpiece](#-submitting-your-masterpiece)
- [Found a Bug? Tell Us!](#-found-a-bug-tell-us)
- [Want a Feature? Let's Hear It!](#-want-a-feature-lets-hear-it)

---

## 🤝 The Basics (Be Cool)

**Our Code of Conduct is Simple:**
- **Be kind**: We're all learning. No one was born knowing Python.
- **Be constructive**: "This sucks" helps no one. "Here's how we could improve X" helps everyone.
- **Be inclusive**: Everyone's welcome here—beginners, experts, night owls, early birds, coffee addicts, tea enthusiasts, you name it.

Basically: Don't be a jerk, and we'll get along great! 😊

---

## 🚀 Getting Your Dev Environment Ready

### Step 1: Fork & Clone
1. **Fork this repo** on GitHub (hit that Fork button!)
2. **Clone your fork** to your machine:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Sortify.git
   cd Sortify
   ```
3. **Add the upstream repo** (so you can stay in sync):
   ```bash
   git remote add upstream https://github.com/Mrtracker-new/Sortify.git
   ```

### Step 2: Set Up Your Environment
We're civilized here—use a virtual environment! Your future self will thank you.

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install all the goodies
pip install -r requirements.txt

# Download the spaCy language model (for NLP magic)
python -m spacy download en_core_web_sm
```

**Pro Tip:** First launch might take a minute to download the Sentence Transformer model (~80MB). Perfect time for a coffee break ☕

---

## 📝 How We Code (No Chaos Allowed)

### Python Style: We Follow PEP 8 (Mostly)

Look, we're not monsters. We follow [PEP 8](https://pep8.org/) because it makes our code readable, not because we love rules.

#### Import Order (Keep It Clean)
```python
# 1. Standard library stuff first
import os
import sys
from pathlib import Path

# 2. Third-party libraries next
import spacy
from PyQt6.QtWidgets import QApplication

# 3. Our own code last
from core.categorization import FileCategorizationAI
from ui.main_window import MainWindow
```

#### Naming Conventions (So We Don't Get Confused)
- **Classes**: `PascalCase` → `FileOperations`, `AIFileClassifier`
- **Functions/Methods**: `snake_case` → `categorize_file()`, `load_model()`
- **Constants**: `UPPER_SNAKE_CASE` → `MAX_FILE_SIZE`, `DEFAULT_TIMEOUT`
- **Private stuff**: Prefix with `_` → `_internal_helper()`

#### Write Docstrings (Future You Will Love You)
Every function should explain what it does. Example:

```python
def categorize_file(self, file_path):
    """Categorize a file based on its content and metadata
    
    Args:
        file_path (str or Path): Path to the file to categorize
        
    Returns:
        str: Category like 'documents/invoices' or 'images/screenshots'
        
    Raises:
        FileNotFoundError: If the file doesn't exist (obviously)
    """
    # Your brilliant code here
```

#### Error Handling (Don't Hide Problems)

**Bad** (please don't do this):
```python
try:
    do_something()
except:
    pass  # 🔥 Problem? What problem? 🔥
```

**Good** (yes, do this):
```python
try:
    do_something()
except FileNotFoundError as e:
    logging.error(f"File not found: {e}")
    raise  # Let the caller know something went wrong
except PermissionError as e:
    logging.warning(f"Permission denied: {e}")
    return False  # Graceful degradation
```

#### Type Hints Are Your Friends
They're optional but **highly encouraged**. Your IDE will love you for it:

```python
from typing import Optional, List, Dict
from pathlib import Path

def move_file(self, source: Path, destination: str) -> Optional[Path]:
    """Move a file (with type hints so VS Code stops yelling at you)"""
    # Implementation
```

### Code Quality Tips

#### Don't Repeat Yourself (DRY)
If you're copy-pasting the same logic three times, **stop**. Make it a helper function.

```python
# Bad: Repetitive code
result1 = process_pdf(file1)
result2 = process_pdf(file2)
result3 = process_pdf(file3)

# Good: Loop or helper function
results = [process_pdf(f) for f in [file1, file2, file3]]
```

#### Keep Functions Small
- **One function, one job**. If it does 5 things, split it into 5 functions.
- **Aim for under 50 lines**. If it's longer, refactor it.
- **Use descriptive names**: `categorize_file()` >> `do_stuff()`

#### Variables Should Make Sense
```python
# Bad (what the heck is 'x'?)
x = get_files()
for f in x:
    process(f)

# Good (ah, now I get it!)
file_paths = get_files()
for file_path in file_paths:
    process_file(file_path)
```

### Platform Compatibility (Windows, Mac, Linux—We Support 'Em All)

When writing platform-specific code, use proper checks:

```python
import os

if os.name == 'nt':  # Windows
    # Windows-specific stuff (icacls, win32api, etc.)
    pass
else:  # Unix-like (Linux, macOS)
    # Unix stuff (chmod, etc.)
    pass
```

**Never** hardcode paths like `C:\\Users\\...` or assume everyone uses forward slashes. Use `pathlib.Path` instead!

---

## 🧪 Testing Your Stuff

We don't deploy bugs to production. Here's how to make sure your code works:

### Running Tests
```bash
# Run everything
python -m pytest

# Run one specific test file
python -m pytest tests/test_categorization.py

# Run with coverage report
python -m pytest --cov=core --cov=ui
```

### Writing Tests (Yes, You Need Them)
- **Write unit tests** for new features
- **Aim for 70%+ code coverage** (the more, the better)
- **Test edge cases**: What if the file doesn't exist? What if it's 0 bytes? What if it's 10 GB?

**Example:**
```python
import pytest
from core.categorization import FileCategorizationAI

def test_categorize_image_file():
    """Test that JPEGs go to the images folder"""
    categorizer = FileCategorizationAI()
    result = categorizer.categorize_file("vacation.jpg")
    assert result.startswith("images/")

def test_categorize_nonexistent_file():
    """Test that nonexistent files raise an error"""
    categorizer = FileCategorizationAI()
    with pytest.raises(FileNotFoundError):
        categorizer.categorize_file("this_file_does_not_exist.txt")
```

---

## 📤 Submitting Your Masterpiece

### Commit Messages (Make Them Meaningful)

We use [Conventional Commits](https://www.conventionalcommits.org/). It sounds fancy but it's simple:

```
type(scope): what you did in ~50 characters

Optional longer explanation if needed.

Fixes #123
```

**Types:**
- `feat`: New feature (e.g., `feat(ai): add HEIC image support`)
- `fix`: Bug fix (e.g., `fix(database): resolve Windows permission error`)
- `docs`: Documentation (e.g., `docs(readme): update install instructions`)
- `refactor`: Code cleanup (e.g., `refactor(main): consolidate permission checks`)
- `test`: Tests (e.g., `test(categorization): add tests for edge cases`)
- `chore`: Boring stuff (e.g., `chore: update dependencies`)

**Examples:**
```bash
git commit -m "feat(categorization): add support for RAW image formats"
git commit -m "fix(undo): handle missing target files gracefully"
git commit -m "docs(contributing): make guide more human-friendly"
```

### Pull Request Workflow

1. **Create a branch** for your feature:
   ```bash
   git checkout -b feat/your-amazing-feature
   ```

2. **Make your changes** and commit:
   ```bash
   git add .
   git commit -m "feat: add your amazing feature"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feat/your-amazing-feature
   ```

4. **Open a Pull Request** on GitHub with:
   - **Clear description** of what you changed and why
   - **Link to related issues** (e.g., "Fixes #42")
   - **Screenshots** if you changed the UI
   - **Test results** (did everything pass?)

5. **Wait for feedback** and be ready to make changes (we're nice, promise!)

### PR Checklist (Before Hitting "Submit")

- [ ] Code follows PEP 8 style
- [ ] All tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated documentation (README, docstrings)
- [ ] Commit messages follow the convention
- [ ] No merge conflicts with `main`
- [ ] You tested it yourself (seriously, run it!)

---

## 🐛 Found a Bug? Tell Us!

**Step 1:** Check if someone else already reported it in [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues).

**Step 2:** If not, create a new issue with:

1. **Clear title**: "Database locks on Windows 11" (not "It's broken!!!")
2. **How to reproduce**: Step-by-step instructions
3. **Expected vs. actual behavior**: What *should* happen vs. what *did* happen
4. **Your environment**:
   - OS (Windows 11, Ubuntu 22.04, macOS 14, etc.)
   - Python version (`python --version`)
   - Sortify version
5. **Error messages**: Copy-paste from the logs
6. **Screenshots**: If relevant

### Bug Report Template

```markdown
**What's Broken:**
Brief description (e.g., "App crashes when sorting PDFs")

**How to Reproduce:**
1. Open Sortify
2. Drag a PDF into the window
3. Click "Organize Files"
4. 💥 Crash

**Expected:**
PDF should be categorized without crashing

**Actual:**
App crashes with "FileNotFoundError"

**Environment:**
- OS: Windows 11 Pro
- Python: 3.11.5
- Sortify: 1.2.0

**Error Log:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\temp\\test.pdf'
```

**Screenshots:**
[Attach if helpful]
```

---

## 💡 Want a Feature? Let's Hear It!

We **love** feature requests! Here's how to suggest one:

1. **Check existing issues** to avoid duplicates
2. **Describe the feature** clearly (what does it do?)
3. **Explain the use case** (why is it useful?)
4. **Be realistic** (e.g., "Add AI voice control" is cool but out of scope)

**Example:**
> **Feature Request:** Add support for Markdown file categorization
> 
> **Use Case:** As a developer, I have tons of `.md` files (READMEs, notes, docs) that get mixed with regular text files. I'd like Sortify to detect and categorize Markdown files separately.
> 
> **Why It's Useful:** Better organization for devs and technical writers.

---

## 📚 Resources for Contributors

- [Python PEP 8 Style Guide](https://pep8.org/) - The holy grail of Python style
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/) - For UI wizards
- [spaCy Documentation](https://spacy.io/) - For NLP nerds
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/) - Git workflow basics

---

## 🙏 Thank You!

Seriously, **thank you** for contributing! Whether you're fixing a typo or adding a major feature, every bit helps make Sortify better for everyone.

If you have questions, don't hesitate to reach out:
- 📧 Email: [rolanlobo901@gmail.com](mailto:rolanlobo901@gmail.com)
- 🐞 Issues: [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues)

---

**Now go forth and code! 🚀**

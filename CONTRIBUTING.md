# Contributing to Sortify

Thank you for your interest in contributing to Sortify! This document provides guidelines and best practices for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

## 🚀 Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Sortify.git
   cd Sortify
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/Mrtracker-new/Sortify.git
   ```

## 💻 Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Download spaCy language model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## 📝 Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) style guidelines. Key points:

#### Import Order
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import spacy
from PyQt6.QtWidgets import QApplication

# Local application imports
from core.categorization import FileCategorizationAI
from ui.main_window import MainWindow
```

#### Naming Conventions
- **Classes**: `PascalCase` (e.g., `FileOperations`, `AIFileClassifier`)
- **Functions/Methods**: `snake_case` (e.g., `categorize_file`, `load_model`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`, `DEFAULT_TIMEOUT`)
- **Private methods**: Prefix with underscore (e.g., `_set_windows_file_permissions`)

#### Documentation
All functions and classes should have docstrings:

```python
def categorize_file(self, file_path):
    """Categorize a file based on its content and metadata
    
    Args:
        file_path (str or Path): Path to the file to categorize
        
    Returns:
        str: Category path in format 'category/subcategory'
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    # Implementation here
```

#### Error Handling
- Use specific exceptions, not bare `except:` clauses
- Log errors appropriately
- Provide meaningful error messages

```python
# Bad
try:
    do_something()
except:
    pass

# Good
try:
    do_something()
except FileNotFoundError as e:
    logging.error(f"File not found: {e}")
    raise
except PermissionError as e:
    logging.warning(f"Permission denied: {e}")
    return False
```

#### Type Hints (Encouraged)
```python
from typing import Optional, List, Dict
from pathlib import Path

def move_file(self, source_path: Path, category_path: str) -> Optional[Path]:
    """Move file to appropriate category folder"""
    # Implementation
```

### Code Quality

#### Avoid Code Duplication
- Extract common logic into helper functions
- Use inheritance and composition appropriately
- Follow the DRY (Don't Repeat Yourself) principle

#### Keep Functions Focused
- Each function should do one thing well
- Aim for functions under 50 lines
- Break complex functions into smaller helpers

#### Use Descriptive Variable Names
```python
# Bad
x = get_files()
for f in x:
    process(f)

# Good
file_paths = get_files()
for file_path in file_paths:
    process_file(file_path)
```

### Platform Compatibility

When writing platform-specific code, use proper checks:

```python
import os

if os.name == 'nt':  # Windows
    # Windows-specific code
    pass
else:  # Unix-like (Linux, macOS)
    # Unix-specific code
    pass
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_categorization.py

# Run with coverage
python -m pytest --cov=core --cov=ui
```

### Writing Tests
- Write unit tests for new functionality
- Aim for at least 70% code coverage
- Test edge cases and error conditions

```python
import pytest
from core.categorization import FileCategorizationAI

def test_categorize_image_file():
    """Test that image files are correctly categorized"""
    categorizer = FileCategorizationAI()
    result = categorizer.categorize_file("test.jpg")
    assert result.startswith("images/")

def test_categorize_nonexistent_file():
    """Test handling of nonexistent files"""
    categorizer = FileCategorizationAI()
    with pytest.raises(FileNotFoundError):
        categorizer.categorize_file("nonexistent.txt")
```

## 📤 Submitting Changes

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): brief description

Longer description if needed

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(categorization): add support for HEIC image format

fix(database): resolve permission error on Windows

docs(readme): update installation instructions

refactor(main): consolidate duplicate database permission code
```

### Pull Request Process

1. Create a new branch for your feature:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

3. Push to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```

4. Open a Pull Request on GitHub with:
   - Clear description of changes
   - Link to related issues
   - Screenshots (if UI changes)
   - Test results

5. Wait for review and address feedback

### PR Checklist

- [ ] Code follows PEP 8 style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, docstrings)
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

## 🐛 Reporting Bugs

Use the [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues) page with:

1. **Clear title** describing the issue
2. **Steps to reproduce** the bug
3. **Expected behavior** vs actual behavior
4. **Environment details**:
   - OS and version
   - Python version
   - Sortify version
5. **Error messages** and logs
6. **Screenshots** (if applicable)

### Bug Report Template

```markdown
**Description:**
Brief description of the bug

**To Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: Windows 11 / Ubuntu 22.04 / macOS 13
- Python: 3.10.5
- Sortify: 1.0.0

**Error Messages:**
```
Paste error messages here
```

**Screenshots:**
[If applicable]
```

## 💡 Feature Requests

Feature requests are welcome! Please:

1. Check if the feature already exists or is requested
2. Clearly describe the feature and use case
3. Explain why it would be useful
4. Consider implementation complexity

## 📚 Resources

- [Python PEP 8 Style Guide](https://pep8.org/)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [spaCy Documentation](https://spacy.io/)
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)

## 🙏 Thank You!

Every contribution helps make Sortify better. Thank you for taking the time to contribute!

---

**Questions?** Feel free to reach out:
- 📧 Email: rolanlobo901@gmail.com
- 🐞 Issues: [GitHub Issues](https://github.com/Mrtracker-new/Sortify/issues)

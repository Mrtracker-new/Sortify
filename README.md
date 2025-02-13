# Sortify

A powerful desktop application built with PyQt6 that helps you organize your files automatically based on their types. The application provides an intuitive interface for managing and organizing files across your system.

![File Organizer Screenshot](screenshots/app_screenshot.png)

## Features

- **Smart File Organization**: Automatically organizes files into categorized folders based on file types
- **Detailed Categories**: Files are sorted into specific subfolders for better organization:
  - Documents (PDF, Word, Text, Spreadsheets, Presentations)
  - Images (Photos, PNG, Graphics, RAW, Design)
  - Audio (Music, Lossless, Playlists, Voice)
  - Video (Movies, TV, Mobile, Web)
  - Archives (ZIP, RAR, Disk, Compressed)
  - Code (Python, Web, Java, C/C++, Scripts)
  - And many more...
- **File Search**: Search for files across directories
- **Drag & Drop**: Easy file selection through drag and drop
- **Undo Feature**: Ability to undo the last organization/move operation
- **Operation History**: Keep track of all file movements
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

1. Download the latest release for your operating system
2. Extract the downloaded file
3. Run the executable:
   - Windows: `FileOrganizer.exe`
   - macOS/Linux: `FileOrganizer`

## Building from Source

### Prerequisites
- `Python 3.8` or higher
- `PyQt6`
- Required Python packages (install using pip):

      pip install -r requirements.txt

### Build Steps
1. Clone the repository:
   
       git clone https://github.com/yourusername/Sortify.git
       cd Sortify

Install dependencies:

    pip install -r requirements.txt

Build the executable:

    python build.py

The executable will be created in the `dist` directory.

## Usage

1. **Select Files**:
   - Click "Select Files" to choose files
   - Or drag and drop files into the application window

2. **Organize Files**:
   - Choose a category from the dropdown (or "All Categories")
   - Click "Organize Files"
   - Select destination directory
   - Files will be automatically sorted into appropriate folders

3. **Search Files**:
   - Enter search term in the search bar
   - Click "Search"
   - Select directory to search in
   - Found files will be listed and can be organized

4. **Undo Operations**:
   - Click "Undo Last Action" to reverse the most recent file movement
   - The operation history shows all recent file movements

## File Organization Structure
Selected Directory/
├── Documents/
│ ├── PDF/
│ ├── Word/
│ ├── Text/
│ ├── Spreadsheets/
│ ├── Presentations/
│ └── eBooks/
├── Images/
│ ├── Photos/
│ ├── PNG/
│ ├── Graphics/
│ ├── RAW/
│ └── Design/
├── Audio/
│ ├── Music/
│ ├── Lossless/
│ ├── Playlists/
│ └── Voice/
└── ... (other categories)
## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PyQt6 for the GUI framework
- All contributors who have helped with the project
- Icons from [insert icon source]

## Support

If you encounter any issues or have questions, please:
1. Check the [Issues](https://github.com/Mrtracker-new/Sortify/issues) page
2. Create a new issue if your problem isn't already listed

## Author

Rolan LObo - [rolanlobo901@gmail.com]


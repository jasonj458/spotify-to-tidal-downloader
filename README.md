# Spotify to Tidal Transfer Tool

A Python application that allows users to transfer playlists from Spotify to Tidal, with the ability to download and convert songs to MP3 format.

## Features

- Transfer playlists from Spotify to Tidal
- Download songs from Tidal
- Convert downloaded songs to MP3 format
- Modern GUI interface
- Authentication management for both Spotify and Tidal
- Progress tracking and error handling

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed and available in system PATH
- WSL (Windows Subsystem for Linux) for file operations
- Spotify Developer account
- Tidal account

### System Requirements

1. **Windows 10 or later**
   - Must be a 64-bit system
   - Windows Subsystem for Linux (WSL) must be installed and configured

2. **WSL Setup**
   - Install WSL by running in PowerShell as Administrator:
     ```powershell
     wsl --install
     ```
   - After installation, restart your computer
   - Set up a Linux username and password when prompted
   - Verify WSL is working by running:
     ```powershell
     wsl --status
     ```

3. **FFmpeg Installation**
   - Download FFmpeg from https://ffmpeg.org/download.html
   - Extract the downloaded files
   - Add FFmpeg's bin directory to your system PATH:
     1. Open System Properties > Advanced > Environment Variables
     2. Under System Variables, find and select "Path"
     3. Click Edit > New
     4. Add the path to FFmpeg's bin directory (e.g., `C:\ffmpeg\bin`)
     5. Click OK to save
   - Verify installation by running:
     ```powershell
     ffmpeg -version
     ```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/spotify-to-tidal.git
cd spotify-to-tidal
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Spotify Developer credentials:
   - Create a new application at https://developer.spotify.com/dashboard
   - Add `http://localhost:8888/callback` to the Redirect URIs
   - Update the credentials in the application settings

4. Set up your Tidal credentials:
   - Log in to your Tidal account
   - The application will handle the authentication process

5. Build the application using the provided build script:
```bash
python build.py
```
   This script will:
   - Check for all required files
   - Install necessary dependencies
   - Create the executable in the `dist` directory
   - Generate a README.txt with usage instructions

## Usage

1. Navigate to the `dist` directory and run the executable:
   - Windows: Double-click `SpotifyToTidal.exe`
   - Or run from command line: `./SpotifyToTidal.exe`

2. Authenticate with Spotify and Tidal when prompted
3. Enter the Spotify playlist URL
4. Select the destination folder for downloads
5. Wait for the transfer and conversion process to complete

Note: The application must be built before it can be run. Running the Python script directly is not supported.

## Troubleshooting

If the application crashes or fails to start:

1. **Authentication Issues**
   - Check if the AppData directory exists:
     ```powershell
     dir %LOCALAPPDATA%\SpotifyToTidal
     ```
   - If it doesn't exist, create it:
     ```powershell
     mkdir %LOCALAPPDATA%\SpotifyToTidal
     ```
   - Delete any existing authentication files and try again:
     ```powershell
     del %LOCALAPPDATA%\SpotifyToTidal\*.pkl
     del %LOCALAPPDATA%\SpotifyToTidal\app_settings.json
     ```
   - Make sure you have proper permissions to access the AppData directory
   - Try running the application as administrator

2. **WSL Issues**
   - Verify WSL is installed and running:
     ```powershell
     wsl --status
     ```
   - If WSL is not installed, run:
     ```powershell
     wsl --install
     ```
   - If WSL is installed but not working, try:
     ```powershell
     wsl --shutdown
     wsl --update
     ```
   - Verify WSL user setup:
     ```powershell
     wsl -u root
     ```
   - If prompted for a username/password, set them up
   - Make sure WSL has proper permissions to access Windows files

3. **FFmpeg Issues**
   - Verify FFmpeg is installed in WSL:
     ```powershell
     wsl bash -c "which ffmpeg"
     ```
   - If not found, install FFmpeg in WSL:
     ```powershell
     wsl bash -c "sudo apt update && sudo apt install -y ffmpeg"
     ```
   - Verify FFmpeg works:
     ```powershell
     wsl bash -c "ffmpeg -version"
     ```

4. **Build Issues**
   - Ensure all required files are present:
     - SpotifyToTidal.py
     - requirements.txt
     - SpotifyToTidal.spec
     - logo.png
     - mp3icon.png
     - sun.png
     - moon.png
   - Try rebuilding with:
     ```bash
     python build.py
     ```

5. **Runtime Issues**
   - Check Windows Event Viewer for application errors
   - Ensure you have administrator privileges
   - Try running the application as administrator
   - Check if antivirus is blocking the application
   - Verify Windows Defender settings

6. **Common Error Messages**
   - "Settings file not found": The application can't find the configuration files in AppData
   - "Tidal session invalid": The Tidal authentication has expired or is corrupted
   - "WSL not found": Windows Subsystem for Linux is not properly installed
   - "FFmpeg not found": FFmpeg is not installed in WSL or not in PATH
   - "Permission denied": The application doesn't have proper permissions to access files

For additional help or if issues persist, please open an issue on GitHub with:
1. The exact error message
2. Steps to reproduce the issue
3. Your system information (Windows version, WSL version)
4. Any relevant error logs from Event Viewer

## Configuration

The application uses a configuration file (`app_settings.json`) to store settings. This file is created automatically on first run and can be modified to change default settings.

## Building from Source

To create an executable, use the provided build script:

```bash
python build.py
```

The executable will be created in the `dist` directory. This is the recommended way to run the application.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Uses spotipy for Spotify API integration
- Uses tidalapi for Tidal API integration
- Uses PyQt5 for the GUI
- Uses FFmpeg for audio conversion 
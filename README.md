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

## Important Notes

1. **Building Requirements**:
   - Always use `build.py` to create the executable
   - The build script ensures all dependencies are properly included
   - Running the executable on other PCs requires the same build process

2. **System Requirements**:
   - Windows 10 or later
   - WSL (Windows Subsystem for Linux) installed and configured
   - FFmpeg installed and available in system PATH
   - Internet connection for Spotify and Tidal authentication

3. **First Run**:
   - The application will create necessary directories in your AppData folder
   - You'll need to authenticate with both Spotify and Tidal
   - You'll need to provide your WSL sudo password for file operations

4. **Troubleshooting**:
   - If the application crashes on other PCs, ensure all system requirements are met
   - Verify WSL is properly installed and configured
   - Check that FFmpeg is installed and accessible in the system PATH
   - Ensure all authentication files are properly created in the AppData folder

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
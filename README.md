# Spotify to Tidal Transfer & Downloader

A modern desktop application that allows you to transfer your playlists, albums, and tracks from Spotify to Tidal, with the ability to download the content directly to your computer.

## Features

- 🎵 Transfer playlists, albums, and tracks from Spotify to Tidal
- 💾 Download content directly to your computer
- 🎧 Convert downloaded files to MP3 format
- 🌓 Light and dark mode support
- 🔒 Secure password handling
- 🎨 Modern and intuitive user interface

## Requirements

- Windows 10/11 with WSL (Windows Subsystem for Linux) installed
- Python 3.8 or higher
- FFmpeg (will be installed automatically if not present)
- Spotify account
- Tidal account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/spotify-to-tidal.git
cd spotify-to-tidal
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Build the application:
```bash
python build.py
```

The executable will be created in the `dist` directory.

## Usage

1. Run the application:
```bash
.\dist\SpotifyToTidal.exe
```

2. Log in to your Spotify and Tidal accounts when prompted
3. Enter a Spotify playlist, album, or track URL
4. Choose whether to convert files to MP3 format
5. Select an output folder
6. Click "Transfer to Tidal" to create a Tidal playlist
7. Click "Download from Tidal" to download the content

## Configuration

The application stores its configuration in `app_settings.json`. You can modify settings such as:
- Download quality
- Output format
- File naming patterns
- UI preferences

## Building from Source

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Run the build script:
```bash
python build.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [tidal-dl-ng](https://github.com/yaronzz/Tidal-Media-Downloader) for the download functionality
- [spotipy](https://github.com/spotipy-dev/spotipy) for Spotify API integration
- [tidalapi](https://github.com/tamland/python-tidal) for Tidal API integration
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework 
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all PyQt5 plugins and data files
qt_plugins = collect_data_files('PyQt5', include_py_files=True)
qt_modules = collect_submodules('PyQt5')

# Get the path to the user's home directory
home_dir = os.path.expanduser('~')
app_data_dir = os.path.join(home_dir, 'AppData', 'Local', 'SpotifyToTidal')

# Create runtime hook content
runtime_hook_content = """
import os
import sys
import json

def create_app_directories():
    # Create app data directory
    home_dir = os.path.expanduser('~')
    app_data_dir = os.path.join(home_dir, 'AppData', 'Local', 'SpotifyToTidal')
    os.makedirs(app_data_dir, exist_ok=True)
    
    # Create default settings if they don't exist
    settings_file = os.path.join(app_data_dir, 'app_settings.json')
    if not os.path.exists(settings_file):
        default_settings = {
            "spotify_config": {
                "client_id": "YOUR_SPOTIFY_CLIENT_ID",
                "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
                "redirect_uri": "http://localhost:8888/callback"
            },
            "tidal_dl_ng_config": {
                "skip_existing": True,
                "lyrics_embed": False,
                "lyrics_file": False,
                "video_download": True,
                "download_delay": True,
                "download_base_path": "",
                "quality_audio": "HIGH",
                "quality_video": "480",
                "format_album": "Albums/{album_artist} - {album_title}{album_explicit}/{track_volume_num_optional}{album_track_num}",
                "format_playlist": "Playlists/{playlist_name}/{list_pos}. {artist_name} - {track_title}",
                "format_mix": "Mix/{mix_name}/{artist_name} - {track_title}",
                "format_track": "Tracks/{artist_name} - {track_title}{track_explicit}",
                "format_video": "Videos/{artist_name} - {track_title}{track_explicit}",
                "video_convert_mp4": True,
                "metadata_cover_dimension": "320",
                "metadata_cover_embed": True,
                "cover_album_file": True,
                "extract_flac": True,
                "downloads_simultaneous_per_track_max": 20,
                "download_delay_sec_min": 3.0,
                "download_delay_sec_max": 5.0,
                "album_track_num_pad_min": 1,
                "downloads_concurrent_max": 3,
                "symlink_to_track": False
            },
            "tidal_session_file": "tidal_session.pkl",
            "similarity_threshold": 70,
            "dark_mode": False,
            "convert_to_mp3_only": False,
            "ui": {
                "light_background": "#FFFFFF",
                "light_surface": "#FFFFFF",
                "light_border_color": "#E0E0E0",
                "light_text": "rgba(0,0,0,0.87)",
                "dark_background": "#1C1B1F",
                "dark_surface": "#1C1B1F",
                "dark_border_color": "#3F3A46",
                "dark_text": "rgba(255,255,255,0.87)",
                "primary_color": "#6750A4",
                "primary_variant": "#625B71",
                "secondary_color": "#03DAC6",
                "border_radius": "12px",
                "toggle_unchecked_icon": "sun.png",
                "toggle_checked_icon": "moon.png",
                "window_icon": "logo.png",
                "scrollbar_width": "8px",
                "scrollbar_light_handle": "#BDBDBD",
                "scrollbar_light_handle_hover": "#9E9E9E",
                "scrollbar_dark_handle": "#444444",
                "scrollbar_dark_handle_hover": "#666666"
            }
        }
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=4)

# Create directories when the application starts
create_app_directories()
"""

# Write runtime hook to file
with open('runtime_hook.py', 'w') as f:
    f.write(runtime_hook_content)

a = Analysis(
    ['SpotifyToTidal.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
        ('mp3icon.png', '.'),
        ('sun.png', '.'),
        ('moon.png', '.'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'spotipy',
        'tidalapi',
        'rapidfuzz',
        'cryptography',
        'subprocess',
        'os',
        'sys',
        'json',
        'pickle',
        'platform',
        'shutil',
        'hashlib',
        'base64',
        'traceback',
        'typing',
        'logging',
        're',
        'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SpotifyToTidal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
) 
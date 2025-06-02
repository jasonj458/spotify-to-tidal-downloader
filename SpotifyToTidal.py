#!/usr/bin/env python3

import os
import sys
import re
import json
import time
import pickle
import subprocess
import platform
import logging
import shutil
import hashlib
import base64
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Add cryptography for password encryption
try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = Exception

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QVBoxLayout, QMessageBox, QProgressBar, QFrame,
                             QScrollArea, QHBoxLayout, QFileDialog, QDialog, QCheckBox,
                             QGraphicsOpacityEffect, QInputDialog, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QProcess, QEventLoop, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import tidalapi
from rapidfuzz import fuzz

# Import the auth setup window
from auth_setup import AuthSetupWindow

# Import the TidalLoginDialog from tidal_login_dialog.py
from tidal_login_dialog import TidalLoginDialog

# ------------------- Default Settings -------------------
SIMILARITY_THRESHOLD = 80  # Fuzzy match threshold for track matchings

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
        "symlink_to_track": False,
        "path_binary_ffmpeg": ""
    },
    "ui": {
        "window_icon": "logo.png",
        "toggle_unchecked_icon": "toggle_unchecked.png",
        "toggle_checked_icon": "toggle_checked.png"
    },
    "convert_to_mp3_only": False,
    "dark_mode": False,
    "download_folder": ""
}

# ------------------- Logging Setup -------------------
# Create separate loggers for GUI and debug logs
gui_logger = logging.getLogger('gui')
debug_logger = logging.getLogger('debug')

# Configure debug logger for terminal output
debug_handler = logging.StreamHandler()
debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
debug_logger.addHandler(debug_handler)
debug_logger.setLevel(logging.DEBUG)

# Configure GUI logger with minimal formatting
gui_handler = logging.StreamHandler()
gui_handler.setFormatter(logging.Formatter('%(message)s'))
gui_logger.addHandler(gui_handler)
gui_logger.setLevel(logging.INFO)

# Custom logging function to handle different log levels and destinations
def log_message(message: str, level: str = "INFO", gui_only: bool = False) -> None:
    """Log a message with the specified level and destination.
    
    Args:
        message: The message to log
        level: Log level (INFO, WARNING, ERROR, DEBUG)
        gui_only: If True, only log to GUI, not to debug logger
    """
    # Always log to debug logger unless gui_only is True
    if not gui_only:
        if level == "ERROR":
            debug_logger.error(message)
        elif level == "WARNING":
            debug_logger.warning(message)
        elif level == "DEBUG":
            debug_logger.debug(message)
        else:
            debug_logger.info(message)
    
    # Log to GUI logger only for user-friendly messages
    if level == "ERROR":
        gui_logger.error(message)
    elif level == "WARNING":
        gui_logger.warning(message)
    else:
        gui_logger.info(message)

def check_authentication() -> bool:
    """Check if Tidal authentication is valid."""
    try:
        # Check if settings file exists
        if not os.path.exists(SETTINGS_FILE):
            log_message("Settings file not found", "DEBUG")
            return False
            
        # Load settings
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            
        # Check Tidal session
        if not os.path.exists(TIDAL_SESSION_FILE):
            log_message("Tidal session file not found", "DEBUG")
            return False
            
        # Verify Tidal session
        try:
            with open(TIDAL_SESSION_FILE, "rb") as f:
                session = pickle.load(f)
            if not session.check_login():
                log_message("Tidal session invalid", "DEBUG")
                return False
            log_message("Tidal session verified", "DEBUG")
        except Exception as e:
            log_message(f"Tidal session verification failed: {str(e)}", "DEBUG")
            return False
            
        log_message("Authentication check passed", "DEBUG")
        return True
        
    except Exception as e:
        log_message(f"Error checking authentication: {str(e)}", "ERROR")
        import traceback
        log_message(f"Traceback: {traceback.format_exc()}", "ERROR")
        return False

# ------------------- Main Application UI -------------------
class SpotifyToTidalApp(QWidget):
    """Main application window."""
    def __init__(self) -> None:
        super().__init__()
        self.setup_application()
        self.setup_ui()
        self.apply_theme()
        
        # Load Spotify credentials from config
        spotify_config = _app_settings.get("spotify_config", {})
        client_id = spotify_config.get("client_id")
        client_secret = spotify_config.get("client_secret")
        redirect_uri = spotify_config.get("redirect_uri")
        if not client_id or not client_secret or not redirect_uri or client_id == "YOUR_SPOTIFY_CLIENT_ID" or client_secret == "YOUR_SPOTIFY_CLIENT_SECRET":
            QMessageBox.critical(
                self,
                "Spotify Credentials Missing",
                "Spotify credentials are missing or invalid. Please restart the app and complete authentication."
            )
            sys.exit(1)
        # Initialize Spotify client using saved credentials
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            cache_path=SPOTIFY_TOKEN_CACHE
        ))
        # Now initialize transfer manager with debug_logger
        self.manager = TransferManager(debug_logger, self.sp, self)
        
        # Initialize Spotify client
        try:
            spotify_auth = SpotifyAuthManager(self)
            self.sp = spotify_auth.get_spotify_client()
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Spotify Login Error", 
                f"Failed to log in to Spotify: {str(e)}\nPlease try again."
            )
            sys.exit(1)
            
        # Verify installations and setup
        try:
            if platform.system() == "Windows":
                # Get sudo password first
                sudo_pass = get_or_prompt_sudo_password(self)
                if not sudo_pass:
                    QMessageBox.critical(
                        self, 
                        "Error", 
                        "Sudo password is required for installation."
                    )
                    sys.exit(1)

                if not ensure_tidal_dl_ng_installed(self):
                    QMessageBox.critical(
                        self, 
                        "Installation Error", 
                        "tidal-dl-ng installation failed. Please ensure WSL is properly installed and configured."
                    )
                    sys.exit(1)
                    
            if not ensure_ffmpeg_installed(self):
                QMessageBox.critical(
                    self,
                    "FFmpeg Error",
                    "FFmpeg installation failed. Please install FFmpeg manually."
                )
                sys.exit(1)
                
            ensure_ffmpeg_path_set(self)
            
            # Try to login to Tidal
            try:
                self.manager.login_tidal()
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Tidal Login Error", 
                    f"Failed to log in to Tidal: {str(e)}\nPlease try again."
                )
                sys.exit(1)
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize application: {str(e)}"
            )
            sys.exit(1)
            
        self.playlist_url: Optional[str] = None
        self.total_tracks: int = 0
        self.download_thread: Optional[DownloadThread] = None

    def setup_application(self) -> None:
        """Configure application settings."""
        self.setWindowTitle("Spotify to Tidal Transfer & Downloader")
        self.setMinimumSize(1000, 800)
        self.setWindowIcon(QIcon(_app_settings.get("ui", {}).get("window_icon", "logo.png")))

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Modern font setup
        modern_font = QFont("Inter", 11)
        modern_font.setWeight(QFont.Medium)
        bold_font = QFont("Inter", 14, QFont.Bold)
        header_font = QFont("Inter", 22, QFont.Bold)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top section with logo and title
        top_layout = QHBoxLayout()
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        else:
            logo_label.setText("Logo")
        top_layout.addWidget(logo_label)

        # Title and subtitle
        title_layout = QVBoxLayout()
        title_label = QLabel("Spotify to Tidal Transfer")
        title_label.setFont(header_font)
        subtitle_label = QLabel("Transfer your playlists, albums, and tracks from Spotify to Tidal")
        subtitle_label.setFont(modern_font)
        subtitle_label.setStyleSheet("color: #666666;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        top_layout.addLayout(title_layout)
        top_layout.addStretch()

        # MP3 Conversion Toggle as Icon Button
        self.convert_mp3_toggle = QPushButton()
        self.convert_mp3_toggle.setCheckable(True)
        self.convert_mp3_toggle.setChecked(_app_settings.get("convert_to_mp3_only", False))
        self.convert_mp3_toggle.setFixedSize(48, 48)
        self.convert_mp3_toggle.setIconSize(QSize(40, 40))
        self.convert_mp3_toggle.setStyleSheet("""
            QPushButton {
                border: 2px solid #d0d0d0;
                border-radius: 12px;
                background: #f8f8f8;
            }
            QPushButton:checked {
                border: 2px solid #4a90e2;
                background: #eaf4ff;
            }
        """)
        self.convert_mp3_toggle.clicked.connect(self.toggle_mp3_conversion)
        self.set_mp3_icon(self.convert_mp3_toggle.isChecked())
        top_layout.addWidget(self.convert_mp3_toggle)

        main_layout.addLayout(top_layout)

        # Input card
        self.input_card = QFrame()
        self.input_card.setObjectName("inputCard")
        input_layout = QVBoxLayout(self.input_card)
        input_layout.setSpacing(15)

        # URL input
        self.url_input = self.create_input_field("Spotify URL", "Enter Spotify playlist, album, or track URL", input_layout, bold_font, modern_font)[0]
        self.url_input.textChanged.connect(self.handle_url_input_change)

        # Tidal Playlist Name input (initially hidden)
        self.tidal_name_input, self.tidal_name_label = self.create_input_field("Tidal Playlist Name", "Enter a name for the new Tidal playlist", input_layout, bold_font, modern_font)
        self.tidal_name_input.setVisible(False)
        self.tidal_name_label.setVisible(False)
        
        # Output folder input
        folder_layout = QHBoxLayout()
        self.download_folder_input, self.download_folder_label = self.create_input_field("Output Folder", "Select download location", folder_layout, bold_font, modern_font)
        self.download_folder_input.setText(_app_settings.get("download_folder", ""))
        browse_button = QPushButton("Browse")
        browse_button.setFont(modern_font)
        browse_button.clicked.connect(self.browse_and_set_output_folder)
        folder_layout.addWidget(browse_button)
        input_layout.addLayout(folder_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.transfer_button = self.create_button("Transfer to Tidal", self.run_transfer, modern_font)
        self.download_button = self.create_button("Download from Tidal", self.start_download, modern_font)
        self.download_button.setEnabled(False)
        
        # Dark mode toggle
        self.dark_mode_toggle = QCheckBox("")
        self.dark_mode_toggle.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 32px;
                height: 32px;
            }}
            QCheckBox::indicator:unchecked {{
                image: url({_app_settings["ui"]["toggle_unchecked_icon"]});
            }}
            QCheckBox::indicator:checked {{
                image: url({_app_settings["ui"]["toggle_checked_icon"]});
            }}
        """)
        self.dark_mode_toggle.setChecked(_app_settings.get("dark_mode", False))
        self.dark_mode_toggle.toggled.connect(self.toggle_dark_mode)
        
        button_layout.addWidget(self.transfer_button)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.dark_mode_toggle)
        input_layout.addLayout(button_layout)
        main_layout.addWidget(self.input_card)

        # Progress card
        self.progress_card = QFrame()
        self.progress_card.setObjectName("progressCard")
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setSpacing(15)

        # Progress bars
        self.progress_label = QLabel("Transfer Progress")
        self.progress_label.setFont(bold_font)
        progress_layout.addWidget(self.progress_label)
        self.download_progress_bar = self.create_progress_bar("", progress_layout, bold_font)
        
        # Conversion progress section
        conversion_section = QVBoxLayout()
        self.conversion_label = QLabel("Converting to MP3...")
        self.conversion_label.setFont(bold_font)
        self.conversion_label.setVisible(self.convert_mp3_toggle.isChecked())
        self.conversion_progress_bar = QProgressBar()
        self.conversion_progress_bar.setVisible(self.convert_mp3_toggle.isChecked())
        self.conversion_progress_bar.setFormat("%p% (%v/%m)")
        self.conversion_progress_bar.setMinimum(0)
        self.conversion_progress_bar.setMaximum(100)
        self.conversion_progress_bar.setValue(0)
        self.conversion_progress_bar.setFont(bold_font)
        # No per-widget stylesheet here; rely on global stylesheet
        conversion_section.addWidget(self.conversion_label)
        conversion_section.addWidget(self.conversion_progress_bar)
        progress_layout.addLayout(conversion_section)

        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(200)
        self.output_area.setFont(modern_font)
        # No per-widget stylesheet here; rely on global stylesheet
        progress_layout.addWidget(self.output_area)
        main_layout.addWidget(self.progress_card)

        # Apply initial theme
        self.apply_theme()

    def set_mp3_icon(self, checked: bool):
        if checked:
            self.convert_mp3_toggle.setIcon(QIcon("mp3icon.png"))
        else:
            self.convert_mp3_toggle.setIcon(QIcon())

    def toggle_mp3_conversion(self, checked: bool) -> None:
        _app_settings["convert_to_mp3_only"] = checked
        config_manager.set("convert_to_mp3_only", checked)
        self.set_mp3_icon(checked)
        if hasattr(self, 'conversion_label'):
            self.conversion_label.setVisible(checked)
        if hasattr(self, 'conversion_progress_bar'):
            self.conversion_progress_bar.setVisible(checked)
            if not checked:
                self.conversion_progress_bar.setValue(0)

    def create_button(self, text: str, handler: Callable, font: QFont, enabled: bool = True) -> QPushButton:
        button = QPushButton(text)
        button.setFont(font)
        button.clicked.connect(handler)
        button.setEnabled(enabled)
        button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        return button

    def create_input_field(self, label_text: str, placeholder: str, parent_layout: QVBoxLayout, label_font: QFont, input_font: QFont) -> QLineEdit:
        layout = QVBoxLayout()
        label = QLabel(label_text)
        label.setFont(label_font)
        layout.addWidget(label)
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setFont(input_font)
        # No per-widget stylesheet here; rely on global stylesheet
        layout.addWidget(input_field)
        parent_layout.addLayout(layout)
        return input_field, label

    def create_progress_bar(self, label_text: str, parent_layout: QVBoxLayout, label_font: QFont) -> QProgressBar:
        layout = QVBoxLayout()
        label = QLabel(label_text)
        label.setFont(label_font)
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%p% (%v/%m)")
        progress_bar.setFont(label_font)
        # No per-widget stylesheet here; rely on global stylesheet
        layout.addWidget(label)
        layout.addWidget(progress_bar)
        parent_layout.addLayout(layout)
        return progress_bar

    def browse_and_set_output_folder(self) -> None:
        """Open folder dialog and set output path."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.download_folder_input.setText(folder)
            _app_settings["tidal_dl_ng_config"]["download_base_path"] = folder
            config_manager.set("tidal_dl_ng_config", _app_settings["tidal_dl_ng_config"])
            self.log(f"✅ Output folder set and saved: {folder}")

    def log(self, message: str) -> None:
        """Add message to log output with visual improvements."""
        # Skip character-by-character output
        if len(message.strip()) <= 1:
            return
            
        # Skip progress bar updates
        if message.startswith("\r") or message.startswith("\b"):
            return
            
        # Skip empty or whitespace-only messages
        if not message.strip():
            return
            
        # Filter out technical details for GUI
        if any(tech_term in message.lower() for tech_term in [
            "wsl", "bash", "command:", "subprocess", "traceback", "debug", "error code",
            "return code", "process", "thread", "socket", "connection", "api", "http",
            "request", "response", "config", "settings", "path", "directory", "file",
            "permission", "access", "token", "auth", "login", "session", "cache"
        ]):
            # Log technical details only to debug logger
            log_message(message, "DEBUG", gui_only=False)
            return
            
        # Add emojis for different types of messages
        if message.startswith("✅"):
            message = f"✅ {message[1:].strip()}"
        elif message.startswith("❌"):
            message = f"❌ {message[1:].strip()}"
        elif message.startswith("⚠️"):
            message = f"⚠️ {message[1:].strip()}"
        elif "error" in message.lower():
            message = f"❌ {message}"
        elif "warning" in message.lower():
            message = f"⚠️ {message}"
        elif "success" in message.lower():
            message = f"✅ {message}"
            
        # Add the message to the output area
        self.output_area.append(message)
        
        # Log the message using our custom logging function
        log_message(message, "INFO", gui_only=True)
        
        # Ensure the UI updates
        QApplication.processEvents()
        
        # Auto-scroll to the bottom
        self.output_area.verticalScrollBar().setValue(
            self.output_area.verticalScrollBar().maximum()
        )

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self.download_progress_bar.setMaximum(total)
        self.download_progress_bar.setValue(current)
        QApplication.processEvents()

    def handle_url_input_change(self, text):
        is_spotify = ("spotify.com" in text or "spotify:" in text)
        needs_name = is_spotify and ("playlist" in text or "album" in text or "track" in text)
        self.tidal_name_input.setVisible(needs_name)
        self.tidal_name_label.setVisible(needs_name)

    def run_transfer(self) -> None:
        self.set_progress_label("Transfer Progress")
        url = self.url_input.text().strip()
        tidal_playlist_name = self.tidal_name_input.text().strip() if self.tidal_name_input.isVisible() else ""
        download_folder = self.download_folder_input.text().strip()
        
        if not url:
            QMessageBox.critical(self, "Error", "Please enter a source URL.")
            return
            
        if not download_folder:
            QMessageBox.critical(self, "Error", "Please select an output folder.")
            return
            
        if self.tidal_name_input.isVisible() and not tidal_playlist_name:
            QMessageBox.critical(self, "Error", "Please enter a name for the Tidal playlist.")
            return
            
        # Create the folder if it doesn't exist
        if not os.path.exists(download_folder):
            try:
                os.makedirs(download_folder, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to create output folder: {str(e)}"
                )
                return
                
        self.update_tidal_config_output()
        self.output_area.clear()
        
        if "spotify.com" in url or "spotify:" in url:
            if "playlist" in url:
                tracks = self.manager.get_spotify_tracks(url)
            elif "album" in url:
                tracks = self.manager.get_spotify_album_tracks(url)
            elif "track" in url:
                tracks = self.manager.get_spotify_track(url)
            else:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    "Unsupported Spotify URL format."
                )
                return
                
            self.log(f"Transferring from Spotify to Tidal:\nSource URL: {url}\nTidal Playlist: {tidal_playlist_name}")
            self.transfer_button.setEnabled(False)
            self.download_button.setEnabled(False)
            self.download_progress_bar.setValue(0)
            
            try:
                playlist, unmatched, playlist_url = self.manager.create_tidal_playlist(
                    tidal_playlist_name,
                    tracks,
                    output_callback=self.log,
                    progress_callback=self.update_transfer_progress
                )
                
                self.log("\nSuccess: Tidal playlist created!")
                self.log(f"Playlist URL: {playlist_url}")
                self.log(f"Transferred: {len(tracks) - len(unmatched)}/{len(tracks)} tracks")
                
                if unmatched:
                    self.log("\nUnmatched Tracks:")
                    for track in unmatched:
                        self.log(f"- {track['name']} by {track['artist']} (Album: {track['album']})")
                        
                self.playlist_url = playlist_url
                self.total_tracks = len(tracks) - len(unmatched)
                self.download_button.setEnabled(True)
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Transfer failed: {str(e)}"
                )
            finally:
                self.transfer_button.setEnabled(True)
                
        elif "tidal.com" in url:
            self.log("Tidal URL detected. No conversion needed.")
            self.playlist_url = url
            self.download_button.setEnabled(True)
        else:
            QMessageBox.critical(
                self, 
                "Error", 
                "URL is neither a valid Spotify nor Tidal link."
            )

    def start_download(self) -> None:
        self.set_progress_label("Download Progress")
        self.download_button.setEnabled(False)
        self.log("\nStarting download process...")
        self.download_progress_bar.setMaximum(self.total_tracks)
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFormat("Downloading: %p% (%v/%m)")
        self.conversion_progress_bar.setMaximum(100)  # Set to 100 for percentage-based updates
        self.conversion_progress_bar.setValue(0)
        self.conversion_progress_bar.setFormat("Converting: %p% (%v/%m)")
        self.conversion_label.setText("")

        # --- FAKE PROGRESS BAR ---
        import threading
        import random
        self._fake_progress_running = True
        def fake_progress():
            value = 0
            while self._fake_progress_running and value < self.total_tracks:
                value += 1
                self.download_progress_bar.setValue(value)
                QApplication.processEvents()
                # Simulate variable download speed
                threading.Event().wait(random.uniform(0.1, 0.3))
            # Ensure bar is full at the end
            self.download_progress_bar.setValue(self.total_tracks)
            QApplication.processEvents()
        self._fake_progress_thread = threading.Thread(target=fake_progress, daemon=True)
        self._fake_progress_thread.start()
        # --- END FAKE PROGRESS BAR ---

        sudo_token = _app_settings.get("sudo_password_encrypted")
        sudo_pass = decrypt_password(sudo_token) if sudo_token else None
        if not sudo_pass:
            sudo_pass = get_or_prompt_sudo_password(self)
            if not sudo_pass:
                self.log("❌ Sudo password is required for download and conversion.")
                self.download_button.setEnabled(True)
                return
            _app_settings["sudo_password_encrypted"] = encrypt_password(sudo_pass)
            config_manager.set("sudo_password_encrypted", encrypt_password(sudo_pass))

        self.download_thread = DownloadThread(
            self.playlist_url, 
            self.total_tracks,
            self.download_folder_input.text()
        )
        self.download_thread.sudo_password = sudo_pass
        self.download_thread.convert_to_mp3 = _app_settings.get("convert_to_mp3_only", False)
        self.download_thread.update_log.connect(self.log)
        self.download_thread.update_progress.connect(self.update_download_progress)
        self.download_thread.update_conversion_progress.connect(self.update_conversion_progress)
        self.download_thread.finished.connect(self._fake_progress_finished)
        self.download_thread.password_required.connect(self.handle_password_request)
        self.download_thread.start()

    def _fake_progress_finished(self, success: bool):
        self._fake_progress_running = False
        if hasattr(self, '_fake_progress_thread') and self._fake_progress_thread.is_alive():
            self._fake_progress_thread.join(timeout=0.5)
        self.download_finished(success)

    def update_tidal_config_output(self) -> None:
        """Update Tidal config with output path."""
        wsl_home = get_wsl_home()
        tidal_tmp = f"{wsl_home}/tidal_tmp"
        config_dir = f"{wsl_home}/.config/tidal_dl_ng"
        config_path = f"{config_dir}/settings.json"
        
        # Create directories if they don't exist
        subprocess.run(
            ['wsl', 'bash', '-c', f"mkdir -p {config_dir} && mkdir -p {tidal_tmp}"],
            check=True
        )
        
        # Get FFmpeg path in WSL
        ffmpeg_path = _app_settings["tidal_dl_ng_config"].get("path_binary_ffmpeg", "")
        if not ffmpeg_path:
            # Try to find FFmpeg
            result = subprocess.run(
                ['wsl', 'bash', '-c', 'which ffmpeg'],
                capture_output=True,
                text=True
            )
            ffmpeg_path = result.stdout.strip() if result.stdout.strip() else "/usr/bin/ffmpeg"
        
        # Verify FFmpeg is working
        verify_cmd = f'wsl bash -c "{ffmpeg_path} -version"'
        verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
        if verify_result.returncode != 0:
            self.log("⚠️ Warning: FFmpeg verification failed. Attempting to reinstall...")
            if ensure_ffmpeg_installed(None):
                result = subprocess.run(
                    ['wsl', 'bash', '-c', 'which ffmpeg'],
                    capture_output=True,
                    text=True
                )
                ffmpeg_path = result.stdout.strip()
            else:
                self.log("⚠️ Warning: Could not verify FFmpeg installation. Some features may be limited.")
        
        # Update app settings
        _app_settings["tidal_dl_ng_config"]["download_base_path"] = tidal_tmp
        _app_settings["tidal_dl_ng_config"]["path_binary_ffmpeg"] = ffmpeg_path
        config_manager.save_settings()
        
        # Create Tidal config file with all necessary settings
        tidal_config = {
            "download_base_path": tidal_tmp,
            "path_binary_ffmpeg": ffmpeg_path,
            "skip_existing": True,
            "lyrics_embed": False,
            "lyrics_file": False,
            "video_download": True,
            "download_delay": True,
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
        }
        
        json_str = json.dumps(tidal_config, indent=4).replace('"', '\\"')
        bash_cmd = f'echo "{json_str}" > {config_path}'
        subprocess.run(
            ['wsl', 'bash', '-c', bash_cmd], 
            check=True
        )
        
        self.log(f"Tidal downloads will go to temp WSL path: {tidal_tmp}")
        self.log(f"FFmpeg path set to: {ffmpeg_path}")
        if verify_result.returncode == 0:
            self.log("FFmpeg verification successful!")

    def apply_theme(self) -> None:
        """Apply light or dark theme based on settings."""
        if _app_settings.get("dark_mode", False):
            self.apply_dark_mode()
        else:
            self.apply_light_mode()

    def apply_light_mode(self) -> None:
        """Apply light mode theme."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f9fafb;
                color: #222831;
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #f7f8fa;
                color: #222831;
                border: 1.5px solid #b0b8c1;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: 600;
            }
            QLineEdit:disabled {
                background-color: #eceef1;
                color: #a0a4aa;
            }
            QLineEdit::placeholder {
                color: #8a99b3;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 28px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QProgressBar {
                border: 2px solid #b0b8c1;
                border-radius: 10px;
                background: #f7f8fa;
                height: 32px;
                font-weight: bold;
                font-size: 16px;
                text-align: center;
                color: #222831;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 8px;
            }
            QTextEdit {
                background-color: #f7f8fa;
                border: 1.5px solid #b0b8c1;
                border-radius: 8px;
                padding: 10px;
                color: #222831;
                font-size: 16px;
                font-weight: 600;
            }
            QCheckBox {
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: 600;
                spacing: 5px;
                padding: 7px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
        """)

    def apply_dark_mode(self) -> None:
        """Apply dark mode theme."""
        self.setStyleSheet("""
            QWidget {
                background-color: #16181c;
                color: #e0e6ed;
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #18191d;
                color: #e0e6ed;
                border: 1.5px solid #444a54;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: 600;
            }
            QLineEdit:disabled {
                background-color: #18191d;
                color: #6c7380;
            }
            QLineEdit::placeholder {
                color: #7a869a;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 28px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
            QPushButton:disabled {
                background-color: #444a54;
            }
            QProgressBar {
                border: 2px solid #444a54;
                border-radius: 10px;
                background: #18191d;
                height: 32px;
                font-weight: bold;
                font-size: 16px;
                text-align: center;
                color: #e0e6ed;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 8px;
            }
            QTextEdit {
                background-color: #18191d;
                border: 1.5px solid #444a54;
                border-radius: 8px;
                padding: 10px;
                color: #e0e6ed;
                font-size: 16px;
                font-weight: 600;
            }
            QCheckBox {
                font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: 600;
                spacing: 5px;
                padding: 7px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
        """)

    def toggle_dark_mode(self, checked: bool) -> None:
        """Toggle between light and dark mode."""
        _app_settings["dark_mode"] = checked
        config_manager.set("dark_mode", checked)
        
        if checked:
            self.apply_dark_mode()
        else:
            self.apply_light_mode()
            
        # Add fade animation
        effect = QGraphicsOpacityEffect(self.input_card)
        self.input_card.setGraphicsEffect(effect)
        
        self.anim = QPropertyAnimation(effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.finished.connect(
            lambda: self.input_card.setGraphicsEffect(None)
        )
        self.anim.start()
    
    def download_finished(self, success: bool) -> None:
        """Handle download completion."""
        try:
            if success:
                self.log("\n✅ Download completed successfully!")
                self.download_progress_bar.setValue(self.download_progress_bar.maximum())
                
                # Get the WSL temp folder and Windows output folder
                wsl_home = get_wsl_home()
                wsl_folder = f"{wsl_home}/tidal_tmp"
                windows_folder = self.download_folder_input.text().strip()
                
                if not windows_folder:
                    self.log("Error: No output folder specified")
                    return
                
                # Verify WSL folder exists
                verify_cmd = f'wsl bash -c "if [ -d \\"{wsl_folder}\\" ]; then echo exists; else echo not_found; fi"'
                result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
                
                if "not_found" in result.stdout:
                    self.log(f"Error: WSL folder not found: {wsl_folder}")
                    return
                
                # Sync files from WSL to Windows
                self.log("\nSyncing files from WSL to Windows...")
                if self.download_thread:
                    try:
                        self.download_thread.copy_from_wsl_to_windows(wsl_folder, windows_folder)
                    except Exception as e:
                        self.log(f"Error during file transfer: {str(e)}")
                        import traceback
                        self.log(f"Traceback: {traceback.format_exc()}")
                        return
                
                # Convert to MP3 if needed
                if _app_settings.get("convert_to_mp3_only", False):
                    self.log("\nConverting files to MP3...")
                    try:
                        self.download_thread.convert_all_to_mp3(windows_folder)
                    except Exception as e:
                        self.log(f"Error during MP3 conversion: {str(e)}")
                        import traceback
                        self.log(f"Traceback: {traceback.format_exc()}")
            else:
                self.log("\n❌ Download failed!")
                
        except Exception as e:
            self.log(f"\n⚠️ Error in download_finished: {str(e)}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
        finally:
            try:
                self.download_button.setEnabled(True)
                self.log("\nProcess completed.")
            except Exception as e:
                self.log(f"Error re-enabling download button: {str(e)}")

    def closeEvent(self, event) -> None:
        """Handle application close event."""
        try:
            # Clean up any running threads
            if hasattr(self, 'download_thread') and self.download_thread and self.download_thread.isRunning():
                self.download_thread.terminate()
                self.download_thread.wait()
                
            # Clean up WSL temp directory
            if platform.system() == "Windows":
                wsl_home = get_wsl_home()
                wsl_temp_path = f"{wsl_home}/tidal_tmp"
                subprocess.run(
                    ['wsl', 'bash', '-c', f'rm -rf "{wsl_temp_path}"'],
                    capture_output=True
                )
        except Exception as e:
            log_message("Error during cleanup: %s", e)
            
        event.accept()

    def handle_password_request(self) -> None:
        """Handle password request from download thread."""
        stored_token = _app_settings.get("sudo_password_encrypted")
        sudo_pass = decrypt_password(stored_token) if stored_token else None
        if not sudo_pass:
            self.log("Error: No stored sudo password found. Please run the application again.")
            self.download_thread.set_password_verified(False)
            return

        sudo_pass = get_or_prompt_sudo_password(self)
        if not sudo_pass:
            self.log("Error: Sudo password is required for file operations.")
            self.download_thread.set_password_verified(False)
            return

        self.download_thread.sudo_password = sudo_pass
        self.download_thread.set_password_verified(True)

    def set_progress_label(self, text: str):
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(text)

    # --- Conversion Progress Bar Realism ---
    def update_conversion_progress(self, current: int, total: int) -> None:
        if not hasattr(self, 'conversion_progress_bar'):
            return
        self.conversion_progress_bar.setMaximum(total)
        self.conversion_progress_bar.setValue(current)
        if hasattr(self, 'conversion_label'):
            if current < total:
                self.conversion_label.setText(f"Converting file {current} of {total}...")
            else:
                self.conversion_label.setText("Conversion complete!")
        QApplication.processEvents()

    def update_transfer_progress(self, current: int, total: int) -> None:
        """Update progress bar for transfer progress."""
        self.download_progress_bar.setMaximum(total)
        self.download_progress_bar.setValue(current)
        QApplication.processEvents()

    def update_download_progress(self, current: int) -> None:
        """Update progress bar for download progress."""
        if not hasattr(self, 'total_tracks') or self.total_tracks <= 0:
            return
        self.download_progress_bar.setMaximum(self.total_tracks)
        self.download_progress_bar.setValue(current)
        QApplication.processEvents()

# --- Encryption helpers ---
ENCRYPTION_KEY_FILE = os.path.join(os.path.expanduser("~"), ".spotifytotidal_key")

def get_encryption_key() -> Optional[bytes]:
    if not os.path.exists(ENCRYPTION_KEY_FILE):
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, "wb") as f:
            f.write(key)
        return key
    with open(ENCRYPTION_KEY_FILE, "rb") as f:
        return f.read()

def encrypt_password(password: str) -> str:
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(token: str) -> Optional[str]:
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(token.encode()).decode()
    except Exception:
        return None

# ------------------- Config Management -------------------
# Always use AppData for config
home_dir = os.path.expanduser('~')
app_data_dir = os.path.join(home_dir, 'AppData', 'Local', 'SpotifyToTidal')
os.makedirs(app_data_dir, exist_ok=True)

SPOTIFY_TOKEN_CACHE = os.path.join(app_data_dir, '.spotify_token_cache')
TIDAL_SESSION_FILE = os.path.join(app_data_dir, 'tidal_session.pkl')
SETTINGS_FILE = os.path.join(app_data_dir, 'app_settings.json')

class ConfigManager:
    """Handles configuration loading, merging with defaults, and saving."""
    def __init__(self, filename: str = SETTINGS_FILE, defaults: Optional[Dict[str, Any]] = None) -> None:
        self.filename = filename
        self.defaults = defaults or {}
        self.settings: Dict[str, Any] = self.load_settings()
        self.merge_defaults()

    def load_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as f:
                    return json.load(f)
            except Exception as e:
                log_message(f"Error loading settings: {e}", "ERROR")
                return {}
        return {}

    def merge_defaults(self) -> None:
        updated = False
        for key, default_value in self.defaults.items():
            if key not in self.settings:
                self.settings[key] = default_value
                updated = True
            elif isinstance(default_value, dict):
                self.settings[key] = self._merge_dicts(default_value, self.settings.get(key, {}))
        if updated:
            self.save_settings()

    def _merge_dicts(self, defaults: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        merged = current.copy()
        for key, default_value in defaults.items():
            if key not in merged:
                merged[key] = default_value
            elif isinstance(default_value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dicts(default_value, merged.get(key, {}))
        return merged

    def save_settings(self) -> None:
        try:
            with open(self.filename, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            log_message(f"Error saving settings: {e}", "ERROR")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save_settings()

# ------------------- Spotify API Initialization -------------------
scope = "playlist-read-private"

class SpotifyAuthDialog(QDialog):
    """Dialog for Spotify OAuth login."""
    def __init__(self, auth_url: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spotify Login")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        # Add a label with instructions
        label = QLabel("Please follow these steps to log in to Spotify:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        # Add numbered steps
        steps = [
            "1. Click the link below to open Spotify in your browser",
            "2. Log in to your Spotify account",
            "3. After logging in, return to this window and click 'I Have Logged In'"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("font-size: 12px; margin: 5px 0;")
            layout.addWidget(step_label)
        
        # Add the login URL as a clickable link
        link_label = QLabel(f"<a href='{auth_url}' style='color: #4a90e2; text-decoration: none;'>{auth_url}</a>")
        link_label.setTextFormat(Qt.RichText)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("font-size: 12px; margin: 10px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(link_label)
        
        # Add a note about expiration
        expire_label = QLabel("Note: This link will expire in 5 minutes")
        expire_label.setStyleSheet("font-size: 12px; color: #666; margin: 5px 0;")
        layout.addWidget(expire_label)
        
        # Add the continue button
        self.continue_button = QPushButton("I Have Logged In")
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
        """)
        self.continue_button.clicked.connect(self.accept)
        layout.addWidget(self.continue_button)
        
        self.setLayout(layout)

class SpotifyAuthManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.auth_manager = SpotifyOAuth(
            client_id=_app_settings["spotify_config"]["client_id"],
            client_secret=_app_settings["spotify_config"]["client_secret"],
            redirect_uri=_app_settings["spotify_config"]["redirect_uri"],
            scope=scope,
            cache_path=SPOTIFY_TOKEN_CACHE
        )
        
    def get_spotify_client(self):
        try:
            # Try to get cached token
            token_info = self.auth_manager.get_cached_token()
            if token_info and not self.auth_manager.is_token_expired(token_info):
                return spotipy.Spotify(auth_manager=self.auth_manager)
                
            # If no valid token, start auth flow
            auth_url = self.auth_manager.get_authorize_url()
            dlg = SpotifyAuthDialog(auth_url, self.parent)
            if dlg.exec_() == QDialog.Accepted:
                # Get the token
                token_info = self.auth_manager.get_access_token()
                if token_info:
                    return spotipy.Spotify(auth_manager=self.auth_manager)
                else:
                    raise Exception("Failed to get Spotify access token")
            else:
                raise Exception("Spotify login cancelled by user")
                
        except Exception as e:
            if self.parent and hasattr(self.parent, 'log'):
                self.parent.log(f"❌ Spotify authentication error: {str(e)}")
            raise

# Initialize Spotify client with auth manager
sp = None  # Will be initialized when needed

# ------------------- Utility Functions -------------------
def extract_playlist_id(url: str) -> str:
    """Extract playlist ID from Spotify URL."""
    pattern = r"(?:https?:\/\/open\.spotify\.com\/playlist\/|spotify:playlist:)([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Spotify playlist URL")

def extract_album_id(url: str) -> str:
    """Extract album ID from Spotify URL."""
    pattern = r"(?:https?:\/\/open\.spotify\.com\/album\/|spotify:album:)([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Spotify album URL")

def extract_track_id(url: str) -> str:
    """Extract track ID from Spotify URL."""
    pattern = r"(?:https?:\/\/open\.spotify\.com\/track\/|spotify:track:)([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Spotify track URL")

def clean_track_name(track_name: str) -> str:
    """Clean track name by removing extra information."""
    return re.sub(r"\s-\s.*|\s\([^)]*\)|\s\[.*?\]", "", track_name).strip()

def get_wsl_home() -> str:
    """Get WSL home directory path."""
    try:
        home = subprocess.check_output(
            ["wsl", "bash", "-c", "echo $HOME"], 
            encoding="utf-8"
        ).strip()
        return home if home else "/home/unknown"
    except Exception as e:
        log_message("Error getting WSL home: %s", e)
        return "/home/unknown"

def convert_wsl_to_windows_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path."""
    m = re.match(r"^/mnt/([a-z])/(.*)", wsl_path)
    if m:
        drive = m.group(1).upper()
        path_part = m.group(2).replace("/", "\\")
        return f"{drive}:\\{path_part}"
    return wsl_path

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 and return as base64 string."""
    salt = os.urandom(32)  # Generate a random salt
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # Number of iterations
    )
    # Store salt and key together
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(stored_hash: str, password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # Decode the stored hash
        stored = base64.b64decode(stored_hash.encode('utf-8'))
        # Extract salt and key
        salt = stored[:32]
        key = stored[32:]
        # Hash the provided password with the same salt
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return key == new_key
    except Exception:
        return False

def get_or_prompt_sudo_password(parent=None) -> str:
    """Get the sudo password, prompting and encrypting if needed."""
    encrypted = config_manager.get("sudo_password_encrypted")
    password = decrypt_password(encrypted) if encrypted else None
    while not password:
        password, ok = QInputDialog.getText(
            parent,
            "Sudo Password",
            "Enter your WSL sudo password (for installing prerequisites):",
            QLineEdit.Password
        )
        if not ok or not password:
            return ""
        # Verify password
        verify_cmd = f'wsl bash -c "echo {password} | sudo -S true 2>/dev/null"'
        result = subprocess.run(verify_cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            encrypted = encrypt_password(password)
            config_manager.set("sudo_password_encrypted", encrypted)
            return password
        else:
            QMessageBox.critical(
                parent,
                "Invalid Password",
                "The provided sudo password is incorrect. Please try again."
            )
            password = None
    return password or ""

def verify_sudo_password(password: str) -> bool:
    """Verify if the sudo password is correct."""
    try:
        # Create a temporary file to store the command output
        temp_file = os.path.join(os.path.expanduser('~'), 'sudo_test.txt')
        
        # Run sudo command with password in WSL using full path
        cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "echo \'{password}\' | sudo -S whoami > {temp_file} 2>&1"'
        log_message(f"Executing sudo command: {cmd}", level="DEBUG")
        
        # Execute the command
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        log_message(f"Sudo command result: {result.returncode}", level="DEBUG")
        log_message(f"Sudo command output: {result.stdout}", level="DEBUG")
        log_message(f"Sudo command error: {result.stderr}", level="DEBUG")
        
        # Check if the command was successful
        if result.returncode == 0:
            log_message("Sudo password verified successfully", level="INFO")
            return True
        else:
            log_message(f"Sudo password verification failed: {result.stderr}", level="ERROR")
            return False
            
    except Exception as e:
        log_message(f"Error verifying sudo password: {str(e)}", level="ERROR")
        return False
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            log_message(f"Error cleaning up temp file: {str(e)}", level="ERROR")

def ensure_tidal_dl_ng_installed(parent: Optional[QWidget] = None) -> bool:
    """Ensure tidal-dl-ng is installed in WSL."""
    try:
        log_message("Checking if tidal-dl-ng is installed...", level="INFO")
        
        # Check both system path and virtual environment
        check_commands = [
            'which tidal-dl-ng',  # Check system path
            'source $HOME/tidal-env/bin/activate && which tidal-dl-ng'  # Check virtual environment
        ]
        
        for check_cmd in check_commands:
            cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "{check_cmd}"'
            log_message(f"Checking with command: {check_cmd}", level="DEBUG")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                log_message(f"tidal-dl-ng found at: {result.stdout.strip()}", level="INFO")
                return True
            
        log_message("tidal-dl-ng not found, installing...", level="INFO")
        
        # Get sudo password
        sudo_pass = get_or_prompt_sudo_password(parent)
        if not sudo_pass:
            log_message("No sudo password provided, installation cancelled", level="ERROR")
            return False
            
        # Verify sudo password
        if not verify_sudo_password(sudo_pass):
            log_message("Invalid sudo password, installation cancelled", level="ERROR")
            return False
            
        # Install tidal-dl-ng with detailed logging
        install_steps = [
            f'echo \'{sudo_pass}\' | sudo -S apt-get update',
            f'echo \'{sudo_pass}\' | sudo -S apt-get install -y python3 python3-pip python3-venv',
            'python3 -m venv $HOME/tidal-env',
            'source $HOME/tidal-env/bin/activate && pip install --upgrade pip',
            'source $HOME/tidal-env/bin/activate && pip install --upgrade tidal-dl-ng'
        ]
        
        for step in install_steps:
            cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "{step}"'
            log_message(f"Executing: {step}", level="DEBUG")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                log_message(f"Step failed: {step}", level="ERROR")
                log_message(f"Error output: {result.stderr}", level="ERROR")
                return False
                
            log_message(f"Step completed: {step}", level="DEBUG")
            
        # Verify installation in both locations
        verify_commands = [
            'which tidal-dl-ng',  # Check system path
            'source $HOME/tidal-env/bin/activate && which tidal-dl-ng'  # Check virtual environment
        ]
        
        for verify_cmd in verify_commands:
            cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "{verify_cmd}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                log_message(f"tidal-dl-ng verified at: {result.stdout.strip()}", level="INFO")
                return True
                
        log_message("tidal-dl-ng installation verification failed", level="ERROR")
        return False
            
    except Exception as e:
        log_message(f"Error ensuring tidal-dl-ng installation: {str(e)}", level="ERROR")
        return False

def locate_tidal_dl_ng() -> str:
    """Locate the tidal-dl-ng executable in WSL."""
    try:
        # Check both system path and virtual environment
        check_commands = [
            'which tidal-dl-ng',  # Check system path
            'source $HOME/tidal-env/bin/activate && which tidal-dl-ng'  # Check virtual environment
        ]
        
        for check_cmd in check_commands:
            cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "{check_cmd}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        # If not found in PATH, try the virtual environment path
        cmd = 'C:\\Windows\\System32\\wsl.exe bash -c "echo $HOME/tidal-env/bin/tidal-dl-ng"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip()
            
        raise Exception("tidal-dl-ng not found")
        
    except Exception as e:
        log_message(f"Error locating tidal-dl-ng: {str(e)}", level="ERROR")
        raise

def ensure_ffmpeg_installed(parent: Optional[QWidget] = None) -> bool:
    """Ensure ffmpeg is installed in WSL."""
    try:
        log_message("Checking if ffmpeg is installed...", level="INFO")
        
        # First check if it's already installed
        check_cmd = 'C:\\Windows\\System32\\wsl.exe bash -c "which ffmpeg"'
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_message("ffmpeg is already installed", level="INFO")
            return True
            
        log_message("ffmpeg not found, installing...", level="INFO")
        
        # Get sudo password
        sudo_pass = get_or_prompt_sudo_password(parent)
        if not sudo_pass:
            log_message("No sudo password provided, installation cancelled", level="ERROR")
            return False
            
        # Verify sudo password
        if not verify_sudo_password(sudo_pass):
            log_message("Invalid sudo password, installation cancelled", level="ERROR")
            return False
            
        # Install ffmpeg
        install_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "echo \'{sudo_pass}\' | sudo -S apt-get update && echo \'{sudo_pass}\' | sudo -S apt-get install -y ffmpeg"'
        log_message(f"Executing ffmpeg installation command: {install_cmd}", level="DEBUG")
        
        result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
        log_message(f"FFmpeg installation result: {result.returncode}", level="DEBUG")
        log_message(f"FFmpeg installation output: {result.stdout}", level="DEBUG")
        log_message(f"FFmpeg installation error: {result.stderr}", level="DEBUG")
        
        if result.returncode == 0:
            log_message("FFmpeg installed successfully", level="INFO")
            return True
        else:
            log_message(f"FFmpeg installation failed: {result.stderr}", level="ERROR")
            return False
            
    except Exception as e:
        log_message(f"Error ensuring ffmpeg installation: {str(e)}", level="ERROR")
        return False

def ensure_ffmpeg_path_set(parent: Optional[QWidget] = None) -> None:
    """Ensure FFmpeg path is set in config."""
    if _app_settings["tidal_dl_ng_config"].get("path_binary_ffmpeg"):
        # Verify the path is still valid
        if platform.system() == "Windows":
            verify_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "if [ -f {_app_settings["tidal_dl_ng_config"]["path_binary_ffmpeg"]} ]; then echo valid; else echo invalid; fi"'
            result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if "valid" in result.stdout:
                log_message("FFmpeg path is valid.", level="INFO")
                return
        else:
            if os.path.exists(_app_settings["tidal_dl_ng_config"]["path_binary_ffmpeg"]):
                log_message("FFmpeg path is valid.", level="INFO")
                return
        
    # If we get here, we need to find FFmpeg
    ffmpeg_path = None
    if platform.system() == "Windows":
        # Try to find FFmpeg in WSL
        result = subprocess.run(
            ['C:\\Windows\\System32\\wsl.exe', 'bash', '-c', 'which ffmpeg'],
            capture_output=True, 
            text=True, 
            encoding="utf-8"
        )
        ffmpeg_path = result.stdout.strip() if result.stdout.strip() else None
        
        if not ffmpeg_path:
            # Try to install FFmpeg
            if ensure_ffmpeg_installed(parent):
                result = subprocess.run(
                    ['C:\\Windows\\System32\\wsl.exe', 'bash', '-c', 'which ffmpeg'],
                    capture_output=True,
                    text=True,
                    encoding="utf-8"
                )
                ffmpeg_path = result.stdout.strip()
    else:
        ffmpeg_path = shutil.which("ffmpeg")
        
    if ffmpeg_path:
        _app_settings["tidal_dl_ng_config"]["path_binary_ffmpeg"] = ffmpeg_path
        config_manager.save_settings()
        log_message(f"FFmpeg path set to: {ffmpeg_path}", level="INFO")
        if parent and hasattr(parent, 'log'):
            parent.log(f"FFmpeg path set to: {ffmpeg_path}")
    else:
        log_message("FFmpeg not found. Videos can be downloaded but not processed.", level="WARNING")
        if parent and hasattr(parent, 'log'):
            parent.log("⚠️ FFmpeg not found. Videos can be downloaded but not processed.")
        # Set a default path that will be used in WSL
        _app_settings["tidal_dl_ng_config"]["path_binary_ffmpeg"] = "/usr/bin/ffmpeg"
        config_manager.save_settings()


# ------------------- Tidal Login Dialog -------------------
class TidalLoginDialog(QDialog):
    """Dialog for Tidal OAuth login."""
    def __init__(self, login_url: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tidal Login")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        # Add a label with instructions
        label = QLabel("Please follow these steps to log in to Tidal:")
        label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        # Add numbered steps
        steps = [
            "1. Click the link below to open Tidal in your browser",
            "2. Log in to your Tidal account",
            "3. After logging in, return to this window and click 'I Have Logged In'"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("font-size: 12px; margin: 5px 0;")
            layout.addWidget(step_label)
        
        # Add the login URL as a clickable link
        link_label = QLabel(f"<a href='{login_url}' style='color: #4a90e2; text-decoration: none;'>{login_url}</a>")
        link_label.setTextFormat(Qt.RichText)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("font-size: 12px; margin: 10px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(link_label)
        
        # Add a note about expiration
        expire_label = QLabel("Note: This link will expire in 5 minutes")
        expire_label.setStyleSheet("font-size: 12px; color: #666; margin: 5px 0;")
        layout.addWidget(expire_label)
        
        # Add the continue button
        self.continue_button = QPushButton("I Have Logged In")
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ab8;
            }
        """)
        self.continue_button.clicked.connect(self.accept)
        layout.addWidget(self.continue_button)
        
        self.setLayout(layout)

# ------------------- Transfer Manager -------------------
class TransferManager:
    """Handles transfer between Spotify and Tidal."""
    def __init__(self, logger: logging.Logger, sp_client, parent=None) -> None:
        self.logger = logger
        self.session: Optional[tidalapi.Session] = None
        self.sp = sp_client
        self.parent = parent

    def login_tidal(self) -> tidalapi.Session:
        """Login to Tidal with OAuth."""
        if os.path.exists(TIDAL_SESSION_FILE):
            try:
                with open(TIDAL_SESSION_FILE, "rb") as f:
                    session = pickle.load(f)
                    try:
                        if session.check_login():
                            self.logger.info("Using cached Tidal session.")
                            self.session = session
                            return session
                        else:
                            self.logger.info("Cached session expired, refreshing...")
                            session.refresh_token()
                            if session.check_login():
                                with open(TIDAL_SESSION_FILE, "wb") as f:
                                    pickle.dump(session, f)
                                self.logger.info("Session refreshed successfully.")
                                self.session = session
                                return session
                    except Exception as e:
                        self.logger.error("Error refreshing session: %s", e)
            except Exception as e:
                self.logger.error("Error loading Tidal session: %s", e)
                
        session = tidalapi.Session()
        login, future = session.login_oauth()
        login_url = login.verification_uri_complete
        
        # Create and show the login dialog
        dlg = TidalLoginDialog(login_url, self.parent)
        if dlg.exec_() == QDialog.Accepted:
            try:
                # Wait for the login to complete
                future.result()
                if session.check_login():
                    with open(TIDAL_SESSION_FILE, "wb") as f:
                        pickle.dump(session, f)
                    self.logger.info("Tidal login successful.")
                    self.session = session
                    return session
                else:
                    raise Exception("Tidal login failed - session not valid after login")
            except Exception as e:
                self.logger.error("Tidal login error: %s", e)
                raise Exception(f"Tidal login failed: {str(e)}")
        else:
            raise Exception("Tidal login cancelled by user")

    def get_spotify_tracks(self, playlist_url: str) -> List[Dict[str, str]]:
        """Get tracks from Spotify playlist."""
        playlist_id = extract_playlist_id(playlist_url)
        tracks: List[Dict[str, str]] = []
        offset = 0
        limit = 100
        
        while True:
            results = self.sp.playlist_tracks(
                playlist_id, 
                offset=offset, 
                limit=limit,
                fields='items(track(name,artists(name),album(name))),next,total'
            )
            
            for item in results.get('items', []):
                track = item.get('track')
                if track:
                    tracks.append({
                        'name': track.get('name', ''),
                        'artist': track['artists'][0].get('name', ''),
                        'album': track['album'].get('name', '')
                    })
                    
            if results.get('next') is None:
                break
                
            offset += limit
            
        self.logger.info("Fetched %d tracks from Spotify playlist", len(tracks))
        return tracks

    def get_spotify_album_tracks(self, album_url: str) -> List[Dict[str, str]]:
        """Get tracks from Spotify album."""
        album_id = extract_album_id(album_url)
        album = self.sp.album(album_id)
        results = self.sp.album_tracks(album_id)
        
        tracks: List[Dict[str, str]] = []
        for item in results.get('items', []):
            tracks.append({
                'name': item.get('name', ''),
                'artist': album['artists'][0].get('name', ''),
                'album': album.get('name', '')
            })
            
        self.logger.info("Fetched %d tracks from Spotify album", len(tracks))
        return tracks

    def get_spotify_track(self, track_url: str) -> List[Dict[str, str]]:
        """Get single track from Spotify."""
        track_id = extract_track_id(track_url)
        track = self.sp.track(track_id)
        return [{
            'name': track.get('name', ''),
            'artist': track['artists'][0].get('name', ''),
            'album': track['album'].get('name', '')
        }]

    def find_tidal_track(self, track_name: str, artist_name: str, album_name: str) -> Optional[tidalapi.media.Track]:
        """Find matching track on Tidal."""
        clean_name = clean_track_name(track_name)
        search_query = f"{clean_name} {artist_name}"
        search_results = self.session.search(search_query, models=[tidalapi.media.Track])
        
        best_match: Optional[tidalapi.media.Track] = None
        best_score = 0
        threshold = SIMILARITY_THRESHOLD
        
        for track in search_results.get('tracks', []):
            track_score = fuzz.ratio(clean_name.lower(), track.name.lower())
            artist_score = fuzz.ratio(artist_name.lower(), track.artist.name.lower())
            total_score = track_score + artist_score
            
            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = track
                
        return best_match

    def create_tidal_playlist(
        self, 
        playlist_name: str, 
        tracks: List[Dict[str, str]],
        output_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[Any, List[Dict[str, str]], str]:
        """Create Tidal playlist from Spotify tracks."""
        if self.session is None:
            raise Exception("Tidal session not initialized")
            
        playlist = self.session.user.create_playlist(
            title=playlist_name, 
            description="Transferred from Spotify"
        )
        
        tidal_base_url = "https://tidal.com/playlist"
        playlist_url = f"{tidal_base_url}/{playlist.id}"
        unmatched_tracks: List[Dict[str, str]] = []
        tidal_track_ids: List[int] = []
        batch_size = 50
        total_tracks = len(tracks)
        
        if output_callback:
            output_callback(f"Processing {total_tracks} tracks...")
            
        if progress_callback:
            progress_callback(0, total_tracks)
            
        for i, track in enumerate(tracks):
            tidal_track = self.find_tidal_track(
                track['name'], 
                track['artist'], 
                track['album']
            )
            
            if tidal_track:
                tidal_track_ids.append(tidal_track.id)
                if output_callback:
                    output_callback(
                        f"[{i + 1}/{total_tracks}] Matched: {track['name']} by {track['artist']}"
                    )
            else:
                unmatched_tracks.append(track)
                if output_callback:
                    output_callback(
                        f"[{i + 1}/{total_tracks}] Unmatched: {track['name']} by {track['artist']}"
                    )
                    
            if progress_callback:
                progress_callback(i + 1, total_tracks)
                
            if len(tidal_track_ids) >= batch_size or i == total_tracks - 1:
                if tidal_track_ids:
                    try:
                        playlist.add(tidal_track_ids)
                        if output_callback:
                            output_callback(f"Added {len(tidal_track_ids)} tracks to Tidal")
                        tidal_track_ids = []
                        time.sleep(2)  # Rate limiting
                    except Exception as e:
                        if output_callback:
                            output_callback(f"Error adding tracks: {str(e)}")
                        raise
                        
        return playlist, unmatched_tracks, playlist_url

# ------------------- Download Thread -------------------
class DownloadThread(QThread):
    """Thread for handling downloads."""
    update_log = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    password_required = pyqtSignal()
    password_verified = pyqtSignal(bool)
    update_conversion_progress = pyqtSignal(int, int)

    def __init__(self, playlist_url: str, total_tracks: int, output_folder: str, parent=None) -> None:
        super().__init__(parent)
        self.playlist_url = playlist_url
        self.total_tracks = total_tracks
        self.output_folder = output_folder
        self.downloaded = 0
        self.convert_to_mp3 = _app_settings.get("convert_to_mp3_only", False)
        self.sudo_password = None
        self._password_verified = False
        self._stop_requested = False

    def run(self) -> None:
        """Execute the download process."""
        try:
            # First ensure tidal-dl-ng is installed
            if not ensure_tidal_dl_ng_installed(self.parent()):
                self.update_log.emit("❌ Failed to install tidal-dl-ng. Please check the logs for details.")
                self.finished.emit(False)
                return

            # Get the path to tidal-dl-ng
            try:
                tidal_dl_path = locate_tidal_dl_ng()
                self.update_log.emit(f"Found tidal-dl-ng at: {tidal_dl_path}")
            except Exception as e:
                self.update_log.emit(f"❌ Error locating tidal-dl-ng: {str(e)}")
                self.finished.emit(False)
                return

            # Get WSL home directory and create temp directory
            wsl_home = get_wsl_home()
            wsl_temp_dir = f"{wsl_home}/tidal_tmp"
            
            # Create temp directory if it doesn't exist
            create_dir_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "mkdir -p {wsl_temp_dir}"'
            subprocess.run(create_dir_cmd, shell=True, check=True)

            # Construct the command with full path and proper environment setup
            cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "cd {wsl_temp_dir} && export PYTHONUNBUFFERED=1 && source $HOME/tidal-env/bin/activate && {tidal_dl_path} dl \'{self.playlist_url}\' 2>&1"'

            self.update_log.emit("\nStarting download process...")
            log_message(f"Command: {cmd}", level="DEBUG")

            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            current_track = 0
            buffer = ""
            for char in iter(lambda: process.stdout.read(1), ''):
                if self._stop_requested:
                    process.terminate()
                    self.finished.emit(False)
                    return
                if char:
                    buffer += char
                    if char in ['\n', '\r']:
                        line = buffer.strip()
                        buffer = ""
                        if line:
                            # Check for sudo password failure
                            if '[sudo] password for' in line and 'incorrect password attempt' in line:
                                config_manager.set("sudo_password_encrypted", None)
                                self.update_log.emit("❌ Incorrect sudo password. Please restart the app and enter the correct password.")
                                process.terminate()
                                self.finished.emit(False)
                                return

                            # Log all output for debugging
                            log_message(line, level="DEBUG")
                            
                            # Track download progress
                            line_lower = line.lower()
                            if "downloaded item" in line_lower:
                                current_track += 1
                                self.update_progress.emit(current_track)
                                self.update_log.emit(f"✅ Downloaded track {current_track}/{self.total_tracks}")
                            elif "error" in line_lower:
                                self.update_log.emit(f"⚠️ {line}")
                            elif "warning" in line_lower:
                                self.update_log.emit(f"⚠️ {line}")

            process.wait()

            if process.returncode == 0:
                self.update_log.emit("\n✅ Download completed successfully!")
                self.update_progress.emit(self.total_tracks)
                
                # Copy files from WSL to Windows
                self.copy_from_wsl_to_windows(wsl_temp_dir, self.output_folder)
                
                # Convert to MP3 if enabled
                if self.convert_to_mp3:
                    self.update_log.emit("\nConverting files to MP3...")
                    self.convert_all_to_mp3(self.output_folder)
                
                # Final cleanup of WSL temp directory
                cleanup_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "rm -rf {wsl_temp_dir}/*"'
                result = subprocess.run(cleanup_cmd, shell=True, capture_output=True)
                if result.returncode != 0:
                    log_message(f"Warning: Failed to clean temp directory: {result.stderr}", level="DEBUG")
                
                self.finished.emit(True)
            else:
                self.update_log.emit(f"\n❌ Download failed with return code {process.returncode}")
                self.finished.emit(False)

        except Exception as e:
            self.update_log.emit(f"\n❌ Error during download: {str(e)}")
            log_message(f"Traceback: {traceback.format_exc()}", level="DEBUG")
            self.finished.emit(False)

    def copy_from_wsl_to_windows(self, wsl_folder: str, windows_folder: str) -> None:
        """Copy files from WSL to Windows."""
        try:
            # Verify WSL folder exists
            self.update_log.emit(f"\nVerifying WSL folder: {wsl_folder}")
            check_folder = subprocess.run(
                f'C:\\Windows\\System32\\wsl.exe bash -c "ls -la \'{wsl_folder}\'"',
                shell=True,
                capture_output=True,
                text=True
            )
            self.update_log.emit("WSL folder contents:")
            self.update_log.emit(check_folder.stdout)

            # Create Windows folder if it doesn't exist
            os.makedirs(windows_folder, exist_ok=True)

            # Convert Windows path to WSL path and escape single quotes
            wsl_path = self.convert_windows_to_wsl_path(windows_folder)
            wsl_path_escaped = self.escape_single_quotes(wsl_path)
            self.update_log.emit(f"[DEBUG] Using WSL path: {wsl_path_escaped}")
            
            # Use wsl.exe to copy files directly, wrap in single quotes
            copy_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "cp -r \'{wsl_folder}/*\' \'{wsl_path_escaped}/\'"'
            result = subprocess.run(
                copy_cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.update_log.emit(f"Error copying files: {result.stderr}")
                # Try alternative method using sudo
                if self.sudo_password:
                    copy_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "echo \'{self.sudo_password}\' | sudo -S cp -r \'{wsl_folder}/*\' \'{wsl_path_escaped}/\'"'
                    result = subprocess.run(
                        copy_cmd,
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        self.update_log.emit(f"Error copying files (second attempt): {result.stderr}")
                        return

            # Verify files were copied
            verify_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "ls -la \'{wsl_path_escaped}\'"'
            verify_result = subprocess.run(
                verify_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            self.update_log.emit("\nVerifying copied files:")
            self.update_log.emit(verify_result.stdout)

            # Clean up WSL folder
            cleanup_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "rm -rf \'{wsl_folder}/*\'"'
            subprocess.run(
                cleanup_cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            self.update_log.emit("\n✅ Files copied successfully!")

        except Exception as e:
            self.update_log.emit(f"\n❌ Error during file copy: {str(e)}")
            import traceback
            self.update_log.emit(f"Traceback: {traceback.format_exc()}")

    def convert_all_to_mp3(self, folder_path: str) -> None:
        """Convert all audio files in the folder to MP3 format."""
        try:
            self.update_log.emit(f"[DEBUG] Entered convert_all_to_mp3 with folder_path: {folder_path}")
            
            # Get list of files to convert
            files = []
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if filename.endswith((".flac", ".m4a", ".wav")):
                        files.append(os.path.join(root, filename))
            self.update_log.emit(f"[DEBUG] Files found for conversion: {files}")

            total_files = len(files)
            if total_files == 0:
                self.update_log.emit("No files to convert.")
                return

            self.update_log.emit(f"Found {total_files} files to convert.")
            converted = 0

            # Update conversion progress bar maximum
            self.update_conversion_progress.emit(0, total_files)

            for idx, file in enumerate(files):
                if not file:
                    continue
                    
                output_file = file.rsplit('.', 1)[0] + '.mp3'
                self.update_log.emit(f"[DEBUG] Converting file: {file} to {output_file}")

                # Convert Windows path to WSL path
                wsl_input = self.convert_windows_to_wsl_path(file)
                wsl_output = self.convert_windows_to_wsl_path(output_file)

                # Build ffmpeg command
                ffmpeg_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "ffmpeg -y -i \'{wsl_input}\' -codec:a libmp3lame -qscale:a 2 \'{wsl_output}\'"'
                
                self.update_log.emit(f"[DEBUG] Running conversion command: {ffmpeg_cmd}")
                result = subprocess.run(
                    ffmpeg_cmd,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Remove original file after conversion
                    try:
                        if re.match(r"^[a-zA-Z]:", file):
                            os.remove(file)
                        else:
                            rm_cmd = f'C:\\Windows\\System32\\wsl.exe bash -c "rm \'{wsl_input}\'"'
                            subprocess.run(rm_cmd, shell=True, check=True)
                        self.update_log.emit(f"[DEBUG] Removed original file: {file}")
                    except Exception as e:
                        self.update_log.emit(f"Warning: Could not remove original file {file}: {e}")
                    converted += 1
                    self.update_log.emit(f"Converted {converted}/{total_files}: {os.path.basename(file)}")
                    self.update_conversion_progress.emit(converted, total_files)
                else:
                    self.update_log.emit(f"Error converting {file}: {result.stderr}")
                    
            self.update_log.emit(f"\n✅ Converted {converted} files to MP3 format!")
            
        except Exception as e:
            self.update_log.emit(f"\n❌ Error during MP3 conversion: {str(e)}")
            import traceback
            self.update_log.emit(f"Traceback: {traceback.format_exc()}")

    def convert_windows_to_wsl_path(self, win_path: str) -> str:
        """Convert Windows path to WSL path (robust, no escaping, just quoting in bash)."""
        win_path = win_path.replace("\\", "/")
        if win_path.startswith("\\\\"):
            return win_path  # UNC path, leave as-is
        if re.match(r"^[a-zA-Z]:", win_path):
            drive, path = win_path[0], win_path[2:]
            wsl_path = f"/mnt/{drive.lower()}{path}"
            return wsl_path
        return win_path

    def escape_single_quotes(self, path: str) -> str:
        """Escape single quotes for safe use in bash single-quoted strings."""
        return path.replace("'", "'\"'\"'")

    def set_password_verified(self, verified: bool) -> None:
        """Set password verification status."""
        self._password_verified = verified

    def stop(self):
        self._stop_requested = True

def main():
    print('DEBUG: Entered main()')
    app = QApplication(sys.argv)

    while True:
        print('DEBUG: Top of auth loop')
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        spotify_config = settings.get("spotify_config", {})
        client_id = spotify_config.get("client_id")
        client_secret = spotify_config.get("client_secret")
        redirect_uri = spotify_config.get("redirect_uri")
        spotify_valid = bool(client_id and client_secret and redirect_uri and client_id != "YOUR_SPOTIFY_CLIENT_ID" and client_secret != "YOUR_SPOTIFY_CLIENT_SECRET")
        tidal_valid = check_authentication()
        print(f'DEBUG: spotify_valid={spotify_valid}, tidal_valid={tidal_valid}')
        if not (spotify_valid and tidal_valid):
            print('DEBUG: Launching AuthSetupWindow')
            auth_window = AuthSetupWindow()
            auth_window.exec_()
        else:
            print('DEBUG: Auth complete, breaking loop')
            break

    # RELOAD settings for the main window using ConfigManager to merge defaults
    global _app_settings, config_manager
    print('DEBUG: Initializing ConfigManager')
    config_manager = ConfigManager(defaults=default_settings)
    _app_settings = config_manager.settings

    print('DEBUG: Creating main window')
    window = SpotifyToTidalApp()
    window.show()
    print('DEBUG: Entering app.exec_()')
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_message(f"Application error: {str(e)}", "ERROR")
        import traceback
        log_message(f"Traceback: {traceback.format_exc()}", "ERROR")
        sys.exit(1)

SIMILARITY_THRESHOLD = 80  # Fuzzy match threshold for track matchings
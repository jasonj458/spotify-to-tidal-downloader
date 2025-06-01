#!/usr/bin/env python3

import os
import sys
import json
import pickle
import logging
from typing import Optional, Dict, Any, Tuple

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox,
                            QTabWidget, QFrame, QCheckBox, QDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import tidalapi
from tidal_login_dialog import TidalLoginDialog

# ------------------- Logging Setup -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- Constants -------------------
# Get the path to the user's home directory
home_dir = os.path.expanduser('~')
app_data_dir = os.path.join(home_dir, 'AppData', 'Local', 'SpotifyToTidal')
os.makedirs(app_data_dir, exist_ok=True)

# Update file paths
SETTINGS_FILE = os.path.join(app_data_dir, 'app_settings.json')
TIDAL_SESSION_FILE = os.path.join(app_data_dir, 'tidal_session.pkl')
SPOTIFY_TOKEN_CACHE = os.path.join(app_data_dir, '.spotify_token_cache')

class AuthSetupWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Authentication Setup")
        self.setMinimumSize(600, 400)
        self.spotify_authenticated = False
        self.tidal_authenticated = False
        
        # Ensure AppData directory exists
        home_dir = os.path.expanduser('~')
        self.app_data_dir = os.path.join(home_dir, 'AppData', 'Local', 'SpotifyToTidal')
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        # Update file paths
        self.settings_file = os.path.join(self.app_data_dir, 'app_settings.json')
        self.tidal_session_file = os.path.join(self.app_data_dir, 'tidal_session.pkl')
        self.spotify_token_cache = os.path.join(self.app_data_dir, '.spotify_token_cache')
        
        self.setup_ui()
        self.load_settings()
        self.check_auth_status()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        tabs.setFont(QFont("Segoe UI", 10))
        
        # Spotify Tab
        spotify_tab = QWidget()
        spotify_layout = QVBoxLayout(spotify_tab)
        
        # Spotify Client ID
        spotify_layout.addWidget(QLabel("Spotify Client ID:"))
        self.spotify_client_id = QLineEdit()
        self.spotify_client_id.setPlaceholderText("Enter your Spotify Client ID")
        spotify_layout.addWidget(self.spotify_client_id)
        
        # Spotify Client Secret
        spotify_layout.addWidget(QLabel("Spotify Client Secret:"))
        self.spotify_client_secret = QLineEdit()
        self.spotify_client_secret.setPlaceholderText("Enter your Spotify Client Secret")
        self.spotify_client_secret.setEchoMode(QLineEdit.Password)
        spotify_layout.addWidget(self.spotify_client_secret)
        
        # Spotify Status
        self.spotify_status = QLabel("Status: Not authenticated")
        spotify_layout.addWidget(self.spotify_status)
        
        # Spotify Test Button
        spotify_test_btn = QPushButton("Test Spotify Connection")
        spotify_test_btn.clicked.connect(self.test_spotify_connection)
        spotify_layout.addWidget(spotify_test_btn)
        
        spotify_layout.addStretch()
        tabs.addTab(spotify_tab, "Spotify")
        
        # Tidal Tab
        tidal_tab = QWidget()
        tidal_layout = QVBoxLayout(tidal_tab)
        
        # Tidal Status
        self.tidal_status = QLabel("Status: Not authenticated")
        tidal_layout.addWidget(self.tidal_status)
        
        # Tidal Login Button
        tidal_login_btn = QPushButton("Login to Tidal")
        tidal_login_btn.clicked.connect(self.login_tidal)
        tidal_layout.addWidget(tidal_login_btn)
        
        tidal_layout.addStretch()
        tabs.addTab(tidal_tab, "Tidal")
        
        layout.addWidget(tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save & Continue")
        self.save_btn.clicked.connect(self.save_and_continue)
        self.save_btn.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.save_btn)
        
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self.close)
        button_layout.addWidget(exit_btn)
        
        layout.addLayout(button_layout)

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'spotify_config' in settings:
                        self.spotify_client_id.setText(settings['spotify_config'].get('client_id', ''))
                        self.spotify_client_secret.setText(settings['spotify_config'].get('client_secret', ''))
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            # Log the path and values
            with open("auth_debug.log", "a") as logf:
                logf.write(f"Saving to: {self.settings_file}\n")
                logf.write(f"Client ID: {self.spotify_client_id.text()}\n")
                logf.write(f"Client Secret: {self.spotify_client_secret.text()}\n")

            # Load the full settings file
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}

            # Update only the spotify_config section
            if 'spotify_config' not in settings:
                settings['spotify_config'] = {}

            settings['spotify_config']['client_id'] = self.spotify_client_id.text()
            settings['spotify_config']['client_secret'] = self.spotify_client_secret.text()
            settings['spotify_config']['redirect_uri'] = "http://localhost:8888/callback"

            # Write the full settings back
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)

            with open("auth_debug.log", "a") as logf:
                logf.write("Save successful!\n")

            msg = f"Settings saved to: {self.settings_file}\n\nClient ID: {self.spotify_client_id.text()}\nClient Secret: {self.spotify_client_secret.text()}"
            print("[DEBUG] " + msg.replace("\n", " "))
            QMessageBox.information(self, "Settings Saved", msg)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            with open("auth_debug.log", "a") as logf:
                logf.write(f"Save failed: {e}\n")
            print(f"[ERROR] Failed to save Spotify credentials: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save Spotify credentials: {e}")
            return False

    def check_auth_status(self):
        # Check Spotify
        try:
            if os.path.exists(self.spotify_token_cache):
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=self.spotify_client_id.text(),
                    client_secret=self.spotify_client_secret.text(),
                    redirect_uri="http://localhost:8888/callback",
                    cache_path=self.spotify_token_cache
                ))
                sp.current_user()
                self.spotify_status.setText("Status: Authenticated")
                self.spotify_status.setStyleSheet("color: green;")
                self.spotify_authenticated = True
            else:
                self.spotify_status.setText("Status: Not authenticated")
                self.spotify_status.setStyleSheet("color: red;")
                self.spotify_authenticated = False
        except Exception:
            self.spotify_status.setText("Status: Not authenticated")
            self.spotify_status.setStyleSheet("color: red;")
            self.spotify_authenticated = False
        
        # Check Tidal
        try:
            if os.path.exists(self.tidal_session_file):
                with open(self.tidal_session_file, 'rb') as f:
                    session = pickle.load(f)
                if session.check_login():
                    self.tidal_status.setText("Status: Authenticated")
                    self.tidal_status.setStyleSheet("color: green;")
                    self.tidal_authenticated = True
                    return
        except Exception:
            pass
        
        self.tidal_status.setText("Status: Not authenticated")
        self.tidal_status.setStyleSheet("color: red;")
        self.tidal_authenticated = False
        
        # Update save button state
        self.update_save_button()

    def update_save_button(self):
        """Update save button state based on authentication status."""
        self.save_btn.setEnabled(self.spotify_authenticated and self.tidal_authenticated)
        if self.spotify_authenticated and self.tidal_authenticated:
            self.save_and_continue()

    def test_spotify_connection(self):
        try:
            if not self.spotify_client_id.text() or not self.spotify_client_secret.text():
                QMessageBox.warning(self, "Error", "Please enter both Client ID and Client Secret")
                return
            
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.spotify_client_id.text(),
                client_secret=self.spotify_client_secret.text(),
                redirect_uri="http://localhost:8888/callback",
                cache_path=self.spotify_token_cache
            ))
            
            user = sp.current_user()
            QMessageBox.information(self, "Success", f"Successfully connected to Spotify as {user['display_name']}")
            self.spotify_status.setText("Status: Authenticated")
            self.spotify_status.setStyleSheet("color: green;")
            self.spotify_authenticated = True
            self.update_save_button()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to Spotify: {str(e)}")
            self.spotify_status.setText("Status: Authentication failed")
            self.spotify_status.setStyleSheet("color: red;")
            self.spotify_authenticated = False
            self.update_save_button()

    def login_tidal(self):
        try:
            session = tidalapi.Session()
            login, future = session.login_oauth()
            login_url = login.verification_uri_complete
            
            # Create and show the login dialog
            dlg = TidalLoginDialog(login_url, self)
            if dlg.exec_() == QDialog.Accepted:
                try:
                    future.result()
                    if session.check_login():
                        # Save session to AppData directory
                        with open(self.tidal_session_file, 'wb') as f:
                            pickle.dump(session, f)
                        
                        self.tidal_status.setText("Status: Authenticated")
                        self.tidal_status.setStyleSheet("color: green;")
                        self.tidal_authenticated = True
                        self.update_save_button()
                        QMessageBox.information(self, "Success", "Successfully logged in to Tidal")
                    else:
                        raise Exception("Login verification failed")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to complete Tidal login: {str(e)}")
                    self.tidal_status.setText("Status: Authentication failed")
                    self.tidal_status.setStyleSheet("color: red;")
                    self.tidal_authenticated = False
                    self.update_save_button()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start Tidal login: {str(e)}")
            self.tidal_status.setText("Status: Authentication failed")
            self.tidal_status.setStyleSheet("color: red;")
            self.tidal_authenticated = False
            self.update_save_button()

    def save_and_continue(self):
        if not self.spotify_authenticated or not self.tidal_authenticated:
            QMessageBox.warning(self, "Error", "Both Spotify and Tidal must be authenticated before continuing")
            return
            
        if self.save_settings():
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings")

def main():
    try:
        app = QApplication(sys.argv)
        window = AuthSetupWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Auth setup error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
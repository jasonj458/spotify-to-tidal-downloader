from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from typing import Optional

class TidalLoginDialog(QDialog):
    """Dialog for Tidal OAuth login."""
    def __init__(self, login_url: str, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tidal Login")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        # --- PATCH: Ensure protocol is present ---
        if not login_url.startswith("http"):
            login_url = "https://" + login_url
        
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
import os
import sys
import subprocess
import shutil

def check_requirements():
    """Check if all required files exist."""
    required_files = [
        'SpotifyToTidal.py',
        'requirements.txt',
        'SpotifyToTidal.spec',
        'logo.png',
        'mp3icon.png',
        'sun.png',
        'moon.png'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print("❌ Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        return False
    return True

def install_requirements():
    """Install required packages."""
    print("📦 Installing requirements...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def build_executable():
    """Build the executable using PyInstaller."""
    print("🔨 Building executable...")
    try:
        # Clean previous build
        if os.path.exists("build"):
            shutil.rmtree("build")
        if os.path.exists("dist"):
            shutil.rmtree("dist")
        if os.path.exists("runtime_hook.py"):
            os.remove("runtime_hook.py")
            
        # Run PyInstaller
        # Find the PyInstaller command and ensure it does NOT use --noconsole, and instead uses --console if present.
        # Example: pyinstaller --onefile --console SpotifyToTidal.py
        subprocess.run([sys.executable, "-m", "PyInstaller", "SpotifyToTidal.spec"], check=True)
        
        # Verify the executable was created
        exe_path = os.path.join("dist", "SpotifyToTidal.exe")
        if os.path.exists(exe_path):
            print(f"✅ Executable created successfully: {exe_path}")
            
            # Create a README file in the dist folder
            readme_path = os.path.join("dist", "README.txt")
            with open(readme_path, "w") as f:
                f.write("""Spotify to Tidal Transfer & Downloader

Requirements:
1. Windows 10 or later
2. WSL (Windows Subsystem for Linux) installed and configured
3. Internet connection for Spotify and Tidal authentication

First Run:
1. The application will create necessary directories in your AppData folder
2. You'll need to authenticate with both Spotify and Tidal
3. You'll need to provide your WSL sudo password for file operations

Note: The application uses WSL for file operations and requires proper WSL setup.
If you encounter any issues, please ensure WSL is properly installed and configured.

For support or issues, please contact the developer.
""")
            
            return True
        else:
            print("❌ Executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    finally:
        # Clean up runtime hook file
        if os.path.exists("runtime_hook.py"):
            os.remove("runtime_hook.py")

def main():
    print("🚀 Starting build process...")
    
    if not check_requirements():
        print("❌ Build aborted due to missing files")
        return
        
    if not install_requirements():
        print("❌ Build aborted due to failed requirements installation")
        return
        
    if not build_executable():
        print("❌ Build aborted due to failed executable creation")
        return
        
    print("✨ Build process completed successfully!")

if __name__ == "__main__":
    main() 
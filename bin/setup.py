import io
import os
import traceback
import urllib.request
import zipfile
import sys
import time
import ctypes

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

ZIP_FILE_NAME = "peerconnect.zip"
APP_NAME = os.environ.get("APP_NAME", "PeerConnect")


GITHUB_REPO_DOWNLOAD_URL = (
    f"https://github.com/ShaikAli65/{APP_NAME}/releases/latest/download/{ZIP_FILE_NAME}"
)


def format_size(size_bytes):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def download_zip(url):
    """Download ZIP file with progress display"""
    print(f"Downloading ZIP file from: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            start_time = time.time()
            chunk_size = 16 * 1024  # 16KB
            data = []

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data.append(chunk)
                downloaded += len(chunk)
                
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                percent = (downloaded / total_size) * 100 if total_size > 0 else 0

                # Progress bar
                if total_size > 0:
                    bar_length = 40
                    filled = int(bar_length * downloaded // total_size)
                    bar = '█' * filled + '-' * (bar_length - filled)
                    sys.stdout.write(
                        f"\r[{bar}] {percent:.1f}% "
                        f"{format_size(downloaded)}/{format_size(total_size)} "
                        f"({format_size(speed)}/s)"
                    )
                else:
                    sys.stdout.write(f"\rDownloaded {format_size(downloaded)}")

                sys.stdout.flush()

            print("\nDownload completed successfully.")
            return b''.join(data)

    except Exception as e:
        raise Exception(f"Error downloading ZIP file: {e}")


def extract_zip(zip_content, target_directory):
    """Extract ZIP file with progress display"""
    print(f"\nExtracting files to: {target_directory}")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
            members = zip_ref.namelist()
            total_files = len(members)
            max_name_length = max(len(name) for name in members) if members else 0
            
            for i, member in enumerate(members, 1):
                zip_ref.extract(member, target_directory)
                display_name = member if len(member) <= 30 else f"...{member[-27:]}"
                sys.stdout.write(
                    f"\rExtracting [{i}/{total_files}] "
                    f"{display_name.ljust(30)} "
                    f"({i/total_files*100:.1f}%)"
                )
                sys.stdout.flush()
            
            print("\nExtraction completed successfully.")

    except Exception as e:
        raise Exception(f"Error extracting ZIP file: {e}")


def create_data_folder():
    """Create a 'data' folder in the user's local AppData directory."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise Exception("LOCALAPPDATA environment variable not found.")

    data_folder = os.path.join(local_appdata, APP_NAME)
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        print(f"Created data folder: {data_folder}")
    else:
        print(f"Data folder already exists: {data_folder}")
    return data_folder


def main():
    if not is_admin():
        print("Requesting administrator privileges...")
        # Relaunch the script with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

    zip_content = download_zip(GITHUB_REPO_DOWNLOAD_URL)

    program_files = os.environ.get("ProgramFiles")
    if not program_files:
        raise Exception("ProgramFiles environment variable not found.")

    app_install_dir = os.path.join(program_files)
    if not os.path.exists(app_install_dir):
        os.makedirs(app_install_dir)
        print(f"Created installation directory: {app_install_dir}")
    else:
        print(f"Installation directory already exists: {app_install_dir}")

    extract_zip(zip_content, app_install_dir)

    create_data_folder()

    print("Setup completed successfully.")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
    input("press enter to exit")

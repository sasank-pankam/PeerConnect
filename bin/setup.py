import io
import os
import traceback
import urllib.request
import zipfile

ZIP_FILE_NAME = "peerconnect.zip"
GITHUB_REPO_DOWNLOAD_URL = (
    f"https://github.com/owner/repo/releases/latest/download/{ZIP_FILE_NAME}"
)


def download_zip(url):
    """Download ZIP file using the Python standard library."""
    print(f"Downloading ZIP file from: {url}")
    try:
        with urllib.request.urlopen(url) as response:
            if hasattr(response, "status") and response.status != 200:
                raise Exception(f"Failed to download file, status code: {response.status}")
            zip_data = response.read()
            print("Download successful.")
            return zip_data
    except Exception as e:
        raise Exception(f"Error downloading ZIP file: {e}")


def extract_zip(zip_content, target_directory):
    """Extract the ZIP file content into the target directory."""
    print(f"Extracting files to: {target_directory}")
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
        zip_ref.extractall(target_directory)
    print("Extraction completed.")


def create_data_folder():
    """Create a 'data' folder in the user's local AppData directory."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise Exception("LOCALAPPDATA environment variable not found.")

    data_folder = os.path.join(local_appdata, "PeerConnect")
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        print(f"Created data folder: {data_folder}")
    else:
        print(f"Data folder already exists: {data_folder}")
    return data_folder


def main():
    zip_content = download_zip(GITHUB_REPO_DOWNLOAD_URL)

    program_files = os.environ.get("ProgramFiles")
    if not program_files:
        raise Exception("ProgramFiles environment variable not found.")

    app_install_dir = os.path.join(program_files, "appname")
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

import os.path
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog

from src.core import *
from src.avails.remotepeer import RemotePeer
from src.avails import useables as use
from src.avails.fileobject import PeerFile
from src.avails.textobject import DataWeaver

every_file = {}


def __setFileId(file: PeerFile, receiver_obj: RemotePeer):
    global every_file
    receiver_obj.increment_file_count()
    every_file[f"{receiver_obj.id}(^){receiver_obj.get_file_count()}"] = file


def fileSender(_data: DataWeaver, receiver_sock: socket.socket, is_dir=False):
    receiver_obj, prompt_data = RemotePeer(), ''
    if _data.content == "":
        files_list = open_file_dialog_window()
        for file in files_list:
            _data.content = file
            fileSender(_data, receiver_sock, is_dir)
    try:
        receiver_obj: RemotePeer = use.get_peer_obj_from_id(_data.id)
        temp_port = use.get_free_port()

        file = PeerFile(uri=(const.THIS_IP, temp_port), path=_data.content)
        __setFileId(file, receiver_obj)

        _header = (const.CMD_RECV_DIR if is_dir else const.CMD_RECV_FILE)
        _id = json.dumps([const.THIS_IP, temp_port])

        try:
            DataWeaver(header=_header, content=file.get_meta_data(), _id=_id).send(receiver_sock)
        except socket.error:
            pass  # give feed back that can't send file, ask for feedback

        if file.verify_handshake():
            file.send_file()
            print("::file sent: ", file.filename, " to ", receiver_sock.getpeername())
            prompt_data = DataWeaver(header="this is a prompt", content=file.filename, _id=receiver_obj.id)
            return file.filename
        return False

    except NotADirectoryError as nde:
        prompt_data = DataWeaver(header="this is a prompt", content=nde.filename, _id=receiver_obj.id)
    except FileNotFoundError as fne:
        prompt_data = DataWeaver(header="this is a prompt", content=fne.filename, _id=receiver_obj.id)
    finally:
        # asyncio.run(handle_data_flow.feed_core_data_to_page(prompt_data))
        pass


def fileReceiver(refer: DataWeaver):
    recv_ip, recv_port = json.loads(refer.id)
    file = PeerFile(uri=(recv_ip, recv_port))
    metadata = refer.content
    file.set_meta_data(filename=metadata['name'], file_size=int(metadata['size']))

    if file.recv_handshake():
        file.recv_file()

    return file.filename


def endFileThreads():
    global every_file
    try:
        for file in every_file.values():
            file.hold()
    except AttributeError as e:
        error_log(f"::Error at endFileThreads() from  endFileThreads/filemanager at line 79: {e}")
    every_file.clear()
    return True


def open_file_dialog_window(prev_directory=[]) -> List[str]:
    """Opens the system-like file picker dialog."""
    prev_directory.append("")
    app = QApplication([])
    dialog = QFileDialog()
    dialog.setOption(QFileDialog.DontUseNativeDialog, True)
    dialog.setWindowFlags(Qt.WindowStaysOnTopHint | dialog.windowFlags())
    files = dialog.getOpenFileNames(directory=prev_directory[0],
                                    caption="Select files to send")[0]
    try:
        prev_directory[0] = os.path.dirname(files[0])
    except IndexError:
        pass
    return files

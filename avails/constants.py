import socket as soc
import threading


USERNAME = ''
THIS_PORT = 0
PAGE_PORT = 0
SERVER_PORT = 0
SERVER_IP = ''
FILE_PORT = 45210
REQ_PORT = 35896
PATH_CURRENT = ''
PATH_LOG = ''
PATH_CONFIG = ''
PATH_PAGE = ''
PATH_DOWNLOAD = ''
THIS_IP = ''

IP_VERSION = soc.AF_INET
PROTOCOL = soc.SOCK_STREAM
FORMAT = 'utf-8'
count_of_user_id = 0
user_id_lock = threading.Lock()
anim_delay = 0
MAX_CALL_BACKS = 6

OBJ = None
OBJ_THREAD = None
REQUESTS_THREAD = None
REMOTE_OBJECT = None
SERVER_THREAD = None
ACTIVE_PEERS = []
PAGE_HANDLE_CALL = threading.Event()
SAFE_LOCK_FOR_PAGE = False
PRINT_LOCK = threading.Lock()
WEB_SOCKET = None
LIST_OF_PEERS: dict = {}

CMD_RECV_FILE = b'thisisacommandtocore_/!_recvafile'
CMD_CLOSING_HEADER = b'thisisacommandtocore_/!_closeconnection'
TEXT_SUCCESS_HEADER = b'textstringrecvsuccess'
REQ_FOR_LIST = b'thisisarequestocore_/!_listofusers'
CMD_NOTIFY_USER = b'thisisacommandtocore_/!_notifyuser'
CMD_RECV_DIR = b'thisisacommandtocore_/!_recvdir'
CMD_RECV_DIR_LITE = b'thisisacommandtocore_/!_recvdir_lite'

CMD_FILESOCKET_HANDSHAKE = 'thisisacommandtocore_/!_filesocketopen'
CMD_FILESOCKET_CLOSE = 'thisisacommandtocore_/!_closefilesocket'
FILESEND_INTITATE_HEADER = 'inititatefilesequence'
SERVER_OK = 'connectionaccepted'
HANDLE_MESSAGE_HEADER = 'thisisamessage'
HANDLE_END = 'endprogram'
HANDLE_COMMAND = 'thisisacommand'
HANDLE_FILE_HEADER = 'thisisafile'
HANDLE_CONNECT_USER = 'connectuser'
HANDLE_RELOAD = 'thisiscommandtocore_/!_reload'
HANDLE_DIR_HEADER = 'thisisadir'
HANDLE_POP_DIR_SELECTOR = 'popdirselector'
HANDLE_PUSH_FILE_SELECTOR = 'pushfileselector'
HANDLE_OPEN_FILE = 'openfile'



import queue

import src.avails.useables as use

from src.core import *
from src.core import requests_handler
from src.avails.textobject import SimplePeerText
from src.avails.remotepeer import RemotePeer
from src.avails.constants import CONNECT_SERVER_FLAG


Error_Calls = 0
connection_status = False


def safe_stop():
    return CONNECT_SERVER_FLAG.is_set()


def get_initial_list(no_of_users, initiate_socket):
    global Error_Calls
    ping_queue = queue.Queue()
    for _ in range(no_of_users):
        try:
            _nomad = RemotePeer.deserialize(initiate_socket)
            ping_queue.put(_nomad)
            use.start_thread(_target=requests_handler.signal_status, _args=(ping_queue,))
            use.echo_print(f"::User received from server : {_nomad}")

        except socket.error as e:
            error_log('::Exception while receiving list of users at connect server.py/get_initial_list, exp:' + str(e))
            if not e.errno == 10054:
                continue

            end_connection_with_server()
            if not ping_queue.empty():
                server_log(f"::Server disconnected received some users retrying ...", 4)
                list_error_handler()
            return False
    return True


def list_error_handler():
    pass


def get_list_from(initiate_socket):
    const.PAGE_HANDLE_CALL.wait()
    global Error_Calls

    initiate_socket = until_sock_is_readable(initiate_socket, control_flag=CONNECT_SERVER_FLAG)
    if initiate_socket is None:
        return False
    raw_length = initiate_socket.recv(8)

    # initiate_socket.setblocking(False)
    # buffer = bytearray()
    # while proceed():
    #     data = initiate_socket.recv(8)
    #     buffer.extend(data)
    #     if len(buffer) == 8:
    #         break
    #
    # raw_length = bytes(buffer)

    length = struct.unpack('!Q', raw_length)[0]  # number of users
    with initiate_socket:
        return get_initial_list(length, initiate_socket)


def list_from_forward_control(list_owner: RemotePeer):
    # socket.create_connection()
    with connect.Socket(const.IP_VERSION, const.PROTOCOL) as list_connection_socket:
        list_connection_socket.connect(list_owner.req_uri)
        if SimplePeerText(list_connection_socket, const.REQ_FOR_LIST, byte_able=False).send():
            get_list_from(list_connection_socket)


def initiate_connection():
    global Error_Calls, connection_status

    use.echo_print("::Connecting to server")
    server_connection = setup_server_connection()
    if server_connection is None:
        return False if (const.END_OR_NOT is True) else None

    text = SimplePeerText(server_connection)
    if text.receive(cmp_string=const.SERVER_OK):
        use.echo_print('\n::Connection accepted by server')
        use.start_thread(_target=get_list_from, _args=(server_connection,))
    elif text.compare(const.REDIRECT):
        # server may send a peer's details to get list from
        recv_list_user = RemotePeer.deserialize(server_connection)
        use.echo_print('::Connection redirected by server to : ', recv_list_user.req_uri)
        use.start_thread(_target=list_from_forward_control, _args=(recv_list_user,))
    else:
        return None
    connection_status = True
    return True


def setup_server_connection():
    retry_count = 0
    while not safe_stop():
        try:
            server_add = (const.SERVER_IP, const.PORT_SERVER)
            server_connection = connect.create_connection(server_add, timeout=const.SERVER_TIMEOUT)
            break
        except (ConnectionRefusedError, TimeoutError, ConnectionError):
            if retry_count >= const.MAX_CALL_BACKS:
                use.echo_print("\n::Ending program server refused connection")
                return None
            try:
                retry_count += 1
                print(f"\r::Connection refused by server, {f'retrying... {retry_count}' if safe_stop() else 'returning'}", end='')
            except KeyboardInterrupt:
                return

    else:
        return None
    try:
        const.THIS_OBJECT.serialize(server_connection)
    except (socket.error,OSError):
        server_connection.close()
        return
    return server_connection


def end_connection_with_server():
    CONNECT_SERVER_FLAG.set()
    print("::Cleared server flag")
    try:
        const.THIS_OBJECT.status = 0
        if connection_status is False:
            return True
        with connect.create_connection((const.SERVER_IP, const.PORT_SERVER)) as end_socket:
            const.THIS_OBJECT.serialize(end_socket)
        print("::sent leaving status to server")
        return True
    except Exception as exp:
        server_log(f'::Failed disconnecting from server at {__name__}/{__file__}, exp : {exp}', 4)
        return False

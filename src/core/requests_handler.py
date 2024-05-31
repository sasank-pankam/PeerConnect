from queue import Queue
from collections import deque

from src.avails.remotepeer import RemotePeer
from src.core import *
from src.avails import useables as use
from src.webpage_handlers import handle_data
from src.avails.textobject import SimplePeerText
from src.core.senders import RecentConnections

from src.avails.constants import REQ_FLAG

_controller = ThreadController(None, control_flag=REQ_FLAG)


def send_list(_conn):

    no_of_peers = struct.pack('!Q', len(peer_list))
    _conn.sendall(no_of_peers)
    error_call = 0
    for _nomad in peer_list.peers():
        if _controller.to_stop:
            return
        if not _nomad.status == 1:
            continue
        try:
            _nomad.serialize(_conn)
        except socket.error as e:
            if error_call := adjust_list_error(error_call, _conn, e) > const.MAX_CALL_BACKS:
                return False
    return


def adjust_list_error(error_call, _conn, err):
    error_log(f"::Exception while giving list of users at {__name__}/{__file__}, exp : {err}")
    error_call += 1
    use.echo_print(
        f"::Exception while giving list of users to {_conn.getpeername()} at {func_str(adjust_list_error)} \n-exp : {err}")


def add_peer_accordingly(_peer: RemotePeer, *, include_ping=False):
    if _peer.status == 1:
        peer_list.add_peer(_peer.id, _peer)
        use.echo_print(f"::added {_peer.uri} {_peer.username} to list of peers")
    else:
        if include_ping:
            if ping_user(_peer):
                return False

        _peer.status = 0
        peer_list.remove_peer(_peer.id)
        RecentConnections.force_remove(_peer.id)
        use.echo_print(f"::removed {_peer.uri} {_peer.username} from list of peers")
    asyncio.run(handle_data.feed_user_status_to_page(_peer))
    return True


def initiate():
    _control_sock = connect.create_server(const.THIS_OBJECT.req_uri,family=const.IP_VERSION)

    use.echo_print("::Requests bind success full at ", const.THIS_OBJECT.req_uri)
    use.echo_print("::Listening for requests at ", _control_sock.getsockname())
    while True:
        readable, _, _ = select.select([_control_sock, _controller], [], [])
        if _controller.to_stop:
            return
        if _control_sock in readable:
            try:
                initiate_conn, _ = _control_sock.accept()
                use.start_thread(_target=control_connection, _args=(initiate_conn,))
            except (socket.error, OSError) as e:
                error_log(f"Error at manage {func_str(initiate)} exp: {e}")


def sync_users_with_server(_conn):
    with _conn:
        raw_data = _conn.recv(8)
        if not (diff_length := struct.unpack('!Q', raw_data)[0]):
            return
        for _ in range(diff_length):
            try:
                notify_user_connection(_conn, True)
            except Exception as e:
                error_log(
                    f"Error syncing list at {func_str(sync_users_with_server)} exp :  {e}")
    return


def notify_user_connection(_conn_socket, ping_again=False):
    try:
        new_peer_object = RemotePeer.deserialize(_conn_socket)
        if not new_peer_object:
            return False
    except Exception as e:
        error_log(f"Error at {func_str(notify_user_connection)} exp :  {e}")
        return None
    return add_peer_accordingly(new_peer_object, include_ping=ping_again)


function_map = {
    const.REQ_FOR_LIST: send_list,
    const.I_AM_ACTIVE: notify_user_connection,
    const.SERVER_PING: sync_users_with_server,
    const.ACTIVE_PING: lambda x: None,
    const.LIST_SYNC: lambda x: None,
}


def control_connection(_conn):
    readable, _, _ = select.select([_conn, _controller], [], [], 40)
    if _controller.to_stop or _conn not in readable:
        return
    # try:
    data = SimplePeerText(_conn, controller=_controller).receive()
    use.echo_print(f"::Received {data} from {_conn.getpeername()}")
    # except (socket.error, OSError) as e:
    #     error_log(f"Socket error at {func_str(control_connection)} exp:{e} peer:{_conn.getpeername()}")
    #     return
    function_map.get(data, lambda x: None)(_conn)


def ping_user(remote_peer: RemotePeer):
    try:
        with connect.Socket(const.IP_VERSION, const.PROTOCOL) as _conn:
            _conn.settimeout(5)
            _conn.connect(remote_peer.req_uri)
            return SimplePeerText(_conn, const.ACTIVE_PING).send()
    except socket.error as e:
        error_log(f"Error pinging user at {func_str(ping_user)} exp :  {e}")
        return False


def signal_status(queue_in: Queue[RemotePeer]):
    while not (_controller.to_stop or queue_in.empty()):
        peer_object = queue_in.get()
        try:
            with connect.create_connection(peer_object.req_uri,timeout=5) as _conn:
                SimplePeerText(_conn, const.I_AM_ACTIVE).send(require_confirmation=False)
                const.THIS_OBJECT.serialize(_conn)
        except socket.error:
            use.echo_print(f"Error sending status({const.THIS_OBJECT.status}) at {func_str(signal_status)}")
            peer_object.status = 0  # this makes that user as not active
        add_peer_accordingly(peer_object)


def sync_list() -> None:
    with const.LOCK_LIST_PEERS:
        list_copy = deque(peer_list.peers())
    while list_copy:
        if _controller.to_stop:
            return
        peer_obj = list_copy.popleft()
        if not ping_user(peer_obj):
            peer_obj.status = 0
            add_peer_accordingly(peer_obj)
            continue
    return


def notify_leaving_status_to_users():
    const.THIS_OBJECT.status = 0
    for peer in peer_list.peers():
        if not peer:
            continue
        # try:
        use.echo_print("::Notifying leaving ", peer.uri, peer.username)
        try:
            with connect.create_connection(peer.req_uri, timeout=5) as _conn:
                SimplePeerText(_conn, const.I_AM_ACTIVE).send(require_confirmation=False)
                const.THIS_OBJECT.serialize(_conn)
        except socket.error:
            use.echo_print(f"Error sending leaving status at {func_str(signal_status)}")

    # except socket.error as e:
        #     error_log(
        #         f"Error sending leaving status at {func_str(notify_leaving_status_to_users)} :  {e}")


def end_requests_connection() -> None:
    notify_leaving_status_to_users()
    _controller.stop()
    const.THIS_OBJECT.status = 0
    use.echo_print("::Requests connections ended")
    return None

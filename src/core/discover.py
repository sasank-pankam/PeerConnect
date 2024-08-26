import asyncio
import pickle
import socket

import kademlia.network
import kademlia.protocol
import kademlia.routing

from src.core import get_this_remote_peer
from ..avails import connect, const, use, RemotePeer


class CustomKademliaProtocol(kademlia.protocol.KademliaProtocol):

    ...


async def ping_all(ip, port, *, times=5):
    s = connect.UDPProtocol.create_sync_sock(const.IP_VERSION)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((ip, port))
    with s:
        for _ in range(times):
            s.sendto(const.ACTIVE_PING, ('<broadcast>', port))
            print("sent ", _, "time")


async def wait_for_replies(ip, port, timeout=5):
    sock = connect.UDPProtocol.create_async_sock(asyncio.get_running_loop(), const.IP_VERSION)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind((ip, port))
    sock.settimeout(timeout)
    with sock:
        try:
            data, ipaddr = await asyncio.wait_for(sock.arecvfrom(16), timeout=timeout)
            print("some data came ", data, ipaddr)
            return pickle.loads(data)
        except TimeoutError:
            return use.echo_print(f"Time Out Reached at {use.func_str(wait_for_replies)}")


async def search_network():
    ip, port = const.THIS_IP, const.PORT_REQ
    print(ip,port)

    task = asyncio.create_task(wait_for_replies(ip, port))
    await ping_all(ip, port)
    print('sent broadcast to network')
    return await task

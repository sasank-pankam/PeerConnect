import asyncio
import random
import traceback
from contextlib import AsyncExitStack

import _path  # noqa
from src.avails import WireData, const
from src.avails.events import MessageEvent
from src.avails.exceptions import ResourceBusy
from src.core.app import AppType, provide_app_ctx
from src.core.bandwidth import Watcher
from src.core.connector import Connector
from src.managers import message
from src.managers.statemanager import State
from src.transfers import HEADERS
from tests.test import get_a_peer, start_test1


async def test_connection():
    peer = get_a_peer()
    assert peer is not None, "no peers"
    connector = Connector()

    async with connector.connect(peer) as connection:
        watcher = Watcher()
        active, closed = await watcher.refresh(peer, connection)

        assert connection in active, "connection is not active"

    print("[TEST][PASSED] connected")


async def test_connection_pool():
    peer = get_a_peer()
    assert peer is not None, "[TEST][FAILED] no peers test"

    connector = Connector()
    const.MAX_CONNECTIONS_BETWEEN_PEERS = 3
    available_after = None
    connections = set()

    async def connection_wait_task(connection_wait):
        async with connection_wait:
            await connection_wait.wait_for(connector.is_connection_available(peer))
            print("[TEST][INFO] connection limit released")

    async with AsyncExitStack() as a_exit:
        for _ in range(const.MAX_CONNECTIONS_BETWEEN_PEERS):
            c = await a_exit.enter_async_context(connector.connect(peer))
            connections.add(c)

        try:
            await a_exit.enter_async_context(connector.connect(peer, raise_if_busy=True))
            print("[TEST][FAILED] connection limiting, no exception found")
        except ResourceBusy as rb:
            available_after = rb.available_after
            connection_wait_t = asyncio.create_task(connection_wait_task(available_after))
            print(f"[TEST][PASSED] connection limit test  {rb=}")

    assert available_after is not None, "[TEST][FAILED] no exception found, test "

    try:
        await asyncio.wait_for(connection_wait_t, 1)
        print("[TEST][PASSED] 'available after' condition test ", available_after)
    except TimeoutError:
        print("[TEST][FAILED] 'available after' condition check ", available_after)

    async with connector.connect(peer) as connection:
        pass

    assert connection in connections, "[TEST][FAILED] connection not found in the expected set"

    print("[TEST][PASSED] connection found in the expected set")


async def test_message(app_ctx: AppType):
    peer = get_a_peer()
    assert peer is not None

    check = asyncio.Event()

    ping = WireData(
        header=HEADERS.PING,
        peer_id=app_ctx.this_peer_id,
        msg_id=(ping_id := str(random.randint(1, 1000)))
    )

    def UNPingHandlerMock():
        async def handler(msg_event: MessageEvent):
            if msg_event.msg.msg_id == ping_id:
                check.set()
                print("ping received")

        return handler

    app_ctx.messages.dispatcher.register_handler(HEADERS.UNPING, UNPingHandlerMock())

    async with message.get_msg_conn(peer) as connection:
        await connection.send(ping)

    try:
        await asyncio.wait_for(check.wait(), 3)
    except TimeoutError:
        print("[TEST][FAILED] to send message reason: un ping not received")
    else:
        app_ctx.messages.dispatcher.remove_handler(HEADERS.UNPING)
        print("[TEST][PASSED]  message")


@provide_app_ctx
async def test_connections(app_ctx):
    print("waiting to get into network")
    await app_ctx.in_network.wait()

    print("starting testing connections")
    try:
        await test_connection()
        await test_connection_pool()
        await test_message(app_ctx)
    except Exception:
        print("#@" * 23)  # debug
        traceback.print_exc()
        raise


if __name__ == "__main__":
    s1 = State("testing connection", test_connections, is_blocking=True)

    start_test1((), (s1,))

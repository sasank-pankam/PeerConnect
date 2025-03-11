import _path  # noqa
from src.avails import DataWeaver, RemotePeer
from src.avails.useables import async_input
from src.conduit.headers import HANDLE
from src.core.app import provide_app_ctx
from src.managers.statemanager import State
from tests.test import start_test


@provide_app_ctx
async def test_message(app_ctx=None):
    message = await async_input()
    app_ctx.peer_list.add_peer(peer_obj=RemotePeer(
        byte_id=B'',
    ))
    DataWeaver(
        header=HANDLE.SEND_TEXT,

    )


if __name__ == '__main__':
    s = State("testing message", test_message)
    start_test(s)

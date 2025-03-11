import asyncio

import _path  # noqa
from src.avails.useables import async_input
from src.core import peers
from src.core.app import provide_app_ctx
from src.managers.statemanager import State
from tests.test import start_test


async def test_list_of_peers():
    while True:
        await async_input("ENTER")
        peer_list = await peers.get_more_peers()
        print(peer_list)


@provide_app_ctx
async def test_members(app_ctx=None):
    await asyncio.sleep(2)
    print("[INFO] members:", app_ctx.peer_list)


if __name__ == "__main__":
    members_test = State("testing members", test_members)
    peer_gathers = State("checking for peer gathering", test_list_of_peers, is_blocking=True)
    start_test(members_test, peer_gathers)

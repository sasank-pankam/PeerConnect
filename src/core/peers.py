"""
Helper functions to deal with peers in network
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

from kademlia import crawling

from src.avails import RemotePeer, use
from src.avails.exceptions import RemotePeerNotFound
from src.avails.remotepeer import convert_peer_id_to_byte_id
from src.conduit import webpage
from src.core import connectivity
from src.core.app import provide_app_ctx
from src.core.peerstore import node_list_ids
from src.core.search import SearchCrawler, get_gossip_searcher

_logger = logging.getLogger(__name__)


class PeerListGetter(crawling.ValueSpiderCrawl):
    peers_cache = {}
    previously_fetched_index = 0

    async def find(self):
        return await self._find(self.protocol.call_find_peer_list)

    @use.override
    async def _handle_found_values(self, values):
        peer = self.nearest_without_value.popleft()
        if peer:
            _logger.debug(f"found values {values}")
            await self.protocol.call_store_peers_in_list(peer, self.node.id, values)
        return values

    @classmethod
    async def get_more_peers(cls, peer_server) -> list[RemotePeer]:
        _logger.debug(f"previous index {cls.previously_fetched_index}")
        if cls.previously_fetched_index >= len(node_list_ids) - 1:
            cls.previously_fetched_index = 0

        find_list_id = node_list_ids[cls.previously_fetched_index]
        _logger.debug(f"looking into {find_list_id}")
        cls.previously_fetched_index += 1
        list_of_peers = await peer_server.get_list_of_nodes(find_list_id)

        if list_of_peers:
            cls.peers_cache.update({x.peer_id: x for x in list_of_peers})

            return list(set(list_of_peers))

        return []


@provide_app_ctx
def get_more_peers(*, app_ctx=None):
    peer_server = app_ctx.kad_server
    _logger.debug("getting more peers")
    return PeerListGetter.get_more_peers(peer_server)


@provide_app_ctx
async def gossip_search(search_string, *, app_ctx=None) -> AsyncIterator[RemotePeer]:
    searcher = get_gossip_searcher()
    async for peer in searcher.search_for(search_string, app_ctx.gossip.gossiper):
        yield peer


@provide_app_ctx
def search_for_nodes_with_name(search_string, *, app_ctx):
    """
    searches for nodes relevant to given ``:param search_string:``

    Returns:
         a generator of peers that matches with the search_string
    """

    return SearchCrawler.search_for_nodes(app_ctx.kad_server, search_string)


async def get_remote_peer_from_network(peer_network, peer_id):
    """Gets the ``RemotePeer`` object corresponding to ``:func RemotePeer.peer_id:`` from the network

    Just a wrapper around ``:method kademlia_network_server.get_remote_peer:``
    with conversions related to ids

    This call is expensive as it performs a distributed search across the network
    try using ``Dock.peer_list`` instead

    Args:
        peer_id(str): id to search for
        peer_network(PeerServer): peer network handler to use for searching
    Returns:
        RemotePeer | None
    """
    byte_id = convert_peer_id_to_byte_id(peer_id)
    _logger.debug(f"getting peer with id {peer_id} from network")
    return await peer_network.get_remote_peer(byte_id)


@provide_app_ctx
async def get_remote_peer(peer_id, *, app_ctx=None) -> Optional[RemotePeer]:
    """
    Just a helper, tries to check for peer_id in cached Dock.peer_list
    if there is a chance that cached remote peer object is expired then use ``:func: peers.get_remote_peer``
    if not found the performs a distributed search in the network
    """
    try:
        peer_obj = app_ctx.peer_list.get_peer(peer_id)
        if not peer_obj.is_online:
            app_ctx.peer_list.remove_peer(peer_id)
            raise KeyError
    except KeyError:
        peer_obj = await get_remote_peer_from_network(app_ctx.kad_server, peer_id)

    if peer_obj is None:
        err = RemotePeerNotFound()
        err.peer_id = peer_id
        raise err

    return peer_obj


# Callbacks called by kademila's routing mechanisms

def remove_peer(app_ctx, peer):
    """
    Does not directly remove peer
    Spawns a Task that tries to check connectivity status of peer
    If peer is reachable then it is not removed
    else peer is marked as offline
    Args:
        app_ctx(AppType): application context
        peer(RemotePeer): peer obj to remove
    """
    _logger.warning(f"a request for removal of {peer}")
    req, fut = connectivity.new_check(peer)

    if fut.done():
        # fast complete without spawning a Task if result is available
        return _may_be_remove(peer, fut.result())

    asyncio.create_task(_check_and_remove_if_needed(peer))


async def _check_and_remove_if_needed(peer: RemotePeer):
    req, fut = connectivity.new_check(peer)
    _may_be_remove(peer, await fut)


def _may_be_remove(peer, what):
    if not what:
        _logger.info(f"connectivity check failed, changing status of {peer} to offline")
        peer.status = RemotePeer.OFFLINE
        use.sync(webpage.update_peer(peer))
    else:
        _logger.info(f"connectivity check succeeded for {peer}")

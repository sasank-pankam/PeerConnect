"""

## How do we perform

1. A distributed search
2. Gather list of peers to display

in a p2p network, working with kademila's routing protocol?

### 1.1 If user can enter the peer id,
    then we can go through the network in O(log n),
    and get that peer details
    cons - But it's the worst UX

### 1.2 User enters a search string related to what ever he knows about other peer
    - we use that string to relate to peer's info and get that (from where?)

### 1.3 refer `2.3`

### 1.4 perform a gossip-based search
    - send a search request packet to the network
    - maintain a state for that request in the memory
    - if a peer relates to that string, it replies to that search request by sending a datagram containing its peer object
    - gather all the replies and cache them in `Storage`

    pros :
    - fast and efficient
    - can we scaled and pretty decentralized
    - cool

    cons :
    - no control over the search query (like cancelling that query) once it is passed into network
    - whole network will eventually respond to that search query
    - we have to ignore those packets


### 2.1 We need to display list of peers who are active in the network
    *.1 Need to iterate over the network over kademlia's routing protocol,
        for that we have to get the first id node in the network,
        append all the nodes found to a priority queue marking them visited if already queried,
        (sounds dfs or bfs), cache all that locally for a while

        cons - we have so much redundant peer objects passing here and there

    *.2 Full brute force
        we have some details of our logically nearest peers,
        so we brute force that list and get whatever they have
        again queried the list of peers sent by them in loop

        cons - we have so much redundant peer objects passing here and there

### 2.2 Preferred solution
    - we selected 20 buckets spaced evenly in the { 0 - 2 ^ 160 } node id space
    - give the bucket authority to nearest peer (closer to that bucket id)
    - each peer's adds themselves to that bucket when they join the network
        - peer's even ping the bucket and re-enter themselves within a time window

    - if a peer owns the bucket, another peer joins the network with the closest id to the bucket
      then a redistribution of bucket to that nearest peer will happen and all the authority over that bucket is
      transferred
    - problem, what if someone is querying that bucket in the meanwhile?
    (we can say that this is consistent hashing)

    - we can now show list of peer's available in the network by,
    step 1 : iterating over the `list of bucket id's`,
    step 2 : communicating  to the peer that is responsible for that bucket
    step 3 : perform a get list of peers RPC
    step 4 : show the list of peers to user

    - now we have peer gathering feature with paging

### 2.3

referring 1.3 :
    we can iterate over `list of bucket id's`,
    communicate to the peers that own bucket,
    ask them to search for relevant peers that match the given search string,
    return the list of peer's matched

    never dos:
        - cache the owner peer for a respective bucket as they can change pretty fast,
          always use kademlia's search protocol to get latest peer data
        - permanently cache peer's data received

"""
import asyncio
import logging
import time
from typing import AsyncIterator

from kademlia import crawling

from src.avails import GossipMessage, RemotePeer, WireData, use
from src.avails.events import GossipEvent
from src.core.app import provide_app_ctx
from src.core.peerstore import node_list_ids
from src.transfers import GOSSIP_HEADER

_logger = logging.getLogger(__name__)


class SearchCrawler:

    @classmethod
    async def get_relevant_peers_for_list_id(cls, kad_server, list_id):
        peer = RemotePeer(list_id)
        nearest = kad_server.protocol.router.find_neighbors(peer)
        crawler = crawling.NodeSpiderCrawl(
            kad_server.protocol,
            peer,
            nearest,
            kad_server.ksize,
            kad_server.alpha
        )
        responsible_nodes = await crawler.find()
        return responsible_nodes

    @classmethod
    async def search_for_nodes(cls, peer_server, search_string):
        _logger.info(f"new search request for : {search_string}")
        for peer in use.search_relevant_peers(peer_server.peer_list, search_string):
            yield peer

        for list_id in node_list_ids:
            peers = await cls.get_relevant_peers_for_list_id(peer_server, list_id)
            for peer in peers:
                _peers = await peer_server.protocol.call_search_peers(peer, search_string)
                yield _peers


class GossipSearch:
    class search_iterator(AsyncIterator):
        timeout = 3

        def __init__(self, message_id):
            self.message_id = message_id
            self.reply_queue: asyncio.Queue[RemotePeer] = asyncio.Queue()

        def add_peer(self, p):
            self.reply_queue.put_nowait(p)

        def __aiter__(self):
            self._start_time = asyncio.get_event_loop().time()
            return self

        async def __anext__(self):
            current_time = asyncio.get_event_loop().time()
            if current_time - self._start_time > self.timeout:
                raise StopAsyncIteration

            try:
                search_response = await asyncio.wait_for(self.reply_queue.get(),
                                                         timeout=self.timeout - (current_time - self._start_time))
                return search_response
            except asyncio.TimeoutError:
                raise StopAsyncIteration

    _message_state_dict: dict[str, search_iterator] = {}
    _search_cache = {}

    @classmethod
    def search_for(cls, find_str, gossiper):
        _logger.info(f"[GOSSIP][SEARCH] new search for: {find_str}")
        m = cls._prepare_search_message(find_str)
        gossiper.gossip_message(m)
        cls._message_state_dict[m.id] = f = cls.search_iterator(m.id)
        return f

    @classmethod
    @provide_app_ctx
    def request_arrived(cls, req_data: GossipMessage, _, app_ctx=None):
        search_string = req_data.message
        if app_ctx.this_remote_peer.is_relevant(search_string):
            return cls._prepare_reply(req_data.id, app_ctx.this_remote_peer)

    @staticmethod
    def _prepare_reply(reply_id, this_rp):
        gm = GossipMessage(
            WireData(
                header=GOSSIP_HEADER.SEARCH_REPLY,
                message=this_rp.serialized,
                created=time.time(),
                msg_id=reply_id,
                ttl=1,
            )
        )

        return bytes(gm)

    @staticmethod
    def _prepare_search_message(find_str):
        gm = GossipMessage(
            WireData(
                header=GOSSIP_HEADER.SEARCH_REQ,
                message=find_str,
                created=time.time(),
                msg_id=use.get_unique_id(),
                ttl=4,
            )
        )
        return gm

    @classmethod
    def reply_arrived(cls, reply_data: GossipMessage, addr):
        # Dock.global_gossip.message_arrived(reply_data, addr)
        try:
            result_iter = cls._message_state_dict[reply_data.id]
            if m := reply_data.message:
                m = RemotePeer.load_from(m)
            result_iter.add_peer(m)
        except KeyError as ke:
            _logger.debug("[GOSSIP][SEARCH] invalid gossip search response id", exc_info=ke)


def GossipSearchReqHandler(searcher, transport, app_ctx,
                           gossip_handler):
    """
    Working:
        * GossipEvent is passed into the handler when someone tries to search for some user
        * We only reply if the search string relates to us.
        * All the decision-making is done by searcher, just a helper to send reply returned by searcher
        * Gossips the received search request received using gossiper

    Args:
        searcher(GossipSearch): delegates search request event to this object
        transport(GossipTransport): transport to use to send messages
        app_ctx(ReadOnlyAppType): application global context
        gossip_handler(GlobalGossipMessageHandler): handler that handles gossip message that has arrived

    """

    async def handle(event: GossipEvent):
        if not app_ctx.gossip.gossiper.is_seen(event.message):
            await gossip_handler(event)
        if reply := searcher.request_arrived(*event):
            return transport.sendto(reply, event.from_addr)

    return handle


def GossipSearchReplyHandler(gossiper, gossip_searcher):
    async def handle(event: GossipEvent):
        print("[GOSSIP][SEARCH] reply received:", event.message, "for", event.from_addr)
        gossiper.message_arrived(*event)
        return gossip_searcher.reply_arrived(*event)

    return handle


def get_gossip_searcher():
    return GossipSearch


def register_handlers(app_ctx, g_dispatcher, gossip_message_handler, gossip_transport):
    gossip_searcher = get_gossip_searcher()
    req_handler = GossipSearchReqHandler(
        GossipSearch(),
        gossip_transport,
        app_ctx,
        gossip_message_handler
    )
    reply_handler = GossipSearchReplyHandler(app_ctx.gossip.gossiper, gossip_searcher)
    g_dispatcher.register_handler(GOSSIP_HEADER.SEARCH_REQ, req_handler)
    g_dispatcher.register_handler(GOSSIP_HEADER.SEARCH_REPLY, reply_handler)

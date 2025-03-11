from src.avails import BaseDispatcher, GossipMessage, const
from src.avails.events import GossipEvent
from src.avails.mixins import QueueMixIn
from src.core import search
from src.core.app import AppType, ReadOnlyAppType
from src.transfers import GOSSIP_HEADER, GossipTransport, REQUESTS_HEADERS, \
    RumorMongerProtocol, SimpleRumorMessageList


class GlobalGossipRumorMessageList(SimpleRumorMessageList):
    __slots__ = "global_peer_list",

    def __init__(self, global_peer_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.global_peer_list = global_peer_list

    def _get_list_of_peers(self):
        return set(self.global_peer_list.keys())


class GlobalRumorMonger(RumorMongerProtocol):
    def __init__(self, transport, global_peer_list):
        super().__init__(transport, global_peer_list,
                         GlobalGossipRumorMessageList(global_peer_list, const.NODE_POV_GOSSIP_TTL))


def GlobalGossipMessageHandler(app_ctx: ReadOnlyAppType):
    gossip_handler = app_ctx.gossip.gossiper

    async def handle(event: GossipEvent):
        print("[GOSSIP] new message arrived", event.message, "from", event.from_addr)
        return gossip_handler.message_arrived(*event)

    return handle


class GossipDispatcher(QueueMixIn, BaseDispatcher):
    async def submit(self, event):
        gossip_message = GossipMessage(event.request)
        handler = self.registry[gossip_message.header]
        g_event = GossipEvent(gossip_message, event.from_addr)
        await handler(g_event)


async def initiate_gossip(data_transport, req_dispatcher, app_ctx: AppType):
    gossip_transport = GossipTransport(data_transport)
    g_dispatcher = GossipDispatcher()

    app_ctx.gossip.transport = gossip_transport
    app_ctx.gossip.gossiper = GlobalRumorMonger(gossip_transport, app_ctx.peer_list)
    app_ctx.gossip.dispatcher = g_dispatcher

    gossip_message_handler = GlobalGossipMessageHandler(app_ctx.read_only())

    search.register_handlers(
        app_ctx.read_only(),
        g_dispatcher,
        gossip_message_handler,
        gossip_transport
    )

    g_dispatcher.register_handler(GOSSIP_HEADER.MESSAGE, gossip_message_handler)
    req_dispatcher.register_handler(REQUESTS_HEADERS.GOSSIP, g_dispatcher)
    await app_ctx.exit_stack.enter_async_context(g_dispatcher)
    app_ctx.gossip.dispatcher = g_dispatcher
    return g_dispatcher


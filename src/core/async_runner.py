import asyncio
from typing import override

from src.core.app import App
from src.avails import use

class AnotherRunner(asyncio.Runner):  # noqa # dirty dirty dirty
    def __init__(self, *, app_ctx, debug=None, loop_factory=None):
        self.app_ctx: App = app_ctx
        super().__init__(debug=debug, loop_factory=loop_factory)

    @override
    def _on_sigint(self, signum, frame, main_task):
        self.app_ctx.finalizing.set()
        use.sync(self.app_ctx.state_manager_handle.put_state(None))
        return super()._on_sigint(signum, frame, main_task)

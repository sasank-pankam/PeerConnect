import asyncio
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from src.avails import RemotePeer, connect, const
from src.avails.exceptions import CancelTransfer, InvalidStateError, TransferIncomplete
from src.transfers import TransferState
from src.transfers._logger import logger


class AbstractStatusMix(ABC):
    @abstractmethod
    def update_status(self, status): ...

    @abstractmethod
    def should_yield(self): ...

    @abstractmethod
    def status_setup(self, prefix, initial_limit, final_limit): ...

    @abstractmethod
    def close(self): ...


class AbstractTransferHandle(AbstractAsyncContextManager, ABC):
    status_updater: AbstractStatusMix
    peer: RemotePeer
    state: TransferState
    to_stop: bool
    _expected_errors: set
    main_task: asyncio.Task | None

    @abstractmethod
    async def continue_transfer(self):
        """When some error happens in the initial state and that error has been recovered
        """

    @abstractmethod
    def connection_made(self, connection: connect.Connection):
        """Connection has arrived that is related to this handle
        """

    @abstractmethod
    def pause(self):
        """Pause send/recv for a moment, usually until resume is called"""

    @abstractmethod
    def resume(self):
        """Resume send/recv"""

    @abstractmethod
    async def cancel(self):
        """Cancel the transfer"""

    @property
    @abstractmethod
    def id(self):
        """ID of the transfer"""

    @property
    @abstractmethod
    def current_file(self):
        """File under transfer"""

    @property
    def _log_prefix(self):
        return f"[{self.__class__}]"


class CommonCancelMixIn:
    async def cancel(self):
        """Cancel the transfer"""
        if self.state not in (TransferState.SENDING, TransferState.RECEIVING, TransferState.PAUSED):
            raise InvalidStateError(f"state is not expected to be in {self.state=}")

        self.to_stop = True
        self._expected_errors.add(ct := CancelTransfer())
        self.main_task.set_exception(ct)
        await self.main_task


class AbstractSender(AbstractTransferHandle):
    @abstractmethod
    def __init__(self, peer_obj, transfer_id, file_list, status_updater): ...

    @abstractmethod
    async def send_files(self):
        """Send files passed into object's constructor"""


class AbstractReceiver(AbstractTransferHandle):
    @abstractmethod
    def __init__(self, peer_obj, transfer_id, download_path, status_updater): ...

    @abstractmethod
    async def recv_files(self):
        """Receive files"""


class CommonAExitMixIn(AbstractAsyncContextManager):
    __slots__ = ()

    async def __aexit__(self, exc_type, exc_value, traceback, /):
        if exc_type not in self._expected_errors:
            return

        to_return = None
        if exc_type is TransferIncomplete and self.state is not TransferState.PAUSED:
            logger.warning(
                f"state miss match at files.Receiver, conditions {exc_type=},{exc_value=}, "
                f"expected state to be PAUSED, "
                f"found {self.state=}"
            )
            to_return = True

        if exc_type is CancelTransfer and self.state is TransferState.ABORTING:
            if const.debug:
                print("SUPPRESSING error cause its expected", traceback)
            to_return = True
        self._expected_errors.clear()
        return to_return


class CommonExceptionHandlersMixIn:
    def _raise_transfer_incomplete_and_change_state(self, prev_error=None, detail=""):
        logger.debug(f'{self._log_prefix} changing state to paused')
        self.state = TransferState.PAUSED
        err = TransferIncomplete(detail)
        err.__cause__ = prev_error
        self._expected_errors.add(err)
        raise err from prev_error

    def _handle_os_error(self, err, detail=""):
        logger.error(f"{self._log_prefix} got error, pausing transfer", exc_info=True)
        self.state = TransferState.PAUSED
        ti = TransferIncomplete(detail)
        self._expected_errors.add(ti)
        raise ti from err

    def _handle_cancel_transfer(self, ct):
        if ct in self._expected_errors:
            # we definitely reach here if we are cancelled using AbstractTransferHandle.cancel
            logger.error(f"{self._log_prefix} cancelled receiving, changing state to ABORTING", exc_info=True)
            self.state = TransferState.ABORTING
        else:
            raise

    def _handle_transfer_incomplete(self, err):
        if err in self._expected_errors:
            raise
        self._expected_errors.add(err)
        logger.error(f"{self._log_prefix} got error, pausing transfer", exc_info=True)
        self.state = TransferState.PAUSED
        raise err

    def handle_exception(self, exp):
        if isinstance(exp, CancelTransfer):
            self._handle_cancel_transfer(exp)
        if isinstance(exp, TransferIncomplete):
            self._handle_transfer_incomplete(exp)
        if isinstance(exp, OSError):
            self._handle_os_error(exp)

        raise exp


class PauseMixIn:
    __slots__ = ()

    def pause(self):
        self.state = TransferState.PAUSED
        self.send_func.pause()
        self.recv_func.pause()
        self.to_stop = True

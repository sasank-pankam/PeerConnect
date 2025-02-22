from asyncio import CancelledError, InvalidStateError
import asyncio
from contextlib import aclosing
from enum import auto, Enum
from itertools import count
from pathlib import Path
import struct
from typing import Callable
from src.avails.exceptions import CancelTransfer, TransferIncomplete
from src.avails import use
from src.transfers import TransferState
from src.transfers.abc import (
    AbstractReceiver,
    AbstractSender,
    CommonAExitMixIn,
    CommonExceptionHandlersMixIn,
)
from src.avails import connect, const
from src.transfers.files._fileobject import FileItem
from src.transfers.status import StatusIterator
from .sender import Sender as list_file_sender
from .receiver import Receiver as list_file_receiver

CHUNK_SIZE = 30 * 1024 * 1024
CHUNK_ID = 0


class _ConnectionState(Enum):
    NOT_DONE = auto()
    INITIATED = auto()
    DONE = auto()


class Sender(CommonAExitMixIn, CommonExceptionHandlersMixIn, AbstractSender):
    version = const.VERSIONS["FO"]
    timeout = const.DEFAULT_TRANSFER_TIMEOUT

    def __init__(
        self, peer_obj, transfer_id, file: Path, status_updater: StatusIterator
    ):
        self.peer = peer_obj
        self._tf_id = transfer_id
        self.big_file = FileItem(file, seeked=0)
        self.big_file.name = file.parts[-1]
        self.status_updater = status_updater

        self.senders = {}
        self.senders_id = count()

        self.current_parts = set()
        self.main_task = None
        self.failed_chunks = []

        self.task_group = set()
        self.to_stop = False

        self.state = TransferState.PREPARING

        self.files_iterator = self._bigfile_chunk_generator()
        self._expected_errors = set()

    def _bigfile_chunk_generator(self):
        size = self.big_file.size
        start = 0
        for id, i in enumerate(range(start, size, CHUNK_SIZE)):
            if len(self.failed_chunks):
                yield True, self.failed_chunks.pop(0)
            yield False, (id, i, i + CHUNK_SIZE)

    async def send_files(self):
        self.main_task = asyncio.current_task()
        try:
            async for _ in self.status_updater:
                yield _
        except CancelledError:
            await self.cancel()
            raise

        except Exception as e:
            self.handle_exception(e)

    async def cancel(self):
        self.to_stop = True
        self.state = TransferState.ABORTING
        self._expected_errors.add(ct := CancelTransfer())
        await self.status_updater.stop(
            TransferIncomplete("User canceled the transfer")
        )  # review
        for task in self.task_group:
            # change this to a custom exception that specifically tells that this operation is cancelled
            task.cancel(ct)

    async def __aenter__(self):
        self.setup_event = asyncio.get_running_loop().create_future()
        self.setup_state = _ConnectionState.NOT_DONE
        self.state = TransferState.CONNECTING
        self.status_updater.status_setup(
            f"[DIR] receiving file: {self.big_file}",
            self.big_file.seeked,
            self.big_file.size,
        )
        self.task_group = set()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback, /):
        if exc_type == TransferIncomplete:
            for tk in self.task_group:
                tk.cancel()
            return True
        await asyncio.gather(*self.task_group)
        return False

    @property
    def id(self):
        return self._tf_id

    @property
    def current_file(self):
        """Note: different from other senders this may can have multiple active sending chunks"""
        return tuple(self.current_parts)

    def connection_made(
        self,
        sender: Callable[[bytes], None] | connect.Sender,
        receiver: Callable[[int], bytes] | connect.Receiver,
    ):
        """
        assuming this function is called when a new connection is made to send this file
        """
        index = next(self.senders_id)
        pair = (sender, receiver)
        task = asyncio.create_task(self.send(pair, index))
        self.task_group.add(task)

    async def send(self, pair, index):
        await self._ensure_ok(pair)
        sender, receiver = pair
        status_updater = StatusIterator(self.status_updater.yield_freq)
        files_sender = list_file_sender(
            self.peer, f"{self._tf_id}-{index}", [], status_updater
        )
        files_sender.connection_made(sender, receiver)
        self.senders[index] = files_sender

        for failed, big_chunk in self.files_iterator:
            id, start, end = big_chunk
            temp_file = FileItem(self.big_file.path, seeked=start)
            temp_file.size = end
            temp_file.name = id

            try:
                await files_sender._send_file_item(temp_file)

                if failed:
                    await self._recover(id, files_sender, temp_file)

                async with aclosing(files_sender.send_one_file(temp_file)) as loop:
                    async for seeked in loop:
                        pass  # skipping the upadte for small file sending part

                ack = await receiver(1)  # for ack
                if ack != b"\x01":
                    raise ValueError(f"expected a \\x01 but {ack} came.")
            except Exception as e:
                self.failed_chunks.append(big_chunk)
                self.handle_exception(e)

            self.current_parts.remove(big_chunk)

    # TODO: rethink this method will not work if other connections are also failed (wait in the whilee loop until it is set)
    async def _ensure_ok(self, pair):
        if self.setup_state == _ConnectionState.DONE:
            return

        if self.setup_state == _ConnectionState.INITIATED:
            await self.setup_event
            return
        self.setup_state = _ConnectionState.INITIATED
        await self._negotiate(pair)
        self.setup_state = _ConnectionState.DONE
        self.setup_event.set_result(True)

    async def _negotiate(self, pairs):
        sender, receiver = pairs
        try:
            # a signal that says there is more to receive
            await sender(b"\x01")
            file_object = bytes(self.big_file)
            file_packet = struct.pack("!I", len(file_object)) + file_object
            await sender(file_packet)
            sig = await receiver(1)
            if sig != b"\x01":
                self.setup_state = _ConnectionState.NOT_DONE
                self.setup_event.set_result(True)
                raise ValueError("Handeshake not complete")
        except Exception as exp:
            self.handle_exception(exp)

    async def _recover(self, id, receiver, temp_file):
        try:
            temp_file.seeked = await use.recv_int(receiver, use.LONG_INT)
        except ValueError as ve:
            self._raise_transfer_incomplete_and_change_state(ve)

    async def continue_transfer(self):
        self.main_task = asyncio.current_task()
        if not self.state == TransferState.PAUSED or self.to_stop is True:
            raise InvalidStateError(f"{self.state=}, {self.to_stop=}")

        # _logger.debug(f"FILE[{self._tf_id}] changing state to sending")
        self.state = TransferState.SENDING

        # continuing with remaining transfer
        async with aclosing(self.send_files()) as file_sender:
            async for items in file_sender:
                yield items


class Receiver(CommonAExitMixIn, CommonExceptionHandlersMixIn, AbstractReceiver):
    version = const.VERSIONS["FO"]

    def __init__(self, peer_obj, transfer_id, download_path, status_updater):
        self.peer = peer_obj
        self._tf_id = transfer_id
        self.status_updater = status_updater

        self.download_path = download_path

        self.receivers = {}
        self.receivers_id = count()

        self.current_parts = set()
        self.main_task = None
        self.failed_chunks = {}

        self.task_group = set()
        self.to_stop = False

        self.state = TransferState.PREPARING
        self.big_file: FileItem | None = None

        self._expected_errors = set()

    async def recv_files(self):
        self.main_task = asyncio.current_task()
        try:
            async for _ in self.status_updater:
                yield _
        except CancelledError:
            await self.cancel()
            raise

        except Exception as e:
            self.handle_exception(e)

    async def cancel(self):
        self.to_stop = True
        self.state = TransferState.ABORTING
        self._expected_errors.add(ct := CancelTransfer())
        await self.status_updater.stop(
            TransferIncomplete("User canceled the transfer")
        )  # review
        for task in self.task_group:
            # change this to a custom exception that specifically tells that this operation is cancelled
            task.cancel(ct)

    async def __aenter__(self):
        self.setup_event = asyncio.get_running_loop().create_future()
        self.setup_state = _ConnectionState.NOT_DONE
        self.state = TransferState.CONNECTING
        self.task_group = set()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback, /):
        if exc_type == TransferIncomplete:
            for tk in self.task_group:
                tk.cancel()
            return True
        await asyncio.gather(*self.task_group)
        return False

    @property
    def id(self):
        return self._tf_id

    @property
    def current_file(self):
        """Note: different from other senders this may can have multiple active sending chunks"""
        return tuple(self.current_parts)

    def connection_made(
        self,
        sender: Callable[[bytes], None] | connect.Sender,
        receiver: Callable[[int], bytes] | connect.Receiver,
    ):
        """
        assuming this function is called when a new connection is made to send this file
        """
        index = next(self.receivers_id)
        pair = (sender, receiver)
        task = asyncio.create_task(self.recv(pair, index))
        self.task_group.add(task)

    async def recv(self, pair, index):
        await self._ensure_ok(pair)
        sender, receiver = pair
        status_updater = StatusIterator(self.status_updater.yield_freq)
        files_receiver = list_file_receiver(
            self.peer, f"{self._tf_id}-{index}", self.download_path, status_updater
        )
        files_receiver.connection_made(sender, receiver)
        self.receivers[index] = files_receiver

        while True:
            temp_file = await files_receiver._recv_file_item()
            id = temp_file.name
            temp_file = FileItem(
                self.download_path
                / f"{self.big_file.path.name}.{id}{const.FILE_ERROR_EXT}",
                seeked=temp_file.seeked,
            )

            ctrl = await receiver(1)
            if (
                ctrl == "\x00"
            ):  # this is the metadata part(especially the chunk is already there or not)
                await self._recover(id, sender, temp_file)

            files_receiver._current_file = temp_file
            async with aclosing(files_receiver._receive_single_file()) as loop:
                async for seeked in loop:
                    pass  # skipping the upadte for small file sending part

            ack = b"\x01"
            await sender(ack)

    async def _ensure_ok(self, pair):
        if self.setup_state == _ConnectionState.DONE:
            return

        if self.setup_state == _ConnectionState.INITIATED:
            await self.setup_event
            return
        self.setup_state = _ConnectionState.INITIATED
        await self._negotiate(pair)
        self.setup_state = _ConnectionState.DONE
        self.setup_event.set_result(True)

    async def _negotiate(self, pair):
        sender, receiver = pair
        try:
            # a signal that says there is more to receive
            sig = await receiver()
            if sig != b"\x01":
                raise ValueError("Expected signal not received")
            lenght = use.recv_int(receiver, use.SHORT_INT)
            self.big_file = FileItem.load_from(
                await receiver(lenght), self.download_path
            )
            await sender(sig)
            self.status_updater.status_setup(
                f"[DIR] receiving file: {self.big_file.name}",
                self.big_file.seeked,
                self.big_file.size,
            )
        except Exception as exp:
            self.handle_exception(exp)

    async def _recover(self, id, sender, temp_file: FileItem):
        try:
            seeked = self.failed_chunks.get(id, 0)
            temp_file.seeked = seeked
            await sender(seeked)
        except ValueError as ve:
            self._raise_transfer_incomplete_and_change_state(ve)

    async def continue_transfer(self):
        if not self.state == TransferState.PAUSED or self.to_stop is True:
            raise InvalidStateError(f"{self.state=}, {self.to_stop=}")

        # _logger.debug(f"FILE[{self._tf_id}] changing state to sending")
        self.state = TransferState.SENDING

        # continuing with remaining transfer
        async with aclosing(self.recv_files()) as file_sender:
            async for items in file_sender:
                yield items

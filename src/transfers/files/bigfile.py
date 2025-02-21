from asyncio.exceptions import CancelledError
import functools
from enum import Enum, auto
from pathlib import Path
from typing import BinaryIO
from itertools import count
import mmap
import os
import asyncio
from collections.abc import Callable
from contextlib import aclosing
import struct
from src.avails import connect
from src.avails.exceptions import CancelTransfer, TransferIncomplete
from src.avails.wire import WireData
from src.transfers.abc import (
    AbstractReceiver,
    AbstractSender,
    CommonAExitMixIn,
    CommonExceptionHandlersMixIn,
)
from src.transfers.files.receiver import recv_file_contents
from src.transfers.status import StatusIterator
from src.transfers.files._fileobject import FileItem
from src.transfers import thread_pool_for_disk_io
from src.transfers import TransferState
from src.transfers.files.sender import send_actual_file
from src.avails import const, use

CHUNK_SIZE = 30 * 1024 * 1024
CHUNK_ID = 0


class ConnectionState(Enum):
    NOT_DONE = auto()
    INITIATED = auto()
    DONE = auto()


class Sender(CommonAExitMixIn, CommonExceptionHandlersMixIn, AbstractSender):
    version = const.VERSIONS["FO"]
    timeout = const.DEFAULT_TRANSFER_TIMEOUT

    def __init__(
        self, peer_obj, transfer_id, file_path: Path, status_updater: StatusIterator
    ):
        self.full_file = FileItem(file_path, seeked=0)
        self.file = FileItem(file_path.parts[-1], seeked=0)
        self.peer_obj = peer_obj
        self._file_id = transfer_id
        self.status_iter = status_updater
        self.io_pairs = {}
        self.io_pair_index_generator = count()
        self.state = TransferState.PREPARING
        self.failed_chunks = []
        self.file_iterator = self.bigfile_chunk_generator()
        self.is_stop = False
        self.current_sending = set()
        self._expected_errors = set()
        self.main_task = None

    def bigfile_chunk_generator(self):
        size = self.file.size
        start = 0
        for id, i in enumerate(range(start, size, CHUNK_SIZE)):
            if len(self.failed_chunks):
                yield self.failed_chunks.pop(0)
            yield id, i, i + CHUNK_SIZE

    async def __aenter__(self):
        self.setup_event = asyncio.get_running_loop().create_future()
        self.setup_state = ConnectionState.NOT_DONE
        self.state = TransferState.CONNECTING
        self.status_iter.status_setup(
            f"[DIR] receiving file: {self.file}", self.file.seeked, self.file.size
        )
        self.task_group = set()
        return self

    @property
    def id(self):
        return self._file_id

    @property
    def current_file(self):
        """Note: different from other senders this may can have multiple active sending chunks"""
        return tuple(self.current_sending)

    def connection_made(
        self,
        sender: Callable[[bytes], None] | connect.Sender,
        receiver: Callable[[int], bytes] | connect.Receiver,
    ):
        """
        assuming this function is called when a new connection is made to send this file
        """
        index = next(self.io_pair_index_generator)
        pair = (sender, receiver)
        self.io_pairs[index] = pair
        task = asyncio.create_task(self.send(pair, index))
        self.task_group.add(task)

    async def _ensure_ok(self, index):
        if self.setup_state == ConnectionState.DONE:
            return

        if self.setup_state == ConnectionState.INITIATED:
            await self.setup_event
            return
        self.setup_state = ConnectionState.INITIATED
        await self._negotiate(index)
        self.setup_state = ConnectionState.DONE
        self.setup_event.set_result(True)

    async def _negotiate(self, pair_index):
        sender, _ = self.io_pairs[pair_index]
        try:
            # a signal that says there is more to receive
            await sender(b"\x01")
            file_object = bytes(self.file)
            file_packet = struct.pack("!I", len(file_object)) + file_object
            await sender(file_packet)
        except Exception as exp:
            self.handle_exception(exp)

    async def send_files(self):
        self.main_task = asyncio.current_task()
        try:
            async for _ in self.status_iter:
                yield _
        except CancelledError:
            await self.cancel()
            raise

        except Exception as e:
            self.handle_exception(e)

    async def cancel(self):
        self.is_stop = True
        self.state = TransferState.ABORTING
        self._expected_errors.add(ct := CancelTransfer())
        await self.status_iter.stop(
            TransferIncomplete("User canceled the transfer")
        )  # review
        for task in self.task_group:
            # change this to a custom exception that specifically tells that this operation is cancelled
            task.cancel(ct)

    async def send(self, io_pair, index):
        await self._ensure_ok(index)
        sender, receiver = io_pair

        for big_chunk in self.file_iterator:
            id, start, end = big_chunk
            temp_file = FileItem(self.file.path, seeked=start)
            temp_file.size = end

            file_send_request = WireData(
                header="finalize_later",
                file_id=id,
            )

            raw_bytes = bytes(file_send_request)
            data_size = struct.pack("!I", len(raw_bytes))

            self.current_sending.add(big_chunk)
            try:
                await sender(data_size + raw_bytes)
                async with aclosing(
                    send_actual_file(sender, temp_file)
                ) as chunk_sender:
                    async for seeked in chunk_sender:
                        if self.is_stop:
                            break
                        self.status_iter.update_status(
                            seeked
                        )  # updating even for a small chunk
            except BaseException as e:
                if len(e.args):
                    self.handle_exception(e.args[0])
                else:
                    raise
            finally:
                if (
                    not temp_file.seeked == temp_file.size
                ):  # a case when transfer is returned before completely sending the file
                    # adding the failed chunk to failed list so that the another pair get associated for this chunk
                    self.failed_chunks.append(big_chunk)
                    del self.io_pairs[index]
                    break
                self.current_sending.remove(id)

    async def continue_transfer(self):
        return

    async def __aexit__(self, exec_type, exec_val, exec_tb):
        if exec_type == TransferIncomplete:
            for tk in self.task_group:
                tk.cancel()
            return True
        await asyncio.gather(*self.task_group)
        return False


if const.IS_WINDOWS:
    # must be fully qualified name  no reletive paths
    def windows_merge(fsrc: BinaryIO, fdst: BinaryIO):
        src_size = os.path.getsize(fsrc.name)
        dst_size = os.path.getsize(fdst.name)

        # Align to allocation granularity (64KB on Windows)
        allocation_granularity = mmap.ALLOCATIONGRANULARITY
        aligned_offset = (dst_size // allocation_granularity) * allocation_granularity
        map_size = dst_size + src_size - aligned_offset

        # Extend destination file
        fdst.truncate(dst_size + src_size)

        # Memory map source file
        src_map = mmap.mmap(fsrc.fileno(), src_size, access=mmap.ACCESS_READ)

        try:
            # Memory map destination file
            dst_map = mmap.mmap(
                fdst.fileno(),
                map_size,
                access=mmap.ACCESS_WRITE,
                offset=aligned_offset,
            )

            # Calculate write position relative to mapped region
            write_pos = dst_size - aligned_offset
            dst_map[write_pos : write_pos + src_size] = src_map[:]
        finally:
            src_map.close()
            dst_map.close()

    merge = windows_merge

else:
    # must be fully qualified name  no reletive paths
    def others_merge(fsrc: BinaryIO, fdst: BinaryIO):
        os.sendfile(fsrc.fileno(), fdst.fileno(), 0, os.path.getsize(fdst.name))

    merge = others_merge


async def merge_all_and_delete(
    download_path: Path, final_file: FileItem, parts: dict[int, FileItem]
):
    files = sorted(parts.items(), key=lambda x: x[0])

    with open(download_path / final_file.path, "ab") as final:
        final.seek(0)

        async def asyncify_merge(curr: BinaryIO):
            await asyncio.get_running_loop().run_in_executor(
                thread_pool_for_disk_io, functools.partial(merge, final, curr)
            )

        for ind, file in files:
            with open(download_path / file.path, "rb") as curr:
                await asyncify_merge(curr)  # Append file2 to file1


class Receiver(CommonAExitMixIn, CommonExceptionHandlersMixIn, AbstractReceiver):
    version = const.VERSIONS["FO"]

    def __init__(self, peer_obj, file_id, download_path, status_updater):
        self.state = TransferState.PREPARING
        self.peer = peer_obj
        self._file_id = file_id
        self.download_path = download_path
        self.to_stop = False  # only set when Receiver.cancel is called
        self.file = FileItem(download_path, seeked=0)
        self.io_pairs = {}
        self.io_pair_index_generator = count()
        self.status_iter = status_updater
        self._expected_errors = set()
        self.parts = {}
        self.task_group = set()
        self.current_receiving = set()
        self.main_task = None

    def connection_made(
        self,
        sender: Callable[[bytes], None] | connect.Sender,
        receiver: Callable[[int], bytes] | connect.Receiver,
    ):
        ind = next(self.io_pair_index_generator)
        pair = (sender, receiver)
        self.io_pairs[ind] = pair
        task = asyncio.create_task(self.recv(pair, ind))
        self.task_group.add(task)

    async def _ensure_ok(self, index):
        if self.setup_state == ConnectionState.DONE:
            return

        if self.setup_state == ConnectionState.INITIATED:
            await self.setup_event
            return
        self.setup_state = ConnectionState.INITIATED
        try:
            await self._negotiate(index)
        except Exception:
            self.setup_state = ConnectionState.NOT_DONE
            raise
        self.setup_state = ConnectionState.DONE
        self.setup_event.set_result(True)

    async def _negotiate(self, pair_index):
        sender, receiver = self.io_pairs[pair_index]
        handshake_byte = await receiver(1)
        if handshake_byte != b"\x01":
            raise ValueError(f"Excepted a '\\x01 but received {handshake_byte=}")

        try:
            file_item_size = await use.recv_int(receiver)
        except ValueError as ve:
            raise TransferIncomplete from ve
        try:
            raw_file_item = await receiver(file_item_size)
        except OSError as oe:
            raise TransferIncomplete from oe
        else:
            self.file = FileItem.load_from(raw_file_item, self.download_path)

    async def __aenter__(self):
        self.setup_state = ConnectionState.NOT_DONE
        self.setup_event = asyncio.get_running_loop().create_future()
        self.status_iter.status_setup(
            f"[DIR] receiving file: {self.file}", self.file.seeked, self.file.size
        )
        return self

    async def recv_files(self):
        self.main_task = asyncio.current_task()
        try:
            async for _ in self.status_iter:
                yield _
        except CancelledError:
            await self.cancel()
            raise

    @property
    def id(self):
        return self._file_id

    @property
    def current_file(self):
        """Note: different from other senders this may can have multiple active sending chunks"""
        return tuple(self.current_receiving)

    async def recv(self, io_pair: tuple[Callable, Callable], ind: int):
        await self._ensure_ok(ind)

        sender, receiver = io_pair
        while self.is_stop:
            data_length = use.recv_int(
                receiver
            )  # finalize_later  decide to handle exception(ValueError)

            data = WireData.load_from(await receiver(data_length))

            file_id = data.body["file_id"]
            self.current_receiving.add(file_id)
            new_file = FileItem(
                f"{self.file.path.stem}[{file_id}]{constants.FILE_ERROR_EXT}", seeked=0
            )

            if new_file.path.exists():
                new_file.path.unlink()

            new_file.path.touch()

            # validatename(new_file, constants.PATH_DOWNLOAD)
            try:
                async for update in recv_file_contents(
                    receiver,
                    FileItem(self.download_path / new_file.path, seeked=0),
                ):
                    self.status_iter.update_status(update)
            except BaseException as e:
                if len(e.args):
                    self.handle_exception(e.args[0])  # handle custom cancel
                else:
                    raise  # only raise for innterrupts
            finally:
                if new_file.seeked < CHUNK_SIZE:
                    # this chunk is not completelty done
                    new_file.path.unlink()  # delete the incomplete file
                    return
            self.parts[file_id] = new_file
            self.current_receiving.remove(file_id)

    async def continue_recv(self):
        return

    async def cancel(self):
        self.is_stop = True
        self.state = TransferState.ABORTING
        self._expected_errors.add(ct := CancelTransfer())
        await self.status_iter.stop(
            TransferIncomplete("User canceled the transfer")
        )  # review
        for task in self.task_group:
            task.set_exception(ct)

    async def __aexit__(self, e_type, e_val, e_tb):
        # todo check for raised errors
        if e_type == TransferIncomplete:
            for tk in self.task_group:
                tk.cancel()  # finalize_later
        await asyncio.gather(*self.task_group)

        await merge_all_and_delete(self.download_path, self.file, self.parts)

"""Small cross-process lease preventing two Studio instances driving one Tube."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


class DeviceLease:
    """Hold an advisory one-byte file lock for the lifetime of a Tube connection."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._stream: BinaryIO | None = None

    def acquire(self) -> bool:
        if self._stream is not None:
            return True
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            stream = self.path.open("a+b")
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            if "stream" in locals():
                stream.close()
            return False
        self._stream = stream
        return True

    def release(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def __enter__(self) -> DeviceLease:
        if not self.acquire():
            raise RuntimeError("Device is already leased by another process.")
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

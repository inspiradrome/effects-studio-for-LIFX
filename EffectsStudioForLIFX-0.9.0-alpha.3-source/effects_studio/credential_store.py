"""Small Windows Credential Manager wrapper for the optional OpenAI key."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Protocol

# Keep the existing target name so upgrades retain access to keys saved by older
# builds. It is an internal compatibility identifier, not the displayed product name.
CREDENTIAL_TARGET = "LIFX Effects Studio/OpenAI API Key"
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_ERROR_NOT_FOUND = 1168


class CredentialStoreError(RuntimeError):
    """Windows could not read or update the saved credential."""


class CredentialStoreProtocol(Protocol):
    def load(self) -> str | None: ...

    def save(self, secret: str) -> None: ...

    def delete(self) -> None: ...


if sys.platform == "win32":

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    _PCREDENTIALW = ctypes.POINTER(_CREDENTIALW)


class WindowsCredentialStore:
    """Persist a generic credential encrypted for the current Windows user."""

    def __init__(self, target: str = CREDENTIAL_TARGET) -> None:
        self.target = target

    @property
    def available(self) -> bool:
        return sys.platform == "win32"

    def load(self) -> str | None:
        api = self._api()
        credential = _PCREDENTIALW()
        if not api.CredReadW(self.target, _CRED_TYPE_GENERIC, 0, ctypes.byref(credential)):
            error = ctypes.get_last_error()
            if error == _ERROR_NOT_FOUND:
                return None
            raise CredentialStoreError(f"Windows could not read the saved API key ({error}).")
        try:
            size = credential.contents.CredentialBlobSize
            data = ctypes.string_at(credential.contents.CredentialBlob, size)
            return data.decode("utf-16-le")
        finally:
            api.CredFree(credential)

    def save(self, secret: str) -> None:
        if not self.available:
            raise CredentialStoreError("Saved API keys require Windows Credential Manager.")
        if not secret:
            raise ValueError("The API key cannot be empty.")
        data = secret.encode("utf-16-le")
        if len(data) > 2560:
            raise ValueError("The API key is too long for Windows Credential Manager.")
        blob = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        credential = _CREDENTIALW(
            Flags=0,
            Type=_CRED_TYPE_GENERIC,
            TargetName=self.target,
            Comment="Saved by Effects Studio for LIFX",
            CredentialBlobSize=len(data),
            CredentialBlob=ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=_CRED_PERSIST_LOCAL_MACHINE,
            AttributeCount=0,
            Attributes=None,
            TargetAlias=None,
            UserName="OpenAI API key",
        )
        if not self._api().CredWriteW(ctypes.byref(credential), 0):
            error = ctypes.get_last_error()
            raise CredentialStoreError(f"Windows could not save the API key ({error}).")

    def delete(self) -> None:
        if not self.available:
            raise CredentialStoreError("Saved API keys require Windows Credential Manager.")
        if self._api().CredDeleteW(self.target, _CRED_TYPE_GENERIC, 0):
            return
        error = ctypes.get_last_error()
        if error != _ERROR_NOT_FOUND:
            raise CredentialStoreError(f"Windows could not forget the API key ({error}).")

    def _api(self):
        if not self.available:
            raise CredentialStoreError("Saved API keys require Windows Credential Manager.")
        api = ctypes.WinDLL("advapi32", use_last_error=True)
        api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(_PCREDENTIALW),
        ]
        api.CredReadW.restype = wintypes.BOOL
        api.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        api.CredWriteW.restype = wintypes.BOOL
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        api.CredDeleteW.restype = wintypes.BOOL
        api.CredFree.argtypes = [ctypes.c_void_p]
        api.CredFree.restype = None
        return api

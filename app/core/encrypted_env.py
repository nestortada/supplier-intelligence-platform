import base64
import ctypes
import os
import sys
from ctypes import wintypes
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values

from app.core.desktop_paths import desktop_data_file, is_desktop_mode


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def encrypted_env_file() -> Path:
    return desktop_data_file(".env.enc")


def _unprotect_windows_dpapi(encrypted: bytes) -> bytes:
    data_in = DATA_BLOB(len(encrypted), ctypes.cast(ctypes.create_string_buffer(encrypted), ctypes.POINTER(ctypes.c_byte)))
    data_out = DATA_BLOB()

    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(data_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(data_out),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(data_out.pbData, data_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(data_out.pbData)


def protect_windows_dpapi(plain: bytes) -> bytes:
    data_in = DATA_BLOB(len(plain), ctypes.cast(ctypes.create_string_buffer(plain), ctypes.POINTER(ctypes.c_byte)))
    data_out = DATA_BLOB()

    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(data_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(data_out),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(data_out.pbData, data_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(data_out.pbData)


def load_encrypted_desktop_env() -> None:
    if not is_desktop_mode() or sys.platform != "win32":
        return

    path = encrypted_env_file()
    if not path.exists():
        return

    encrypted = base64.b64decode(path.read_text(encoding="utf-8"))
    decrypted_text = _unprotect_windows_dpapi(encrypted).decode("utf-8")

    for key, value in dotenv_values(stream=StringIO(decrypted_text)).items():
        if value is not None and key not in os.environ:
            os.environ[key] = value

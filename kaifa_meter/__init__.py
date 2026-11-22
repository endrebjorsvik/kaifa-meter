"""Kaifa meter reader and decoder package."""

from importlib import metadata

from kaifa_meter import db_writer, decoder, reader
from kaifa_meter.decoder import decode_frame
from kaifa_meter.reader import read_file, read_serial

try:
    __version__ = metadata.version("kaifa_meter")
except metadata.PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "__version__",
    "db_writer",
    "decode_frame",
    "decoder",
    "read_file",
    "read_serial",
    "reader",
]

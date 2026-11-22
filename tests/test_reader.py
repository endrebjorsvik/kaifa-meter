import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kaifa_meter import decoder, reader

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_FILE = DATA_DIR / "dump-2018-11-18T20:27:54.823083.dat"


def test_get_frame_valid():
    raw_bytes = SAMPLE_FILE.read_bytes()
    stream = io.BytesIO(raw_bytes)
    frame = reader.get_frame(stream)
    assert frame == raw_bytes


def test_get_frame_with_noise_prefix():
    raw_bytes = SAMPLE_FILE.read_bytes()
    noisy_stream = io.BytesIO(b"\x00\xff\x12\x7e\x00\x00" + raw_bytes)
    frame = reader.get_frame(noisy_stream)
    assert frame == raw_bytes


def test_get_frame_eof_empty():
    stream = io.BytesIO(b"")
    with pytest.raises(EOFError, match="Unexpected end of stream"):
        reader.get_frame(stream)


def test_get_frame_eof_truncated():
    raw_bytes = SAMPLE_FILE.read_bytes()[:10]
    stream = io.BytesIO(raw_bytes)
    with pytest.raises(EOFError):
        reader.get_frame(stream)


def test_read_serial():
    raw_bytes = SAMPLE_FILE.read_bytes()
    mock_serial = MagicMock()
    # Return one valid frame stream, then raise KeyboardInterrupt to terminate loop
    stream = io.BytesIO(raw_bytes)
    mock_serial.read.side_effect = lambda size=1: (
        stream.read(size)
        if stream.tell() < len(raw_bytes)
        else (_ for _ in ()).throw(KeyboardInterrupt)
    )

    received_frames: list[decoder.DecodedFrame] = []

    with patch("kaifa_meter.reader.Serial") as mock_serial_cls:
        mock_serial_cls.return_value.__enter__.return_value = mock_serial

        with pytest.raises(KeyboardInterrupt):
            reader.read_serial("/dev/test", callback=received_frames.append)

    assert len(received_frames) == 1
    assert received_frames[0].items_count == 1

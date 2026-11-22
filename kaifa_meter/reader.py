import io
import logging
import pathlib
from collections import deque
from collections.abc import Callable

from serial import EIGHTBITS, PARITY_EVEN, STOPBITS_ONE, Serial

from kaifa_meter import decoder

logger = logging.getLogger(__name__)

FRAME_TAG = b"\x7e"
# 16-bit frame format field = "0101SLLL_LLLLLLLL"
FRAME_FORMAT_MASK = b"\xa0"
FRAME_LENGTH_MASK = 0b111

type FrameCallback = Callable[[decoder.DecodedFrame], None]


def get_frame(stream: io.RawIOBase | io.BufferedIOBase | io.IOBase) -> bytes:
    """Extract a single HDLC frame from an input stream."""
    fifo: deque[bytes] = deque(2 * [b"\x00"], maxlen=2)
    while True:
        byte = stream.read(1)
        if not byte:
            raise EOFError("Unexpected end of stream while looking for frame start")
        fifo.append(byte)
        if (
            fifo[0] == FRAME_TAG
            and (fifo[1][0] & FRAME_FORMAT_MASK[0]) == FRAME_FORMAT_MASK[0]
        ):
            logger.debug("Found start of frame: %s", list(fifo))
            break

    # Read second byte of frame info to extract frame length
    byte2_raw = stream.read(1)
    if not byte2_raw:
        raise EOFError("Unexpected end of stream while reading frame length")

    byte1, byte2 = fifo[1][0], byte2_raw[0]
    frame_length = ((byte1 & FRAME_LENGTH_MASK) << 8) | byte2
    logger.debug("Frame length: %d", frame_length)

    # Read remaining frame data:
    # 2 format bytes already read, plus 1 byte for trailing frame tag (0x7e).
    remaining_bytes = frame_length - 1
    frame_remaining = stream.read(remaining_bytes)
    if len(frame_remaining) < remaining_bytes:
        raise EOFError("Stream ended before complete frame could be read")

    return FRAME_TAG + bytes([byte1, byte2]) + frame_remaining


def read_serial(
    device_path: pathlib.Path | str,
    callback: FrameCallback | None = None,
) -> None:
    """Continuously read frames from a serial connection and dispatch them."""
    with Serial(
        str(device_path),
        2400,
        bytesize=EIGHTBITS,
        parity=PARITY_EVEN,
        stopbits=STOPBITS_ONE,
    ) as ser:
        while True:
            try:
                frame = get_frame(ser)
            except Exception as e:  # noqa: BLE001
                logger.error("Unexpected error while reading frame: %s", e)
                continue

            try:
                msg = decoder.decode_frame(frame)
            except Exception as e:  # noqa: BLE001
                logger.error("Could not decode frame %s: %s", frame.hex(), e)
                continue

            if callback is None:
                print(msg.data.pwr_act_pos)
            else:
                callback(msg)


def read_file(filename: pathlib.Path) -> decoder.DecodedFrame:
    """Read and decode a single frame from a file."""
    with filename.open("rb") as fp:
        return decoder.decode_frame(get_frame(fp))


def read_one_frame(device_path: str | pathlib.Path) -> bytes:
    with Serial(
        str(device_path),
        2400,
        bytesize=EIGHTBITS,
        parity=PARITY_EVEN,
        stopbits=STOPBITS_ONE,
    ) as ser:
        return get_frame(ser)


if __name__ == "__main__":
    read_serial(pathlib.Path("/dev/ttyUSB0"), callback=None)

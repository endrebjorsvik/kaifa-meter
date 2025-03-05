import io
import logging
from typing import Callable

from serial import Serial, EIGHTBITS, PARITY_EVEN, STOPBITS_ONE

from kaifa_meter import decoder

FRAME_TAG = b"\x7e"
# 16 bit frame format field = "0101SLLL_LLLLLLLL"
FRAME_FORMAT_MASK = b"\xa0"
FRAME_LENGTH_MASK = 0b111


def get_frame(stream: io.IOBase) -> bytes:
    # Find frame start
    fifo = 2 * [b"\x00"]
    while True:
        fifo.pop(0)
        fifo.append(stream.read(1))
        if fifo[0] == FRAME_TAG:
            logging.debug(f"Found candidate for frame start: {fifo}")
            # Only consider 4 MSbit of the frame format
            frame_format = bytes([fifo[1][0] & FRAME_FORMAT_MASK[0]])
            if frame_format == FRAME_FORMAT_MASK:
                logging.debug(f"Found start of frame: {fifo}")
                break

    # Read one more byte to find frame length
    fifo.append(stream.read(1))
    frame_length = ((fifo[1][0] & FRAME_LENGTH_MASK) << 8) + fifo[2][0]
    logging.debug(f"Frame length: {frame_length}")
    # Read remaining frame data.
    # We have already read two frame bytes, and we want to add the
    # trailing frame tag (frame length does not include frame tags).
    frame_remaining = stream.read(frame_length - 2 + 1)
    frame = b"".join(fifo) + frame_remaining
    return frame


def read_serial(
    device_path: str, callback: Callable[[decoder.DecodedFrame], None] | None
):
    with Serial(
        device_path, 2400, bytesize=EIGHTBITS, parity=PARITY_EVEN, stopbits=STOPBITS_ONE
    ) as ser:
        while True:
            try:
                frame = get_frame(ser)
            except Exception as e:
                logging.error(f"Unexpected error while reading frame. Exception: {e}")
                continue

            try:
                msg = decoder.decode_frame(frame)
            except Exception as e:
                logging.error(f"Could not decode frame: {frame}. Exception: {e}")
                continue

            if callback is None:
                print(msg.data.pwr_act_pos)
            else:
                callback(msg)


def read_file(filename: str):
    with open(filename, "rb") as fp:
        return decoder.decode_frame(get_frame(fp))


if __name__ == "__main__":
    read_serial("/dev/ttyUSB0", callback=None)

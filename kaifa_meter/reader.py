
import datetime
import logging
from serial import Serial, EIGHTBITS, PARITY_EVEN, STOPBITS_ONE

from kaifa_meter.decoder import decode_frame

FRAME_TAG = b'\x7e'
# 16 bit frame format field = "0101SLLL_LLLLLLLL"
FRAME_FORMAT_MASK = b'\xa0'
FRAME_LENGTH_MASK = 0b111


def get_frame(stream):
    # Find frame start
    fifo = 2*['\x00']
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
    frame = b''.join(fifo) + frame_remaining
    return frame


def read_serial(device_path, callback=None):
    with Serial(device_path, 2400, bytesize=EIGHTBITS, parity=PARITY_EVEN,
                stopbits=STOPBITS_ONE) as ser:
        while True:
            frame = get_frame(ser)
            msg = decode_frame(frame)
            if callback is None:
                print(msg.data.pwr_act_pos.val)
            else:
                callback(msg)


def read_file(filename):
    with open("data/dump-2018-11-18T20:27:38.865264.dat", 'rb') as fp:
        print(decode_frame(get_frame(fp)))


if __name__ == '__main__':
    read_serial('/dev/ttyUSB0')

from datetime import datetime
from pathlib import Path

import construct
import pytest

from kaifa_meter import decoder

DATA_DIR = Path(__file__).parent.parent / "data"


def test_decode_all_sample_files():
    sample_files = list(DATA_DIR.glob("dump-*.dat"))
    assert len(sample_files) > 0

    for file_path in sample_files:
        frame = file_path.read_bytes()
        msg = decoder.decode_frame(frame)
        assert msg is not None
        assert isinstance(msg.items_count, int)
        assert isinstance(msg.meter_ts, datetime)
        assert msg.header.dest_addr.raw == b"\x01"
        assert msg.header.dest_addr.logical == 0
        assert msg.header.dest_addr.physical is None
        assert msg.header.src_addr.raw == b"\x02\x01"
        assert msg.header.src_addr.logical == 1
        assert msg.header.src_addr.physical == 0


def test_decode_single_item_frame():
    file_path = DATA_DIR / "dump-2018-11-18T20:27:54.823083.dat"
    msg = decoder.decode_frame(file_path.read_bytes())

    assert msg.items_count == 1
    assert msg.meter_ts == datetime(2018, 11, 18, 20, 27, 52)
    assert msg.data.pwr_act_pos == 601
    assert msg.data.get("obis_version") is None
    assert msg.data_iv.get("IL1") is None
    assert msg.data_energy.get("act_pos") is None


def test_decode_nine_item_frame():
    file_path = DATA_DIR / "dump-2018-11-18T20:27:43.126293.dat"
    msg = decoder.decode_frame(file_path.read_bytes())

    assert msg.items_count == 9
    assert msg.meter_ts == datetime(2018, 11, 18, 20, 27, 40)
    assert msg.data.obis_version == "KFM_001"
    assert msg.data.meter_id == "6970631402394972"
    assert msg.data.meter_type == "MA105H2E"
    assert msg.data.pwr_act_pos == 602
    assert msg.data.pwr_act_neg == 0
    assert msg.data.pwr_react_pos == 0
    assert msg.data.pwr_react_neg == 136

    assert msg.data_iv.IL1 == 2.778
    assert msg.data_iv.ULN1 == 240.6


def test_decode_invalid_frame():
    with pytest.raises(construct.ConstructError):
        decoder.decode_frame(b"invalid_data_frame")


def test_hdlc_address_parsing():
    addr1 = decoder.HdlcAddress.parse(b"\x01")
    assert addr1.raw == b"\x01"
    assert addr1.logical == 0
    assert addr1.physical is None

    addr2 = decoder.HdlcAddress.parse(b"\x02\x01")
    assert addr2.raw == b"\x02\x01"
    assert addr2.logical == 1
    assert addr2.physical == 0

    addr4 = decoder.HdlcAddress.parse(b"\x02\x04\x06\x01")
    assert addr4.raw == b"\x02\x04\x06\x01"
    assert addr4.logical == ((1 << 7) | 2)
    assert addr4.physical == ((3 << 7) | 0)

    # Unterminated address (missing LSB=1 on final byte)
    with pytest.raises(construct.ValidationError):
        decoder.HdlcAddress.parse(b"\x02\x04\x06\x08")


def test_hcs_checksum_verification():
    file_path = DATA_DIR / "dump-2018-11-18T20:27:54.823083.dat"
    raw_frame = bytearray(file_path.read_bytes())

    # Tamper with header byte (frame_info or address)
    raw_frame[2] ^= 0x01
    with pytest.raises(construct.ChecksumError, match="HCS mismatch"):
        decoder.decode_frame(bytes(raw_frame))


def test_fcs_checksum_verification():
    file_path = DATA_DIR / "dump-2018-11-18T20:27:54.823083.dat"
    raw_frame = bytearray(file_path.read_bytes())

    # Tamper with payload byte (meter timestamp / data)
    raw_frame[15] ^= 0x01
    with pytest.raises(construct.ChecksumError, match="FCS mismatch"):
        decoder.decode_frame(bytes(raw_frame))


def test_item_int32_signed_current():
    # Tag 0x06 with positive value: 2778 mA
    parsed_pos = decoder.ItemInt32.parse(b"\x06\x00\x00\x0a\xda")
    assert parsed_pos.val == 2778

    # Tag 0x06 with negative value: -500 mA (0xfffffe0c)
    parsed_neg = decoder.ItemInt32.parse(b"\x06\xff\xff\xfe\x0c")
    assert parsed_neg.val == -500

    # Tag 0x05 (standard DLMS signed double-long)
    parsed_tag5 = decoder.ItemInt32.parse(b"\x05\xff\xff\xfe\x0c")
    assert parsed_tag5.val == -500

    # Invalid tag
    with pytest.raises(construct.ValidationError):
        decoder.ItemInt32.parse(b"\x07\x00\x00\x00\x01")

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

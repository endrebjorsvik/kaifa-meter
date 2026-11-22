import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

import construct as c

if TYPE_CHECKING:
    ChecksumBase = c.Construct[bytes, bytes]
    AddressContainer = c.Container[bytes | int | None]
    AdapterBase = c.Adapter[list[int], list[int], AddressContainer, int]
else:
    ChecksumBase = c.Construct
    AdapterBase = c.Adapter
    AddressContainer = c.Container


logger = logging.getLogger(__name__)


def _generate_crc_table() -> tuple[int, ...]:
    table: list[int] = []
    for i in range(256):
        curr = i
        for _ in range(8):
            if curr & 1:
                curr = (curr >> 1) ^ 0x8408
            else:
                curr >>= 1
        table.append(curr)
    return tuple(table)


CRC16_TABLE = _generate_crc_table()


def crc16_hdlc(data: bytes) -> bytes:
    """Compute 16-bit HDLC Frame Check Sequence (CRC-16-CCITT) in little-endian byte order."""
    crc = 0xFFFF
    for byte in data:
        crc = (crc >> 8) ^ CRC16_TABLE[(crc ^ byte) & 0xFF]
    return (crc ^ 0xFFFF).to_bytes(2, "little")


class FrameChecksum(ChecksumBase):
    """Construct field verifying HDLC CRC-16 checksum over a stream byte slice."""

    def __init__(
        self,
        start_offset_func: Callable[[c.Container[Any]], int],
        name: str,
    ) -> None:
        super().__init__()
        self.start_offset_func = start_offset_func
        self.name = name
        self.flagbuildnone = True

    @override
    def _parse(self, stream: Any, context: c.Container[Any], path: str) -> bytes:
        current_offset = c.stream_tell(stream, path)
        start_offset = self.start_offset_func(context)
        c.stream_seek(stream, start_offset, 0, path)
        data = c.stream_read(stream, current_offset - start_offset, path)
        c.stream_seek(stream, current_offset, 0, path)
        expected_crc = crc16_hdlc(data)
        read_crc = c.stream_read(stream, 2, path)
        if read_crc != expected_crc:
            raise c.ChecksumError(
                f"{self.name} mismatch: read {read_crc.hex()}, expected {expected_crc.hex()}",
                path=path,
            )
        return read_crc

    @override
    def _build(  # type: ignore
        self, obj: Any, stream: Any, context: c.Container[Any], path: str
    ) -> bytes:
        raise NotImplementedError()
        if obj is not None and isinstance(obj, (bytes, bytearray)) and len(obj) == 2:
            crc = bytes(obj)
        else:
            current_offset = c.stream_tell(stream, path)
            start_offset = self.start_offset_func(context)
            c.stream_seek(stream, start_offset, 0, path)
            data = c.stream_read(stream, current_offset - start_offset, path)
            c.stream_seek(stream, current_offset, 0, path)
            crc = crc16_hdlc(data)
        c.stream_write(stream, crc, 2, path)
        return crc

    def _sizeof(self, context: c.Container[Any], path: str) -> int:
        return 2


class HdlcAddressAdapter(AdapterBase):
    """Adapter for HDLC variable-length address field (1, 2, or 4 octets).

    In HDLC (ISO 13239 / IEC 62056-46), the least significant bit (bit 0) of each
    octet indicates whether another octet follows (0 = extension, 1 = final octet).
    """

    @override
    def _decode(
        self, obj: list[int], context: c.Container[Any], path: str
    ) -> AddressContainer:
        if not (1 <= len(obj) <= 4):
            raise c.ValidationError(
                f"HDLC address length must be 1, 2, or 4 bytes, got {len(obj)}",
                path=path,
            )
        if (obj[-1] & 1) == 0:
            raise c.ValidationError(
                "HDLC address missing extension end bit",
                path=path,
            )

        raw = bytes(obj)
        length = len(obj)
        if length == 1:
            logical = obj[0] >> 1
            return c.Container(raw=raw, logical=logical, physical=None)
        if length == 2:
            logical = obj[0] >> 1
            physical = obj[1] >> 1
            return c.Container(raw=raw, logical=logical, physical=physical)
        if length == 4:
            logical = ((obj[0] >> 1) << 7) | (obj[1] >> 1)
            physical = ((obj[2] >> 1) << 7) | (obj[3] >> 1)
            return c.Container(raw=raw, logical=logical, physical=physical)

        raise c.ValidationError(f"Invalid HDLC address length: {length}", path=path)

    @override
    def _encode(self, obj: Any, context: c.Container[Any], path: str) -> list[int]:
        raise NotImplementedError()
        if isinstance(obj, (bytes, bytearray)):
            return list(obj)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, (c.Container, dict)):
            if "raw" in obj and obj["raw"] is not None:
                return list(obj["raw"])
            if obj.get("physical") is None:
                return [(int(obj["logical"]) << 1) | 1]
            return [(int(obj["logical"]) << 1) & 0xFE, (int(obj["physical"]) << 1) | 1]
        if isinstance(obj, int):
            return [(obj << 1) | 1]
        raise c.ValidationError(f"Cannot encode HDLC address: {obj!r}", path=path)


def _address_collector(obj: int, elements: list[int], ctx: Any) -> bool:
    return (obj & 1 != 0) or len(elements) >= 4


HdlcAddress = HdlcAddressAdapter(
    c.RepeatUntil(
        predicate=_address_collector,
        subcon=c.Byte,
    )
)

FrameInfo = c.BitStruct(
    "frame_format" / c.Bit[4],
    "separator" / c.Bit,
    "frame_length" / c.BitsInteger(11),
)

Header = c.Struct(
    "start_tag" / c.Const(b"\x7e"),
    "_header_start" / c.Tell,
    "frame_info" / FrameInfo,
    "dest_addr" / HdlcAddress,
    "src_addr" / HdlcAddress,
    "control_field" / c.Byte,
    "hcs" / FrameChecksum(lambda ctx: ctx._header_start, name="HCS"),
)

Meta = c.Struct(
    "lsap_dest" / c.Byte,
    "lsap_src" / c.Byte,
    "llc_quality" / c.Byte,
    c.Bytes(5),
)


def _get_footer_crc_start(ctx: c.Container[Any]) -> int:
    if "_" in ctx and "header" in ctx._ and "_header_start" in ctx._.header:
        return ctx._.header._header_start
    return 0


Footer = c.Struct(
    "fcs" / FrameChecksum(_get_footer_crc_start, name="FCS"),
    "end_tag" / c.Const(b"\x7e"),
)


# ########################
#  Data types
# ########################
Timestamp = c.Struct(
    "item_type" / c.Const(b"\x09"),
    "item_length" / c.Int8ub,
    "year" / c.Int16ub,
    "month" / c.Int8ub,
    "day" / c.Int8ub,
    c.Byte,
    "hour" / c.Int8ub,
    "minute" / c.Int8ub,
    "second" / c.Int8ub,
    c.Bytes(4),
    "val"
    / c.Computed(
        lambda ctx: datetime(
            ctx.year, ctx.month, ctx.day, ctx.hour, ctx.minute, ctx.second
        )
    ),
)

ItemsCount = c.Struct(
    "item_type" / c.Const(b"\x02"),
    "val" / c.Int8ub,
)

Text = c.Struct(
    "item_type" / c.Const(b"\x09"),
    "item_length" / c.Int8ub,
    "val" / c.PaddedString(c.this.item_length, "utf8"),
)

ItemUint32 = c.Struct(
    "item_type" / c.Const(b"\x06"),
    "val" / c.Int32ub,
)

ItemInt32 = c.Struct(
    # DLMS/COSEM defines 0x05 as signed 32-bit (double-long) and 0x06 as unsigned
    # 32-bit (double-long-unsigned). Kaifa meters specify current as signed,
    # but use tag 0x06; we accept either 0x05 or 0x06.
    "item_type" / c.OneOf(c.Bytes(1), [b"\x05", b"\x06"]),
    "val" / c.Int32sb,
)


# #############################
#  High level data collections
# #############################
List1 = c.Struct(
    "pwr_act_pos_item" / ItemUint32,
    "pwr_act_pos" / c.Computed(c.this.pwr_act_pos_item.val) * "W",
)

List2Head = c.Struct(
    "obis_version_item" / Text,
    "meter_id_item" / Text,
    "meter_type_item" / Text,
    "pwr_act_pos_item" / ItemUint32,
    "pwr_act_neg_item" / ItemUint32,
    "pwr_react_pos_item" / ItemUint32,
    "pwr_react_neg_item" / ItemUint32,
    "obis_version" / c.Computed(c.this.obis_version_item.val),
    "meter_id" / c.Computed(c.this.meter_id_item.val),
    "meter_type" / c.Computed(c.this.meter_type_item.val),
    "pwr_act_pos" / c.Computed(c.this.pwr_act_pos_item.val) * "W",
    "pwr_act_neg" / c.Computed(c.this.pwr_act_neg_item.val) * "W",
    "pwr_react_pos" / c.Computed(c.this.pwr_react_pos_item.val) * "VAr",
    "pwr_react_neg" / c.Computed(c.this.pwr_react_neg_item.val) * "VAr",
)

List2SinglePhase = c.Struct(
    "IL1_item" / ItemInt32,
    "ULN1_item" / ItemUint32,
    "IL1" / c.Computed(c.this.IL1_item.val / 1000) * "A",
    "ULN1" / c.Computed(c.this.ULN1_item.val / 10) * "V",
)

List2ThreePhase = c.Struct(
    "IL1_item" / ItemInt32,
    "IL2_item" / ItemInt32,
    "IL3_item" / ItemInt32,
    "ULN1_item" / ItemUint32,
    "ULN2_item" / ItemUint32,
    "ULN3_item" / ItemUint32,
    "IL1" / c.Computed(c.this.IL1_item.val / 1000) * "A",
    "IL2" / c.Computed(c.this.IL2_item.val / 1000) * "A",
    "IL3" / c.Computed(c.this.IL3_item.val / 1000) * "A",
    "ULN1" / c.Computed(c.this.ULN1_item.val / 10) * "V",
    "ULN2" / c.Computed(c.this.ULN2_item.val / 10) * "V",
    "ULN3" / c.Computed(c.this.ULN3_item.val / 10) * "V",
)

List3Energy = c.Struct(
    "meter_ts_item" / Timestamp,
    "act_pos_item" / ItemUint32,
    "act_neg_item" / ItemUint32,
    "react_pos_item" / ItemUint32,
    "react_neg_item" / ItemUint32,
    "meter_ts" / c.Computed(c.this.meter_ts_item.val),
    "act_pos" / c.Computed(c.this.act_pos_item.val) * "Wh",
    "act_neg" / c.Computed(c.this.act_neg_item.val) * "Wh",
    "react_pos" / c.Computed(c.this.react_pos_item.val) * "VArh",
    "react_neg" / c.Computed(c.this.react_neg_item.val) * "VArh",
)

# #####################
#  Top level message
# #####################
Message = c.Struct(
    "header" / Header,
    "meta" / Meta,
    "meter_ts_item" / Timestamp,
    "meter_ts" / c.Computed(c.this.meter_ts_item.val),
    "items_count_item" / ItemsCount,
    "items_count" / c.Computed(c.this.items_count_item.val),
    "data"
    / c.Switch(
        c.this.items_count,
        {
            1: List1,
            9: List2Head,
            13: List2Head,
            14: List2Head,
            18: List2Head,
        },
    ),
    "data_iv"
    / c.Switch(
        c.this.items_count,
        {
            9: List2SinglePhase,
            13: List2ThreePhase,
            14: List2SinglePhase,
            18: List2ThreePhase,
        },
        default=c.Struct(),
    ),
    "data_energy"
    / c.Switch(
        c.this.items_count,
        {
            14: List3Energy,
            18: List3Energy,
        },
        default=c.Struct(),
    ),
    "footer" / Footer,
)

type DecodedFrame = c.Container[c.Struct]


def decode_frame(frame: bytes) -> DecodedFrame:
    """Decode raw bytes into a parsed Kaifa meter frame."""
    return Message.parse(frame)


if __name__ == "__main__":
    datapath = Path("./data")
    for file in sorted(datapath.glob("dump-*.dat")):
        frame = file.read_bytes()
        msg = decode_frame(frame)
        print(msg)
        print(f"{msg.meter_ts}: {msg.data.pwr_act_pos} W")
        print(f"Reactive: {msg.data.get('pwr_react_neg')} VAr")
        print(f"Current: {msg.data_iv.get('IL1')} A")
        print(f"Voltage: {msg.data_iv.get('ULN1')} V")
        print(f"Energy: {msg.data_energy.get('act_pos')} Wh")
        print()

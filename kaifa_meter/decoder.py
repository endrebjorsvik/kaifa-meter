import json
import pathlib
import construct as c
import datetime

FrameInfo = c.BitStruct(
    "frame_format" / c.Bit[4],
    "separator" / c.Bit,
    "frame_length" / c.BitsInteger(11),
)

Header = c.Struct(
    "start_tag" / c.Const(b'\x7e'),
    "frame_info" / FrameInfo,
    "dest_addr" / c.Int8ub,  # TODO: Proper parsing. Not static.
    "src_addr" / c.Struct(  # TODO: Proper parsing. Not static.
        c.Int8ub,
        c.Int8ub,
    ),
    "control_field" / c.Byte,
    "hcs" / c.Bytes(2),  # TODO: Verify checksum
)

Meta = c.Struct(
    "lsap_dest" / c.Byte,
    "lsap_src" / c.Byte,
    "llc_quality" / c.Byte,
    c.Bytes(5),
)

Footer = c.Struct(
    "fcs" / c.Bytes(2),  # TODO: Verify checksum
    "end_tag" / c.Const(b'\x7e'),
)


# ########################
#  Data types
# ########################
Timestamp = c.Struct(
    "item_type" / c.Const(b'\x09'),
    "item_length" / c.Int8ub,
    "year" / c.Int16ub,
    "month" / c.Int8ub,
    "day" / c.Int8ub,
    c.Byte,
    "hour" / c.Int8ub,
    "minute" / c.Int8ub,
    "second" / c.Int8ub,
    c.Bytes(4),
    "val" / c.Computed(lambda ctx: datetime.datetime(
        ctx.year, ctx.month, ctx.day,
        ctx.hour, ctx.minute, ctx.second
    )),
)

ItemsCount = c.Struct(
    "item_type" / c.Const(b'\x02'),
    "val" / c.Int8ub,
)

Text = c.Struct(
    "item_type" / c.Const(b'\x09'),
    "item_length" / c.Int8ub,
    "val" / c.PaddedString(c.this.item_length, 'utf8'),
)

ItemUint32 = c.Struct(
    "item_type" / c.Const(b'\x06'),
    "val" / c.Int32ub,
)

ItemInt32 = c.Struct(
    "item_type" / c.Const(b'\x06'),  # TODO: This looks odd, but Kaifa states that Current is signed.
    "val" / c.Int32sb,
)


# #############################
#  High level data collections
# #############################
List1 = c.Struct(
    "pwr_act_pos" / ItemUint32,
)

List2Top = c.Struct(
    "obis_version" / Text,
    "meter_id" / Text,
    "meter_type" / Text,
    "pwr_act_pos" / ItemUint32,
    "pwr_act_neg" / ItemUint32,
    "pwr_react_pos" / ItemUint32,
    "pwr_react_neg" / ItemUint32,
)

List2SinglePhase = c.Struct(
    c.Embedded(List2Top),
    "IL1_raw" / ItemInt32,
    "IL1" / c.Computed(c.this.IL1_raw.val / 1000),
    "ULN1_raw" / ItemUint32,
    "ULN1" / c.Computed(c.this.ULN1_raw.val / 10),
)

List2ThreePhase = c.Struct(
    c.Embedded(List2Top),
    "IL1_raw" / ItemInt32,
    "IL1" / c.Computed(c.this.IL1_raw.val / 1000),
    "IL2_raw" / ItemInt32,
    "IL2" / c.Computed(c.this.IL2_raw.val / 1000),
    "IL3_raw" / ItemInt32,
    "IL3" / c.Computed(c.this.IL3_raw.val / 1000),
    "ULN1_raw" / ItemUint32,
    "ULN1" / c.Computed(c.this.ULN1_raw.val / 10),
    "ULN2_raw" / ItemUint32,
    "ULN2" / c.Computed(c.this.ULN2_raw.val / 10),
    "ULN3_raw" / ItemUint32,
    "ULN3" / c.Computed(c.this.ULN3_raw.val / 10),
)

List3Items = c.Struct(
    "meter_ts" / Timestamp,
    "energy_act_pos_raw" / ItemUint32,
    "energy_act_pos" / c.Computed(c.this.energy_act_pos_raw.val / 1000),
    "energy_act_neg_raw" / ItemUint32,
    "energy_act_neg" / c.Computed(c.this.energy_act_neg_raw.val / 1000),
    "energy_react_pos_raw" / ItemUint32,
    "energy_react_pos" / c.Computed(c.this.energy_react_pos_raw.val / 1000),
    "energy_react_neg_raw" / ItemUint32,
    "energy_react_neg" / c.Computed(c.this.energy_react_neg_raw.val / 1000),
)

List3SinglePhase = c.Struct(
    c.Embedded(List2SinglePhase),
    c.Embedded(List3Items),
)

List3ThreePhase = c.Struct(
    c.Embedded(List2ThreePhase),
    c.Embedded(List3Items),
)

# #####################
#  Top level message
# #####################
message = c.Struct(
    "header" / Header,
    "meta" / Meta,
    "meter_ts" / Timestamp,
    "items_count" / ItemsCount,
    "data" / c.Switch(c.this.items_count.val, {
        1: List1,
        9: List2SinglePhase,
        13: List2ThreePhase,
        14: List3SinglePhase,
        18: List3ThreePhase,
    }),
    "footer" / Footer,
)


def decode_frame(frame):
    msg = message.parse(frame)
    return msg


def get_field(struct, field):
    """Attempt to always read the 'val' attribute
       of the desired field.
    """
    v = struct.get(field)
    try:
        return v.val
    except AttributeError:
        return v


if __name__ == '__main__':
    datapath = pathlib.Path('./data')
    files = list(datapath.glob('dump-*.dat'))
    for f in files:
        with open(f, 'rb') as fp:
            frame = fp.read()

        msg = decode_frame(frame)
        print(f"{msg['timestamp']['val']}: {get_field(msg.data, 'pwr_act_pos')} W")
        try:
            print(f"Current: {msg.data.IL1} A")
            print(f"Voltage: {msg.data.ULN1} V")
            print(f"Reactive: {msg.data.pwr_react_neg.val} VAr")
        except AttributeError:
            pass

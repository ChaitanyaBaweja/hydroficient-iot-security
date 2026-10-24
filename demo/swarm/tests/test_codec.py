import json

from swarm import codec, messages


def test_publish_worked_example():
    assert codec.encode_publish("a/b", b"hi") == bytes.fromhex("30 08 00 03 61 2F 62 00 68 69")


def test_publish_qos1_has_packet_id():
    got = codec.encode_publish("a/b", b"hi", qos=1, packet_id=1)
    assert got == bytes.fromhex("32 0A 00 03 61 2F 62 00 01 00 68 69")


def test_remaining_length_varint():
    pkt = codec.encode_publish("x", b"y" * 200)
    rem, nxt = codec._decode_varint(pkt, 1)
    assert nxt - 1 == 2           # two-byte varint
    assert rem == 2 + 1 + 1 + 200  # topic(2+1) + proplen(1) + payload(200)


def test_describe_covers_every_byte():
    msg = messages.make_message(
        "HYDROLOGIC-Device-001", messages.iso(0), 1,
        {"pressure_upstream": 72.0, "pressure_downstream": 60.0,
         "flow_rate": 150.0, "gate_a_position": 45.0, "gate_b_position": 45.0},
    )
    payload = json.dumps(msg, separators=(",", ":")).encode()
    pkt = codec.encode_publish("hydroficient/grand-marina/device-001/sensors", payload)
    fields = codec.describe_publish(pkt)
    # Fields tile the packet exactly.
    pos = 0
    for f in fields:
        assert f["offset"] == pos, f
        pos += f["length"]
    assert pos == len(pkt)
    # Payload field round-trips to the original message.
    assert json.loads(fields[-1]["value"]) == msg


def test_tls_record_len():
    assert codec.tls13_record_len(100) == 122


def test_reason_codes():
    assert codec.REASON[0x00] == "Success"
    assert codec.REASON[0x87] == "Not authorized"

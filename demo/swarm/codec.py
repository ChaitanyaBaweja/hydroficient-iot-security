"""Encode and describe MQTT 5 PUBLISH packets for the on-screen decode panel.

The point of the panel is to show externs that the telemetry they already send
in the curriculum is a real wire format with named fields, and to contrast the
plaintext payload with what an on-path observer sees under TLS (lengths and
timing only). Built straight from the OASIS MQTT 5 spec.
"""

REASON = {0x00: "Success", 0x87: "Not authorized"}


def _encode_varint(x):
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _decode_varint(data, i):
    """Return (value, next_index) for the varint starting at data[i]."""
    mult, value, length = 1, 0, 0
    while True:
        b = data[i + length]
        value += (b & 0x7F) * mult
        length += 1
        if not (b & 0x80):
            break
        mult *= 128
    return value, i + length


def encode_publish(topic, payload, qos=0, packet_id=None):
    """Encode a PUBLISH packet (MQTT 5, empty properties)."""
    topic_b = topic.encode("utf-8")
    var = bytearray()
    var += len(topic_b).to_bytes(2, "big") + topic_b
    if qos > 0:
        if packet_id is None:
            raise ValueError("packet_id required for QoS > 0")
        var += packet_id.to_bytes(2, "big")
    var += _encode_varint(0)  # property length 0
    remaining = bytes(var) + payload
    fixed = 0x30 | (qos << 1)
    return bytes([fixed]) + _encode_varint(len(remaining)) + remaining


def describe_publish(packet):
    """Break a PUBLISH packet into labelled fields in byte order.

    Each field is {offset, length, label, hex, value}; together they tile the
    whole packet with no gaps, so the panel can line up each byte with meaning.
    """
    fields = []

    def add(off, length, label, value):
        chunk = packet[off:off + length]
        fields.append({
            "offset": off, "length": length, "label": label,
            "hex": " ".join(f"{b:02X}" for b in chunk), "value": value,
        })

    fixed = packet[0]
    qos = (fixed >> 1) & 0x03
    add(0, 1, "Fixed header (PUBLISH, QoS %d)" % qos, f"type=3 qos={qos}")

    rem, i = _decode_varint(packet, 1)
    add(1, i - 1, "Remaining length", str(rem))

    tlen = int.from_bytes(packet[i:i + 2], "big")
    add(i, 2, "Topic length", str(tlen))
    i += 2
    add(i, tlen, "Topic", packet[i:i + tlen].decode("utf-8", "replace"))
    i += tlen

    if qos > 0:
        add(i, 2, "Packet identifier", str(int.from_bytes(packet[i:i + 2], "big")))
        i += 2

    plen, j = _decode_varint(packet, i)
    add(i, j - i, "Property length", str(plen))
    i = j + plen

    payload = packet[i:]
    add(i, len(payload), "Payload", payload.decode("utf-8", "replace"))
    return fields


def tls13_record_len(plaintext_len):
    """Bytes on the wire for a TLS 1.3 application-data record carrying
    `plaintext_len` bytes: 5-byte header + plaintext + content-type byte + 16-byte
    AEAD tag. This is all an on-path observer can measure."""
    return 5 + plaintext_len + 1 + 16

import bz2
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ANIM_GROUP = ROOT.parent / "deob" / "kickabout-asset-dump" / "16_0.bin"
OUT_DIR = ROOT / "research" / "animation-decoded"


def u8(data, pos):
    return data[pos], pos + 1


def u16(data, pos):
    return int.from_bytes(data[pos:pos + 2], "big"), pos + 2


def u24(data, pos):
    return int.from_bytes(data[pos:pos + 3], "big"), pos + 3


def i32(data, pos):
    return int.from_bytes(data[pos:pos + 4], "big", signed=True), pos + 4


def decode_container(data):
    kind = data[0]
    packed_len = int.from_bytes(data[1:5], "big")
    if kind == 0:
        return data[5:5 + packed_len]
    unpacked_len = int.from_bytes(data[5:9], "big")
    payload = data[9:9 + packed_len]
    if kind == 1:
        # The cache stores raw bzip2 blocks. Any valid block-size byte works for these blocks.
        decoded = bz2.decompress(b"BZh1" + payload)
    elif kind == 2:
        import gzip
        decoded = gzip.decompress(payload)
    else:
        raise ValueError(f"unknown container kind {kind}")
    if len(decoded) != unpacked_len:
        raise ValueError(f"decoded {len(decoded)} bytes, expected {unpacked_len}")
    return decoded


def infer_file_count(group):
    chunks = group[-1]
    matches = []
    for file_count in range(1, 5000):
        table_pos = len(group) - 1 - file_count * chunks * 4
        if table_pos < 0:
            break
        pos = table_pos
        sizes = [0] * file_count
        for _ in range(chunks):
            acc = 0
            for i in range(file_count):
                delta, pos = i32(group, pos)
                acc += delta
                sizes[i] += acc
        if sum(sizes) == table_pos and all(size >= 0 for size in sizes):
            matches.append((file_count, table_pos, sizes))
    if len(matches) != 1:
        raise ValueError(f"ambiguous file count matches: {matches[:5]}")
    return matches[0]


def split_group(group):
    chunks = group[-1]
    file_count, table_pos, _ = infer_file_count(group)
    chunk_table = table_pos
    sizes = [0] * file_count
    pos = chunk_table
    for _ in range(chunks):
        acc = 0
        for i in range(file_count):
            delta, pos = i32(group, pos)
            acc += delta
            sizes[i] += acc

    files = [bytearray() for _ in range(file_count)]
    data_pos = 0
    pos = chunk_table
    for _ in range(chunks):
        acc = 0
        for i in range(file_count):
            delta, pos = i32(group, pos)
            acc += delta
            files[i].extend(group[data_pos:data_pos + acc])
            data_pos += acc
    return [bytes(file) for file in files]


def parse_nm(data):
    pos = 0
    result = {
        "frames": [],
        "durations": [],
        "loop_start": -1,
        "loop_count": 0,
        "priority": None,
        "replay_mode": True,
        "extra_tables": 0,
        "opcodes": [],
    }
    while pos < len(data):
        opcode, pos = u8(data, pos)
        result["opcodes"].append(opcode)
        if opcode == 0:
            break
        if opcode == 1:
            count, pos = u16(data, pos)
            durations = []
            frames = []
            for _ in range(count):
                value, pos = u16(data, pos)
                durations.append(value)
            for _ in range(count):
                value, pos = u16(data, pos)
                frames.append(value)
            for i in range(count):
                value, pos = u16(data, pos)
                frames[i] += value << 16
            result["durations"] = durations
            result["frames"] = frames
        elif opcode == 2:
            result["loop_start"], pos = u8(data, pos)
        elif opcode == 3:
            count, pos = u8(data, pos)
            result["mask"] = list(data[pos:pos + count]) + [9999999]
            pos += count
        elif opcode in (5, 6, 7, 9, 10, 11):
            _, pos = u8(data, pos)
        elif opcode == 8:
            result["loop_count"], pos = u8(data, pos)
            result["replay_mode"] = False
        elif opcode == 12:
            count, pos = u8(data, pos)
            pos += count * 4
            result["extra_tables"] += 1
        elif opcode == 13:
            count, pos = u16(data, pos)
            for _ in range(count):
                entry_count, pos = u8(data, pos)
                if entry_count > 0:
                    _, pos = u24(data, pos)
                    pos += (entry_count - 1) * 2
            result["extra_tables"] += 1
        elif opcode in (14, 15, 16, 18):
            pass
        else:
            raise ValueError(f"unsupported opcode {opcode} at {pos - 1}")
    result["parsed_bytes"] = pos
    return result


def read_smart(data, pos):
    if data[pos] < 128:
        return data[pos] - 64, pos + 1
    return int.from_bytes(data[pos:pos + 2], "big") - 49152, pos + 2


def parse_skeleton(data, skeleton_id):
    pos = 0
    count, pos = u8(data, pos)
    transform_types = list(data[pos:pos + count])
    pos += count
    flags = list(data[pos:pos + count])
    pos += count
    masks = []
    for _ in range(count):
        value, pos = u16(data, pos)
        masks.append(value)
    groups = []
    lengths = []
    for _ in range(count):
        value, pos = u8(data, pos)
        lengths.append(value)
    for length in lengths:
        groups.append(list(data[pos:pos + length]))
        pos += length
    return {
        "id": skeleton_id,
        "count": count,
        "transform_types": transform_types,
        "flags": flags,
        "masks": masks,
        "groups": groups,
        "parsed_bytes": pos,
    }


def parse_frame(data, skeletons):
    flags_pos = 0
    skeleton_id = int.from_bytes(data[1:3], "big")
    skeleton = skeletons[skeleton_id]
    transform_count = data[3]
    flags_pos = 4
    values_pos = flags_pos + transform_count
    entries = []
    last_zero = -1
    last_inserted_zero = -1
    for transform_index in range(transform_count):
        transform_type = skeleton["transform_types"][transform_index]
        if transform_type == 0:
            last_zero = transform_index
        present = data[flags_pos]
        flags_pos += 1
        if present <= 0:
            continue
        parent = -1
        if transform_type == 0:
            last_inserted_zero = transform_index
        elif transform_type in (1, 2, 3):
            if last_zero > last_inserted_zero:
                parent = last_zero
                last_inserted_zero = last_zero
        default = 128 if transform_type == 3 else 0
        x = y = z = default
        if present & 1:
            x, values_pos = read_smart(data, values_pos)
        if present & 2:
            y, values_pos = read_smart(data, values_pos)
        if present & 4:
            z, values_pos = read_smart(data, values_pos)
        if transform_type == 2:
            x = ((x & 0xFF) << 3) + ((x >> 8) & 7)
            y = ((y & 0xFF) << 3) + ((y >> 8) & 7)
            z = ((z & 0xFF) << 3) + ((z >> 8) & 7)
        entries.append({
            "transform": transform_index,
            "parent": parent,
            "type": transform_type,
            "x": x,
            "y": y,
            "z": z,
            "flags": present,
        })
    if values_pos != len(data):
        raise ValueError(f"frame parse ended at {values_pos}, expected {len(data)}")
    return {"skeleton_id": skeleton_id, "entries": entries}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = RAW_ANIM_GROUP.read_bytes()
    group = decode_container(raw)
    files = split_group(group)

    rows = []
    for index, data in enumerate(files):
        (OUT_DIR / f"characters_{index:03}.nm").write_bytes(data)
        parsed = parse_nm(data)
        rows.append({
            "index": index,
            "bytes": len(data),
            "frame_count": len(parsed["frames"]),
            "total_duration": sum(parsed["durations"]),
            "loop_start": parsed["loop_start"],
            "loop_count": parsed["loop_count"],
            "replay_mode": parsed["replay_mode"],
            "opcodes": " ".join(str(op) for op in parsed["opcodes"]),
            "frames": " ".join(str(frame) for frame in parsed["frames"]),
            "durations": " ".join(str(duration) for duration in parsed["durations"]),
        })

    with (OUT_DIR / "characters_animation_sequences.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    skeleton_group = decode_container((ROOT.parent / "deob" / "kickabout-asset-dump" / "15_0.bin").read_bytes())
    skeleton_files = split_group(skeleton_group)
    skeletons = {}
    skeleton_rows = []
    skeleton_transform_rows = []
    for index, data in enumerate(skeleton_files):
        (OUT_DIR / f"skeleton_{index:03}.bin").write_bytes(data)
        parsed = parse_skeleton(data, index)
        skeletons[index] = parsed
        skeleton_rows.append({
            "index": index,
            "bytes": len(data),
            "transform_count": parsed["count"],
            "transform_types": " ".join(str(value) for value in parsed["transform_types"]),
            "parsed_bytes": parsed["parsed_bytes"],
        })
        for transform_index, transform_type in enumerate(parsed["transform_types"]):
            skeleton_transform_rows.append({
                "skeleton_id": index,
                "transform_index": transform_index,
                "type": transform_type,
                "mask": parsed["masks"][transform_index],
                "groups": " ".join(str(value) for value in parsed["groups"][transform_index]),
            })
    with (OUT_DIR / "skeletons.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=skeleton_rows[0].keys())
        writer.writeheader()
        writer.writerows(skeleton_rows)
    with (OUT_DIR / "skeleton_transforms.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=skeleton_transform_rows[0].keys())
        writer.writeheader()
        writer.writerows(skeleton_transform_rows)

    frame_group = decode_container((ROOT.parent / "deob" / "kickabout-asset-dump" / "14_0.bin").read_bytes())
    frame_files = split_group(frame_group)
    frame_rows = []
    frame_entry_rows = []
    for index, data in enumerate(frame_files):
        parsed = parse_frame(data, skeletons)
        frame_rows.append({
            "index": index,
            "bytes": len(data),
            "skeleton_id": parsed["skeleton_id"],
            "entry_count": len(parsed["entries"]),
            "types": " ".join(str(entry["type"]) for entry in parsed["entries"]),
        })
        skeleton = skeletons[parsed["skeleton_id"]]
        for order, entry in enumerate(parsed["entries"]):
            frame_entry_rows.append({
                "frame_index": index,
                "skeleton_id": parsed["skeleton_id"],
                "order": order,
                "transform_index": entry["transform"],
                "parent": entry["parent"],
                "type": entry["type"],
                "x": entry["x"],
                "y": entry["y"],
                "z": entry["z"],
                "flags": entry["flags"],
                "groups": " ".join(str(value) for value in skeleton["groups"][entry["transform"]]),
            })
    with (OUT_DIR / "frames.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=frame_rows[0].keys())
        writer.writeheader()
        writer.writerows(frame_rows)
    with (OUT_DIR / "frame_entries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=frame_entry_rows[0].keys())
        writer.writeheader()
        writer.writerows(frame_entry_rows)
    print(f"decoded {len(files)} character animation sequences")
    print(f"decoded {len(skeleton_files)} skeletons and {len(frame_files)} frames to {OUT_DIR}")


if __name__ == "__main__":
    main()

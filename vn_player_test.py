import colorsys
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import pygame


SCREEN_W = 960
SCREEN_H = 640
FPS = 60
RENDER_HEADING_STEPS = 2048
RENDER_FRAME_COUNT = 32
RENDER_TURN_STEPS_PER_SECOND = 3200
ROOT = Path(__file__).resolve().parent
VN_ASSETS = ROOT / "assets" / "kickabout-named-assets"
if not VN_ASSETS.exists():
    VN_ASSETS = ROOT / "kickabout-named-assets"
if not VN_ASSETS.exists():
    VN_ASSETS = Path(r"C:\Users\reidm\OneDrive\Desktop\codex\deob\kickabout-named-assets")
ANIMATION_DIR = ROOT / "research" / "animation-decoded"
FIELD = pygame.Rect(70, 55, 820, 530)
PLAYER_SPEED = 190
SPRINT_SPEED = 260
BALL_GRAVITY = 820
GROUND_FRICTION = 0.985
AIR_FRICTION = 0.996

CHARACTERS = [
    ("Hotshot", "striker", 1, 17, 31, PLAYER_SPEED, SPRINT_SPEED, False),
    ("Ranger", "scout", 3, 24, 31, 230, 310, False),
    ("Tank", "tank", 0, 16, 15, 155, 220, False),
    ("Keeper", "keeper", 4, None, None, 185, 245, True),
]

HEAD_VARIANTS = {
    0: [
        ("skin 1", 1, 0x1192),
        ("skin 2", 2, 0x0D64),
        ("skin 3", 3, 0x0DE5),
        ("afro", 4, 0x1997),
        ("skin 5", 5, 0x0D52),
    ],
    1: [
        ("skin 1", 1, 0x09B9),
        ("skin 2", 2, 0x0DB9),
        ("skin 3", 3, 0x0D97),
        ("skin 4", 4, 0x0DC0),
        ("skin 5", 5, 0x09B9),
    ],
    2: [
        ("skin 1", 1, 0x09D2),
        ("skin 2", 2, 0x0DD2),
        ("skin 3", 3, 0x0D1A),
        ("skin 4", 4, 0x15DA),
        ("skin 5", 5, 0x0DD2),
    ],
    3: [
        ("skin 1", 1, 0x0962),
        ("skin 2", 2, 0x1196),
        ("skin 3", 3, 0x1531),
        ("skin 4", 4, 0x0962),
        ("skin 5", 5, 0x15DA),
    ],
    4: [
        ("head 1", 1, None),
        ("head 2", 2, None),
        ("head 3", 3, None),
        ("head 4", 4, None),
        ("head 5", 5, None),
    ],
}

KIT_PALETTE = [
    0x038A, 0x138A, 0x238A, 0x338A, 0x438A, 0x538A, 0x638A, 0x738A,
    0x838A, 0x938A, 0xA38A, 0xB38A, 0xC38A, 0xD38A, 0x0014, 0x0001,
    0x03B2, 0x13B2, 0x23B2, 0x33B2, 0x43B2, 0x53B2, 0x63B2, 0x73B2,
    0x83B2, 0x93B2, 0xA3B2, 0xB3B2, 0xC3B2, 0xD3B2, 0x0028, 0x007C,
]


def clamp(value, low, high):
    return max(low, min(high, value))


class Reader:
    def __init__(self, data, pos=0):
        self.data = data
        self.pos = pos

    def u8(self):
        value = self.data[self.pos]
        self.pos += 1
        return value

    def i8(self):
        value = self.data[self.pos]
        self.pos += 1
        return value - 256 if value > 127 else value

    def u16(self):
        value = int.from_bytes(self.data[self.pos:self.pos + 2], "big")
        self.pos += 2
        return value

    def smart(self):
        peek = self.data[self.pos]
        if peek < 128:
            return self.u8() - 64
        return self.u16() - 49152


@dataclass
class VNMesh:
    vertices: list
    faces: list
    colors: list
    vertex_groups: list
    face_groups: list


@dataclass
class CharacterVariant:
    label: str
    frames: list
    mesh: VNMesh
    color_map: dict
    head_index: int
    body_base_color: int | None


@dataclass
class CharacterSet:
    name: str
    variants: list
    walk_speed: int
    sprint_speed: int
    keeper: bool


@dataclass
class AnimationFrameEntry:
    skeleton_id: int
    transform_index: int
    parent: int
    type: int
    x: int
    y: int
    z: int
    groups: list


@dataclass
class AnimationSequence:
    index: int
    frames: list
    durations: list


@dataclass
class AnimationDatabase:
    sequences: dict
    frame_entries: dict
    skeleton_groups: dict


def load_vn_new(path):
    data = path.read_bytes()
    if len(data) < 23 or data[-2:] != b"\xff\xff":
        raise ValueError(f"{path.name} is not the new VN format")

    header = Reader(data, len(data) - 23)
    vertex_count = header.u16()
    face_count = header.u16()
    tex_count = header.u8()
    flags = header.u8()
    has_face_type = bool(flags & 1)
    priority_flag = header.u8()
    alpha_flag = header.u8()
    face_group_flag = header.u8()
    texture_flag = header.u8()
    vertex_group_flag = header.u8()
    x_len = header.u16()
    y_len = header.u16()
    z_len = header.u16()
    face_index_len = header.u16()
    texture_coord_len = header.u16()

    cursor = tex_count
    vertex_flag_off = cursor
    cursor += vertex_count
    face_type_off = cursor
    if has_face_type:
        cursor += face_count
    face_opcode_off = cursor
    cursor += face_count
    priority_off = cursor
    if priority_flag == 255:
        cursor += face_count
    face_group_off = cursor
    if face_group_flag == 1:
        cursor += face_count
    vertex_group_off = cursor
    if vertex_group_flag == 1:
        cursor += vertex_count
    alpha_off = cursor
    if alpha_flag == 1:
        cursor += face_count
    face_index_off = cursor
    cursor += face_index_len
    texture_index_off = cursor
    if texture_flag == 1:
        cursor += face_count * 2
    texture_extra_off = cursor
    cursor += texture_coord_len
    face_color_off = cursor
    cursor += face_count * 2
    x_off = cursor
    cursor += x_len
    y_off = cursor
    cursor += y_len
    z_off = cursor
    cursor += z_len

    flag_reader = Reader(data, vertex_flag_off)
    xr = Reader(data, x_off)
    yr = Reader(data, y_off)
    zr = Reader(data, z_off)
    vertices = []
    x = y = z = 0
    for _ in range(vertex_count):
        bits = flag_reader.u8()
        dx = xr.smart() if bits & 1 else 0
        dy = yr.smart() if bits & 2 else 0
        dz = zr.smart() if bits & 4 else 0
        x += dx
        y += dy
        z += dz
        vertices.append((x, y, z))

    color_reader = Reader(data, face_color_off)
    colors = [color_reader.u16() for _ in range(face_count)]
    vertex_groups = None
    if vertex_group_flag == 1:
        group_reader = Reader(data, vertex_group_off)
        vertex_groups = [group_reader.u8() for _ in range(vertex_count)]
    face_groups = None
    if face_group_flag == 1:
        group_reader = Reader(data, face_group_off)
        face_groups = [group_reader.u8() for _ in range(face_count)]

    opcode_reader = Reader(data, face_opcode_off)
    index_reader = Reader(data, face_index_off)
    faces = []
    kept_colors = []
    kept_face_groups = []
    a = b = c = last = 0
    for face_index in range(face_count):
        opcode = opcode_reader.u8()
        if opcode == 1:
            a = index_reader.smart() + last
            b = index_reader.smart() + a
            c = index_reader.smart() + b
            last = c
        elif opcode == 2:
            b = c
            c = index_reader.smart() + last
            last = c
        elif opcode == 3:
            a = c
            c = index_reader.smart() + last
            last = c
        elif opcode == 4:
            a, b = b, a
            c = index_reader.smart() + last
            last = c
        if 0 <= a < vertex_count and 0 <= b < vertex_count and 0 <= c < vertex_count:
            faces.append((a, b, c))
            kept_colors.append(colors[face_index])
            kept_face_groups.append(face_groups[face_index] if face_groups is not None else -1)

    if vertex_groups is None:
        vertex_groups = [-1] * len(vertices)
    return VNMesh(vertices, faces, kept_colors, vertex_groups, kept_face_groups)


def combine_meshes(meshes):
    vertices = []
    faces = []
    colors = []
    vertex_groups = []
    face_groups = []
    offset = 0
    for mesh in meshes:
        vertices.extend(mesh.vertices)
        faces.extend((a + offset, b + offset, c + offset) for a, b, c in mesh.faces)
        colors.extend(mesh.colors)
        vertex_groups.extend(mesh.vertex_groups)
        face_groups.extend(mesh.face_groups)
        offset += len(mesh.vertices)
    return VNMesh(vertices, faces, colors, vertex_groups, face_groups)


def build_group_table(group_ids):
    groups = {}
    for index, group_id in enumerate(group_ids):
        if group_id < 0:
            continue
        groups.setdefault(group_id, []).append(index)
    if not groups:
        return []
    return [groups.get(group_id, []) for group_id in range(max(groups) + 1)]


def parse_ints(text):
    return [int(part) for part in text.split()] if text else []


def load_animation_database():
    sequence_path = ANIMATION_DIR / "characters_animation_sequences.csv"
    entry_path = ANIMATION_DIR / "frame_entries.csv"
    skeleton_path = ANIMATION_DIR / "skeleton_transforms.csv"
    if not sequence_path.exists() or not entry_path.exists() or not skeleton_path.exists():
        return AnimationDatabase({}, {}, {})

    sequences = {}
    with sequence_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            index = int(row["index"])
            sequences[index] = AnimationSequence(
                index=index,
                frames=parse_ints(row["frames"]),
                durations=parse_ints(row["durations"]),
            )

    skeleton_groups = {}
    with skeleton_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            skeleton_id = int(row["skeleton_id"])
            transform_index = int(row["transform_index"])
            skeleton_groups[(skeleton_id, transform_index)] = parse_ints(row["groups"])

    frame_entries = {}
    with entry_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            frame_index = int(row["frame_index"])
            frame_entries.setdefault(frame_index, []).append(AnimationFrameEntry(
                skeleton_id=int(row["skeleton_id"]),
                transform_index=int(row["transform_index"]),
                parent=int(row["parent"]),
                type=int(row["type"]),
                x=int(row["x"]),
                y=int(row["y"]),
                z=int(row["z"]),
                groups=parse_ints(row["groups"]),
            ))
    return AnimationDatabase(sequences, frame_entries, skeleton_groups)


def copy_mesh_with_vertices(mesh, vertices):
    return VNMesh(vertices, mesh.faces, mesh.colors, mesh.vertex_groups, mesh.face_groups)


def repair_orphan_animation_groups(mesh, max_group):
    repaired = list(mesh.vertex_groups)
    for vertex_index, group_id in enumerate(mesh.vertex_groups):
        if group_id <= max_group:
            continue
        neighbor_groups = {}
        for face in mesh.faces:
            if vertex_index not in face:
                continue
            for neighbor in face:
                if neighbor == vertex_index:
                    continue
                neighbor_group = mesh.vertex_groups[neighbor]
                if 0 <= neighbor_group <= max_group:
                    neighbor_groups[neighbor_group] = neighbor_groups.get(neighbor_group, 0) + 1
        if neighbor_groups:
            repaired[vertex_index] = max(neighbor_groups, key=neighbor_groups.get)
    return repaired


def trig_2048(angle):
    radians = (angle & 2047) / 2048 * math.tau
    return math.sin(radians), math.cos(radians)


def vertices_for_groups(vertex_table, group_ids):
    vertices = []
    for group_id in group_ids:
        if 0 <= group_id < len(vertex_table):
            vertices.extend(vertex_table[group_id])
    return vertices


def compute_animation_pivot(vertices, vertex_table, group_ids, x, y, z):
    indices = vertices_for_groups(vertex_table, group_ids)
    if not indices:
        return [x, y, z]
    sx = sy = sz = 0
    for index in indices:
        vx, vy, vz = vertices[index]
        sx += vx
        sy += vy
        sz += vz
    count = len(indices)
    return [sx / count + x, sy / count + y, sz / count + z]


def apply_transform(vertices, vertex_table, entry, pivot):
    indices = vertices_for_groups(vertex_table, entry.groups)
    if entry.type == 0:
        return compute_animation_pivot(vertices, vertex_table, entry.groups, entry.x, entry.y, entry.z)
    if not indices:
        return pivot
    if entry.type == 1:
        for index in indices:
            x, y, z = vertices[index]
            vertices[index] = (x + entry.x, y + entry.y, z + entry.z)
        return pivot
    if entry.type == 2:
        sin_z, cos_z = trig_2048(entry.z)
        sin_x, cos_x = trig_2048(entry.x)
        sin_y, cos_y = trig_2048(entry.y)
        px, py, pz = pivot
        for index in indices:
            x, y, z = vertices[index]
            x -= px
            y -= py
            z -= pz
            if entry.z:
                nx = y * sin_z + x * cos_z
                ny = y * cos_z - x * sin_z
                x, y = nx, ny
            if entry.x:
                ny = y * cos_x - z * sin_x
                nz = y * sin_x + z * cos_x
                y, z = ny, nz
            if entry.y:
                nx = z * sin_y + x * cos_y
                nz = z * cos_y - x * sin_y
                x, z = nx, nz
            vertices[index] = (x + px, y + py, z + pz)
        return pivot
    if entry.type == 3:
        px, py, pz = pivot
        sx = entry.x / 128
        sy = entry.y / 128
        sz = entry.z / 128
        for index in indices:
            x, y, z = vertices[index]
            vertices[index] = ((x - px) * sx + px, (y - py) * sy + py, (z - pz) * sz + pz)
    return pivot


def animated_mesh_for_frame(mesh, animation_db, frame_index):
    entries = animation_db.frame_entries.get(frame_index & 0xFFFF)
    if not entries:
        return mesh
    vertices = [tuple(vertex) for vertex in mesh.vertices]
    max_group = max((group for entry in entries for group in entry.groups), default=-1)
    vertex_groups = repair_orphan_animation_groups(mesh, max_group)
    vertex_table = build_group_table(vertex_groups)
    pivot = [0, 0, 0]
    for entry in entries:
        if entry.parent >= 0:
            parent_groups = animation_db.skeleton_groups.get((entry.skeleton_id, entry.parent), [])
            pivot = compute_animation_pivot(vertices, vertex_table, parent_groups, 0, 0, 0)
        pivot = apply_transform(vertices, vertex_table, entry, pivot)
    return copy_mesh_with_vertices(mesh, vertices)


def hsl16_to_rgb(value):
    hue = ((value >> 10) & 63) / 64
    sat = ((value >> 7) & 7) / 7
    light = (value & 127) / 127
    r, g, b = colorsys.hls_to_rgb(hue, light, sat)
    return int(r * 255), int(g * 255), int(b * 255)


def kit_placeholder_colors(saturation):
    colors = set()
    light_row = 0
    for _ in range(13):
        hue = 20
        for _ in range(10):
            colors.add(hue | (light_row << 10) | (saturation << 7))
            hue += 5
        light_row += 3
    return colors


KIT_PRIMARY_PLACEHOLDERS = kit_placeholder_colors(7)
KIT_SECONDARY_PLACEHOLDERS = kit_placeholder_colors(6)


def build_color_map(mesh, body_base_color, primary_index, secondary_index):
    color_map = {}
    if body_base_color is not None:
        color_map[0xDBBC] = hsl16_to_rgb(body_base_color)
    if primary_index is not None:
        primary = hsl16_to_rgb(KIT_PALETTE[primary_index])
        for color in KIT_PRIMARY_PLACEHOLDERS.intersection(mesh.colors):
            color_map[color] = primary
    if secondary_index is not None:
        secondary = hsl16_to_rgb(KIT_PALETTE[secondary_index])
        for color in KIT_SECONDARY_PLACEHOLDERS.intersection(mesh.colors):
            color_map[color] = secondary
    return color_map


def rotate_project(vertex, yaw, scale, center):
    x, y, z = vertex
    cy = math.cos(yaw)
    sy = math.sin(yaw)
    rx = x * cy + z * sy
    rz = -x * sy + z * cy
    sx = center[0] + rx * scale
    sy2 = center[1] + y * scale + rz * scale * 0.16
    return sx, sy2, rz


def render_mesh(mesh, yaw, size=(116, 150), scale=0.34, color_map=None):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    center = (size[0] / 2, size[1] * 0.91)
    projected = [rotate_project(v, yaw, scale, center) for v in mesh.vertices]
    draw_faces = []
    for face, color in zip(mesh.faces, mesh.colors):
        pts = [projected[i] for i in face]
        area = (
            (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1])
            - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
        )
        if abs(area) < 0.2:
            continue
        depth = sum(p[2] for p in pts) / 3
        rgb = color_map.get(color, hsl16_to_rgb(color)) if color_map else hsl16_to_rgb(color)
        shade = clamp(0.82 + depth * 0.002, 0.55, 1.15)
        shaded = tuple(clamp(round(c * shade), 0, 255) for c in rgb)
        draw_faces.append((depth, [(p[0], p[1]) for p in pts], shaded))
    for _, pts, color in sorted(draw_faces, key=lambda item: item[0]):
        pygame.draw.polygon(surface, color, pts)
    return surface


def render_yaw_for_frame(index):
    steps = index * RENDER_HEADING_STEPS / RENDER_FRAME_COUNT
    return steps / RENDER_HEADING_STEPS * math.tau


def load_player_surfaces(prefix, head_index, body_base_color, primary_index, secondary_index, keeper=False):
    body = load_vn_new(VN_ASSETS / f"Characters_{prefix}_body.bin")
    head = load_vn_new(VN_ASSETS / f"Characters_{prefix}_head_{head_index:02d}.bin")
    mesh = combine_meshes([body, head])
    color_map = {} if keeper else build_color_map(mesh, body_base_color, primary_index, secondary_index)
    frames = []
    for i in range(RENDER_FRAME_COUNT):
        frames.append(render_mesh(mesh, render_yaw_for_frame(i), color_map=color_map))
    return frames, mesh, color_map


def load_ball_surfaces():
    ball = load_vn_new(VN_ASSETS / "balls_skin_football.bin")
    return [render_mesh(ball, i * math.tau / 16, (42, 42), 0.42) for i in range(16)]


def vector_to_heading_steps(vec):
    if vec.length_squared() <= 0.01:
        return 0
    angle = math.atan2(-vec.x, -vec.y)
    return round((angle % math.tau) / math.tau * RENDER_HEADING_STEPS) % RENDER_HEADING_STEPS


def heading_frame_index(heading_steps, frame_count):
    return round((heading_steps % RENDER_HEADING_STEPS) / RENDER_HEADING_STEPS * frame_count) % frame_count


def turn_heading(current, target, max_delta):
    diff = (target - current + RENDER_HEADING_STEPS // 2) % RENDER_HEADING_STEPS - RENDER_HEADING_STEPS // 2
    diff = clamp(diff, -max_delta, max_delta)
    return (current + diff) % RENDER_HEADING_STEPS


def input_mask(keys):
    mask = 0
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        mask |= 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        mask |= 2
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        mask |= 4
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        mask |= 8
    return mask


def movement_from_mask(mask):
    x = 0
    y = 0
    if mask & 1:
        x += 1
    if mask & 4:
        x -= 1
    if mask & 2:
        y -= 1
    if mask & 8:
        y += 1
    move = pygame.Vector2(x, y)
    return move.normalize() if move.length_squared() else move


class Ball:
    def __init__(self, frames):
        self.frames = frames
        self.pos = pygame.Vector2(FIELD.center)
        self.vel = pygame.Vector2()
        self.z = 0.0
        self.vz = 0.0
        self.carrier = None
        self.uncatchable = 0.0

    def release(self, direction, speed, lift):
        direction = direction.normalize() if direction.length_squared() else pygame.Vector2(0, -1)
        self.carrier = None
        self.pos += direction * 24
        self.vel = direction * speed
        self.vz = lift
        self.z = 4
        self.uncatchable = 0.28

    def update(self, dt, player):
        self.uncatchable = max(0, self.uncatchable - dt)
        if self.carrier:
            self.pos = self.carrier.pos + self.carrier.facing * 30
            self.vel.update(0, 0)
            self.z = 0
            self.vz = 0
            return
        self.pos += self.vel * dt
        self.z += self.vz * dt
        self.vz -= BALL_GRAVITY * dt
        if self.z <= 0:
            self.z = 0
            if self.vz < 0:
                self.vz *= -0.44
                if abs(self.vz) < 65:
                    self.vz = 0
        self.vel *= AIR_FRICTION if self.z > 2 else GROUND_FRICTION
        if self.vel.length() < 12:
            self.vel.update(0, 0)
        self.pos.x = clamp(self.pos.x, FIELD.left + 10, FIELD.right - 10)
        self.pos.y = clamp(self.pos.y, FIELD.top + 10, FIELD.bottom - 10)
        if self.uncatchable <= 0 and self.z < 32 and self.pos.distance_to(player.pos) < 42:
            self.carrier = player

    def draw(self, screen):
        ground = self.pos
        shadow = pygame.Surface((38, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 95), shadow.get_rect())
        screen.blit(shadow, shadow.get_rect(center=(ground.x, ground.y + 12)))
        frame = self.frames[round(pygame.time.get_ticks() / 75) % len(self.frames)]
        scale = clamp(1 + self.z / 120, 1, 1.55)
        image = pygame.transform.smoothscale(frame, (round(frame.get_width() * scale), round(frame.get_height() * scale)))
        screen.blit(image, image.get_rect(center=(ground.x, ground.y - self.z)))


class Player:
    def __init__(self, character_sets, animation_db):
        self.character_sets = character_sets
        self.animation_db = animation_db
        self.character_index = 0
        self.variant_index = 0
        self.character = self.character_sets[self.character_index]
        self.variant = self.character.variants[self.variant_index]
        self.name = self.character.name
        self.frames = self.variant.frames
        self.walk_speed = self.character.walk_speed
        self.sprint_speed = self.character.sprint_speed
        self.keeper = self.character.keeper
        self.pos = pygame.Vector2(FIELD.centerx, FIELD.centery + 130)
        self.vel = pygame.Vector2()
        self.facing = pygame.Vector2(0, -1)
        self.heading_steps = vector_to_heading_steps(self.facing)
        self.target_heading_steps = self.heading_steps
        self.slide = 0.0
        self.cooldown = 0.0
        self.keeper_dive = 0.0
        self.keeper_recovery = 0.0
        self.keeper_target_x = self.pos.x
        self.pose = "idle"
        self.anim_enabled = bool(animation_db.sequences)
        self.anim_sequence_index = min(animation_db.sequences) if animation_db.sequences else -1
        self.anim_time = 0.0

    def cycle_character(self, delta):
        self.character_index = (self.character_index + delta) % len(self.character_sets)
        self.variant_index = 0
        self.apply_character()

    def set_character(self, index):
        if 0 <= index < len(self.character_sets):
            self.character_index = index
            self.variant_index = 0
            self.apply_character()

    def cycle_variant(self, delta):
        self.variant_index = (self.variant_index + delta) % len(self.character.variants)
        self.apply_character()

    def apply_character(self):
        self.character = self.character_sets[self.character_index]
        self.variant_index %= len(self.character.variants)
        self.variant = self.character.variants[self.variant_index]
        self.name = self.character.name
        self.frames = self.variant.frames
        self.walk_speed = self.character.walk_speed
        self.sprint_speed = self.character.sprint_speed
        self.keeper = self.character.keeper
        self.slide = 0.0
        self.keeper_dive = 0.0
        self.keeper_recovery = 0.0
        self.cooldown = 0.0

    def cycle_animation_sequence(self, delta):
        if not self.animation_db.sequences:
            return
        sequence_ids = sorted(self.animation_db.sequences)
        current = sequence_ids.index(self.anim_sequence_index) if self.anim_sequence_index in sequence_ids else 0
        self.anim_sequence_index = sequence_ids[(current + delta) % len(sequence_ids)]
        self.anim_time = 0.0

    def toggle_animation_preview(self):
        if self.animation_db.sequences:
            self.anim_enabled = not self.anim_enabled

    def current_animation_frame(self):
        sequence = self.animation_db.sequences.get(self.anim_sequence_index)
        if not sequence or not sequence.frames:
            return None
        durations = sequence.durations or [1] * len(sequence.frames)
        total = sum(max(1, duration) for duration in durations)
        tick = int(self.anim_time * 50) % total
        elapsed = 0
        for frame_index, duration in zip(sequence.frames, durations):
            elapsed += max(1, duration)
            if tick < elapsed:
                return frame_index
        return sequence.frames[-1]

    def face_direction(self, direction, snap=False):
        if direction.length_squared() <= 0.01:
            return
        self.facing = direction.normalize()
        self.target_heading_steps = vector_to_heading_steps(self.facing)
        if snap:
            self.heading_steps = self.target_heading_steps

    def face_toward(self, target, snap=False):
        self.face_direction(pygame.Vector2(target) - self.pos, snap)

    def update(self, dt, keys, ball=None):
        self.anim_time += dt
        self.cooldown = max(0, self.cooldown - dt)
        self.slide = max(0, self.slide - dt)
        self.keeper_dive = max(0, self.keeper_dive - dt)
        self.keeper_recovery = max(0, self.keeper_recovery - dt)
        move = movement_from_mask(input_mask(keys))
        if self.keeper_dive > 0:
            direction_x = 1 if self.keeper_target_x >= self.pos.x else -1
            self.vel.update(direction_x * 300, 0)
            self.facing.update(direction_x, 0)
            self.pose = "keeper dive"
        elif self.keeper_recovery > 0:
            self.vel.update(0, 0)
            self.pose = "keeper stand"
        elif self.slide > 0:
            self.vel = self.facing * 360
            self.pose = "tackle"
        else:
            if move.length_squared():
                self.face_direction(move)
            speed = self.sprint_speed if keys[pygame.K_SPACE] else self.walk_speed
            self.vel = move * speed
            if self.keeper and move.length_squared():
                self.pose = "keeper shuffle"
            elif move.length_squared():
                self.pose = "dash" if keys[pygame.K_SPACE] else "move"
            else:
                self.pose = "idle"
        if self.facing.length_squared():
            self.target_heading_steps = vector_to_heading_steps(self.facing)
        max_turn = RENDER_TURN_STEPS_PER_SECOND * dt
        self.heading_steps = turn_heading(self.heading_steps, self.target_heading_steps, max_turn)
        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, FIELD.left + 22, FIELD.right - 22)
        self.pos.y = clamp(self.pos.y, FIELD.top + 22, FIELD.bottom - 22)

    def tackle(self, ball):
        if self.cooldown > 0:
            return
        aim = aim_direction(self)
        self.face_direction(aim)
        if self.keeper:
            self.keeper_target_x = clamp(self.pos.x + clamp(aim.x, -1, 1) * 125, FIELD.left + 22, FIELD.right - 22)
            self.keeper_dive = 0.40
            self.keeper_recovery = 1.20
            self.cooldown = 1.10
            return
        self.slide = 0.22
        self.cooldown = 0.45
        if ball.carrier is None and ball.z < 40 and self.pos.distance_to(ball.pos) < 70:
            ball.release(ball.pos - self.pos, 520, 70)

    def draw(self, screen):
        pygame.draw.ellipse(screen, (0, 0, 0, 85), (self.pos.x - 20, self.pos.y + 23, 40, 14))
        frame_index = self.current_animation_frame() if self.anim_enabled else None
        if frame_index is None:
            frame = self.frames[heading_frame_index(self.heading_steps, len(self.frames))]
        else:
            animated = animated_mesh_for_frame(self.variant.mesh, self.animation_db, frame_index)
            frame = render_mesh(
                animated,
                render_yaw_for_frame(heading_frame_index(self.heading_steps, RENDER_FRAME_COUNT)),
                color_map=self.variant.color_map,
            )
        y_offset = -54
        scale = 1.0
        angle = 0.0
        if self.slide > 0:
            y_offset = -47
            scale = 1.08
        elif self.keeper_dive > 0:
            direction_x = 1 if self.keeper_target_x >= self.pos.x else -1
            angle = -72 * direction_x
            scale = 1.08
            y_offset = -46
        elif self.pose == "keeper stand":
            angle = math.sin(pygame.time.get_ticks() / 75) * 5
            y_offset = -50
        elif self.pose == "keeper shuffle":
            y_offset = -54 + math.sin(pygame.time.get_ticks() / 70) * 3
        elif self.pose == "dash":
            angle = math.sin(pygame.time.get_ticks() / 45) * 4
        if angle or scale != 1.0:
            frame = pygame.transform.rotozoom(frame, angle, scale)
        screen.blit(frame, frame.get_rect(center=(self.pos.x, self.pos.y + y_offset)))
        if self.pose.startswith("keeper"):
            label = self.pose.replace("keeper ", "")
            font = pygame.font.SysFont("arial", 12, bold=True)
            text = font.render(label, True, (250, 246, 210))
            screen.blit(text, text.get_rect(center=(self.pos.x, self.pos.y - 118)))


def load_character_sets():
    sets = []
    for name, prefix, class_id, primary_index, secondary_index, walk_speed, sprint_speed, keeper in CHARACTERS:
        variants = []
        for label, head_index, body_base_color in HEAD_VARIANTS[class_id]:
            frames, mesh, color_map = load_player_surfaces(
                prefix,
                head_index,
                body_base_color,
                primary_index,
                secondary_index,
                keeper,
            )
            variants.append(CharacterVariant(label, frames, mesh, color_map, head_index, body_base_color))
        sets.append(CharacterSet(name, variants, walk_speed, sprint_speed, keeper))
    return sets


def draw_field(screen):
    screen.fill((24, 80, 52))
    stripe_h = FIELD.height // 10
    for i in range(10):
        color = (42, 157, 83) if i % 2 == 0 else (35, 139, 75)
        pygame.draw.rect(screen, color, (FIELD.left, FIELD.top + i * stripe_h, FIELD.width, stripe_h + 1))
    pygame.draw.rect(screen, (232, 244, 228), FIELD, 4)
    pygame.draw.line(screen, (232, 244, 228), (FIELD.left, FIELD.centery), (FIELD.right, FIELD.centery), 3)
    pygame.draw.circle(screen, (232, 244, 228), FIELD.center, 76, 3)
    pygame.draw.rect(screen, (232, 244, 228), (FIELD.centerx - 70, FIELD.top - 16, 140, 16), 3)
    pygame.draw.rect(screen, (232, 244, 228), (FIELD.centerx - 70, FIELD.bottom, 140, 16), 3)


def aim_direction(player):
    mouse = pygame.Vector2(pygame.mouse.get_pos())
    return mouse - player.pos if mouse.distance_to(player.pos) > 4 else player.facing


def main():
    pygame.init()
    pygame.display.set_caption("Kickabout VN Player Test")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 16, bold=True)
    animation_db = load_animation_database()
    player = Player(load_character_sets(), animation_db)
    ball = Ball(load_ball_surfaces())

    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= event.key <= pygame.K_4:
                    player.set_character(event.key - pygame.K_1)
                elif event.key in (pygame.K_q, pygame.K_LEFTBRACKET):
                    player.cycle_character(-1)
                elif event.key in (pygame.K_e, pygame.K_RIGHTBRACKET):
                    player.cycle_character(1)
                elif event.key in (pygame.K_z, pygame.K_COMMA):
                    player.cycle_variant(-1)
                elif event.key in (pygame.K_x, pygame.K_PERIOD):
                    player.cycle_variant(1)
                elif event.key == pygame.K_f:
                    player.toggle_animation_preview()
                elif event.key in (pygame.K_c, pygame.K_SEMICOLON):
                    player.cycle_animation_sequence(-1)
                elif event.key in (pygame.K_v, pygame.K_QUOTE):
                    player.cycle_animation_sequence(1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if ball.carrier is player:
                        aim = aim_direction(player)
                        player.face_direction(aim)
                        ball.release(aim, 720, 95)
                    else:
                        player.tackle(ball)
                elif event.button == 3 and ball.carrier is player:
                    aim = aim_direction(player)
                    player.face_direction(aim)
                    ball.release(aim, 540, 520)

        keys = pygame.key.get_pressed()
        player.update(dt, keys, ball)
        ball.update(dt, player)
        if ball.carrier is None and ball.uncatchable <= 0 and ball.z < 30 and ball.pos.distance_to(player.pos) < 42:
            ball.carrier = player

        draw_field(screen)
        if player.pos.y <= ball.pos.y:
            player.draw(screen)
            ball.draw(screen)
        else:
            ball.draw(screen)
            player.draw(screen)
        help_text = (
            f"1 Hotshot  2 Ranger  3 Tank  4 Keeper | Q/E character | Z/X head-skin | "
            f"current: {player.name} {player.variant.label}"
        )
        screen.blit(font.render(help_text, True, (245, 248, 238)), (18, 16))
        anim_label = "off"
        sequence = player.animation_db.sequences.get(player.anim_sequence_index)
        if player.anim_enabled and sequence:
            frame_id = player.current_animation_frame()
            anim_label = f"seq {sequence.index:02d} frames {len(sequence.frames)} frame {frame_id}"
        controls = (
            "WASD/arrows move | Space sprint | LMB low shot/tackle | RMB lob | "
            f"F anim {anim_label} | C/V seq | Esc quit"
        )
        screen.blit(font.render(controls, True, (245, 248, 238)), (18, 38))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

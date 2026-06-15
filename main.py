import math
import random
from dataclasses import dataclass
from pathlib import Path

import pygame

from vn_player_test import (
    HEAD_VARIANTS,
    animated_mesh_for_frame,
    load_animation_database,
    load_player_surfaces,
    render_mesh,
    render_yaw_for_frame,
)


SCREEN_W = 1100
SCREEN_H = 700
FPS = 60
FIELD = pygame.Rect(100, 90, 900, 1710)
WORLD_SCALE = FIELD.width / 896
GOAL_W = round((525 - 448) * WORLD_SCALE)
PLAYER_R = 20
BALL_R = 9
TICK_RATE = 60
TICK_DT = 1 / TICK_RATE
ANGLE_STEPS = 8192
SURFACE_ID = 0  # 0 park, 1 beach, 2 street
GROUND_FRICTION = [64356 / 65536, 64749 / 65536, 64749 / 65536]
AIR_FRICTION = [64356 / 65536, 63569 / 65536, 64749 / 65536]
HIGH_FRICTION = 60293 / 65536
BOUNCE_DAMPING = 58982 / 65536
BALL_GRAVITY = 0.25 * WORLD_SCALE * TICK_RATE * TICK_RATE
PLAYER_GRAVITY = 0.4 * WORLD_SCALE * TICK_RATE * TICK_RATE
BALL_STOP_SPEED = 0.25 * WORLD_SCALE * TICK_RATE
BALL_UNCATCHABLE_LOW = 20 / TICK_RATE
BALL_UNCATCHABLE_HIGH = 35 / TICK_RATE
BALL_UNCATCHABLE_PASS = 10 / TICK_RATE
BALL_HIGH_FRICTION_TIME = 25 / TICK_RATE
PICKUP_RADIUS = 40 * WORLD_SCALE
HEADER_INTERCEPT_RADIUS = 100 * WORLD_SCALE
SPRITE_FACING_OFFSET = 90
SLIDE_TACKLE_PLAYER_RANGE = 46
AI_REACTION_MIN = 0.18
AI_REACTION_MAX = 0.42
AI_TARGET_ERROR = 34
AI_SHOT_ERROR_DEGREES = 8
AI_KEEPER_ERROR = 22 * WORLD_SCALE

GRASS_A = (44, 168, 91)
GRASS_B = (37, 148, 80)
LINE = (239, 248, 236)
INK = (22, 29, 34)
WHITE = (245, 248, 239)
BLUE = (58, 145, 220)
RED = (222, 88, 68)
YELLOW = (246, 193, 62)
ORANGE = (246, 139, 50)
SHADOW = (20, 40, 28)

ROOT = Path(__file__).resolve().parent
LOCAL_ASSETS = ROOT / "assets" / "kenney_sports-pack" / "PNG"
ASSETS = LOCAL_ASSETS if LOCAL_ASSETS.exists() else ROOT.parent / "kenney-assets" / "packs" / "kenney_sports-pack" / "PNG"

FORMATIONS = {
    "Diamond": {
        "blue": [(0, -0.32), (-0.26, 0.02), (0.26, 0.02), (0, 0.34)],
        "red": [(0, 0.32), (-0.26, -0.02), (0.26, -0.02), (0, -0.34)],
    },
    "Box": {
        "blue": [(-0.22, -0.24), (0.22, -0.24), (-0.22, 0.24), (0.22, 0.24)],
        "red": [(-0.22, 0.24), (0.22, 0.24), (-0.22, -0.24), (0.22, -0.24)],
    },
    "Wide": {
        "blue": [(0, -0.34), (-0.34, 0.0), (0.34, 0.0), (0, 0.34)],
        "red": [(0, 0.34), (-0.34, 0.0), (0.34, 0.0), (0, -0.34)],
    },
    "Y": {
        "blue": [(-0.20, -0.34), (0.20, -0.34), (0, 0.00), (0, 0.34)],
        "red": [(-0.20, 0.34), (0.20, 0.34), (0, 0.00), (0, -0.34)],
    },
    "Upside-down Y": {
        "blue": [(0, -0.34), (0, 0.00), (-0.20, 0.34), (0.20, 0.34)],
        "red": [(0, 0.34), (0, 0.00), (-0.20, -0.34), (0.20, -0.34)],
    },
}
FORMATION_NAMES = list(FORMATIONS)

PLAYER_CLASS_ORDER = ["Hotshot", "Ranger", "Tank"]
PLAYER_CLASSES = {
    "Hotshot": {
        "asset": "hotshot",
        "color": (70, 210, 92),
        "visual_scale": 1.0,
        "run": 187,
        "dribble": 168,
        "sprint": 202,
        "sprint_dribble": 182,
        "slide_speed": 176,
        "charge_stat": 70,
        "shot_power": 1.24,
        "shot_lift": 1.10,
        "tackle_range": 0.78,
        "tackle_power": 0.88,
        "aerial_range": 0.82,
        "aerial_power": 0.90,
    },
    "Ranger": {
        "asset": "ranger",
        "color": BLUE,
        "visual_scale": 0.8,
        "run": 207,
        "dribble": 186,
        "sprint": 225,
        "sprint_dribble": 202,
        "slide_speed": 160,
        "charge_stat": 80,
        "shot_power": 0.88,
        "shot_lift": 0.92,
        "tackle_range": 0.88,
        "tackle_power": 0.90,
        "aerial_range": 0.88,
        "aerial_power": 0.88,
    },
    "Tank": {
        "asset": "tank",
        "color": WHITE,
        "visual_scale": 1.2,
        "run": 172,
        "dribble": 155,
        "sprint": 188,
        "sprint_dribble": 169,
        "slide_speed": 341,
        "charge_stat": 55,
        "shot_power": 1.02,
        "shot_lift": 0.98,
        "tackle_range": 1.36,
        "tackle_power": 1.28,
        "aerial_range": 1.34,
        "aerial_power": 1.22,
    },
}

VN_CLASS_ASSETS = {
    "Hotshot": ("striker", 1, 26, 31, False),
    "Ranger": ("scout", 3, 26, 31, False),
    "Tank": ("tank", 0, 26, 31, False),
    "Keeper": ("keeper", 4, None, None, True),
}

ANIM_TACKLED = 2
ANIM_SLIDE = 5
ANIM_GET_UP = 7
ANIM_POSSESS = 18
ANIM_IDLE = 21


def clamp(value, low, high):
    return max(low, min(high, value))


def load_image(path, scale=1.0):
    image = pygame.image.load(path).convert_alpha()
    if scale != 1.0:
        size = (round(image.get_width() * scale), round(image.get_height() * scale))
        image = pygame.transform.scale(image, size)
    return image


def load_character(color, frame, scale=1.75):
    return load_image(ASSETS / color / f"character{color} ({frame}).png", scale)


def load_character_frames(color, frames=(6,), scale=1.75):
    return [load_character(color, frame, scale) for frame in frames]


def safe_normalize(vec, fallback=pygame.Vector2(0, -1)):
    if vec.length_squared() <= 0.001:
        return fallback.copy()
    return vec.normalize()


def world_to_screen(pos, camera):
    return pygame.Vector2(pos.x - camera.x, pos.y - camera.y)


def screen_to_world(pos, camera):
    return pygame.Vector2(pos) + camera


def ball_side_near_goal(pos, team):
    return pos.y < FIELD.top + 430 if team == "blue" else pos.y > FIELD.bottom - 430


def trig_from_index(angle_index):
    radians = (angle_index & (ANGLE_STEPS - 1)) * math.tau / ANGLE_STEPS
    return math.cos(radians), math.sin(radians)


def kickabout_power_from_charge(elapsed, charge_stat=70):
    cycle = 80 + 120 * (100 - charge_stat) / 100
    stat_window = charge_stat * 14 / 100
    dead_zone = 14 - stat_window
    timer_value = (cycle - elapsed * TICK_RATE) % cycle
    phase = (dead_zone + timer_value) % cycle
    half = cycle / 2
    distance_from_peak = cycle - phase if phase > half else phase
    if distance_from_peak < dead_zone:
        return 0
    if distance_from_peak > half - stat_window:
        return 256
    span = max(1, half - dead_zone - stat_window)
    return clamp(((distance_from_peak - dead_zone) * 256) / span, 0, 256)


def kickabout_impulse(power, high=False, special_low=False):
    kick_scale = 12 + 6 * power / 256
    angle = 700 if high else 227
    cos_v, sin_v = trig_from_index(angle)
    horizontal = kick_scale * cos_v
    vertical = kick_scale * sin_v
    high_friction = False
    if special_low and not high and power > 32:
        horizontal += horizontal * 1.5 + (1280 * power) / 65536
        high_friction = True
    return horizontal * WORLD_SCALE * TICK_RATE, vertical * WORLD_SCALE * TICK_RATE, high_friction


def kickabout_pass_velocity(origin, target, ticks=70):
    friction = GROUND_FRICTION[SURFACE_ID]
    retention = sum(friction ** i for i in range(1, ticks + 1))
    if retention <= 0:
        return pygame.Vector2()
    return (target - origin) / (retention * TICK_DT)


def add_aim_error(direction, degrees):
    direction = safe_normalize(direction)
    return direction.rotate(random.uniform(-degrees, degrees))


def direction_frame_index(direction, frame_count):
    if frame_count <= 1:
        return 0
    direction = safe_normalize(direction)
    angle = math.atan2(-direction.x, -direction.y)
    return round((angle % math.tau) / math.tau * frame_count) % frame_count


@dataclass
class Burst:
    text: str
    pos: pygame.Vector2
    color: tuple
    ttl: float = 0.8

    def update(self, dt):
        self.ttl -= dt
        self.pos.y -= 38 * dt

    def draw(self, surface, font, camera):
        alpha = clamp(self.ttl / 0.8, 0, 1)
        label = font.render(self.text, True, self.color)
        label.set_alpha(round(255 * alpha))
        surface.blit(label, label.get_rect(center=world_to_screen(self.pos, camera)))


@dataclass
class VNVisual:
    frames: list
    mesh: object
    color_map: dict


def sequence_duration(animation_db, sequence_id):
    sequence = animation_db.sequences.get(sequence_id) if animation_db else None
    if not sequence or not sequence.frames:
        return 0
    durations = sequence.durations or [1] * len(sequence.frames)
    return sum(max(1, duration) for duration in durations) / 50


def sequence_frame(animation_db, sequence_id, elapsed, loop=True):
    sequence = animation_db.sequences.get(sequence_id) if animation_db else None
    if not sequence or not sequence.frames:
        return None
    durations = sequence.durations or [1] * len(sequence.frames)
    total = sum(max(1, duration) for duration in durations)
    if total <= 0:
        return sequence.frames[0]
    tick = int(elapsed * 50)
    if loop:
        tick %= total
    else:
        tick = min(tick, total - 1)
    elapsed_ticks = 0
    for frame_index, duration in zip(sequence.frames, durations):
        elapsed_ticks += max(1, duration)
        if tick < elapsed_ticks:
            return frame_index
    return sequence.frames[-1]


class Ball:
    def __init__(self, image):
        self.image = image
        self.pos = pygame.Vector2(FIELD.center)
        self.vel = pygame.Vector2()
        self.z = 0.0
        self.vz = 0.0
        self.last_touch = "blue"
        self.carrier = None
        self.possession_grace = 0.0
        self.clearance_grace = 0.0
        self.protected_clearance_team = None
        self.uncatchable = 0.0
        self.high_friction = 0.0

    def reset(self, direction=1):
        self.carrier = None
        self.pos.update(FIELD.centerx, FIELD.centery - direction * 120)
        self.vel.update(random.uniform(-35, 35), direction * 100)
        self.z = 0
        self.vz = 0
        self.clearance_grace = 0.0
        self.protected_clearance_team = None
        self.uncatchable = 0.0
        self.high_friction = 0.0

    def can_be_collected(self):
        return (
            self.carrier is None
            and self.uncatchable <= 0
            and self.z < 30 * WORLD_SCALE
            and FIELD.top <= self.pos.y <= FIELD.bottom
        )

    def collect(self, player):
        previous_carrier = self.carrier
        self.carrier = player
        player.slide_visual = 0.0
        self.last_touch = player.team
        if previous_carrier is not player:
            self.possession_grace = 0.85 if player.team == "blue" and not player.keeper else 0.35
        self.clearance_grace = 0.0
        self.protected_clearance_team = None
        self.uncatchable = 0.0
        self.high_friction = 0.0
        self.z = 0
        self.vz = 0
        self.vel.update(0, 0)

    def release(self, direction, power, lift, team, uncatchable=BALL_UNCATCHABLE_LOW, high_friction=False):
        direction = safe_normalize(direction)
        self.carrier = None
        self.pos += direction * 18
        self.vel = direction * power
        self.vz = lift
        self.z = max(self.z, 2)
        self.last_touch = team
        self.uncatchable = uncatchable
        self.high_friction = BALL_HIGH_FRICTION_TIME if high_friction else 0.0

    def update(self, dt):
        self.possession_grace = max(0, self.possession_grace - dt)
        self.clearance_grace = max(0, self.clearance_grace - dt)
        self.uncatchable = max(0, self.uncatchable - dt)
        self.high_friction = max(0, self.high_friction - dt)
        if self.carrier:
            carry_dir = safe_normalize(self.carrier.facing)
            self.pos = self.carrier.pos + carry_dir * 29
            self.vel = self.carrier.vel * 0.45
            self.z = 0
            self.vz = 0
            return

        remaining = dt
        while remaining > 0:
            step = min(TICK_DT, remaining)
            tick_scale = step / TICK_DT
            previous_vel = self.vel.copy()
            previous_vz = self.vz

            self.pos.x += self.vel.x * step
            if self.pos.x < FIELD.left + BALL_R:
                self.pos.x = FIELD.left + BALL_R
                self.vel.x = abs(self.vel.x)
            elif self.pos.x > FIELD.right - BALL_R:
                self.pos.x = FIELD.right - BALL_R
                self.vel.x = -abs(self.vel.x)

            self.pos.y += self.vel.y * step
            in_goal_mouth = FIELD.centerx - GOAL_W <= self.pos.x <= FIELD.centerx + GOAL_W
            if self.pos.y < FIELD.top + BALL_R and not in_goal_mouth:
                self.pos.y = FIELD.top + BALL_R
                self.vel.y = abs(self.vel.y)
            elif self.pos.y > FIELD.bottom - BALL_R and not in_goal_mouth:
                self.pos.y = FIELD.bottom - BALL_R
                self.vel.y = -abs(self.vel.y)

            self.z += self.vz * step
            if self.z <= 0:
                self.z = 0
                if self.vz < 0:
                    self.vz = -self.vz
            self.vz -= BALL_GRAVITY * step

            if self.vel.x != previous_vel.x:
                self.vel.x *= BOUNCE_DAMPING
            if self.vel.y != previous_vel.y:
                self.vel.y *= BOUNCE_DAMPING
            if self.vz != previous_vz and self.z <= 0:
                self.vz *= BOUNCE_DAMPING
                if abs(self.vz) < 85:
                    self.vz = 0
                    self.protected_clearance_team = None
                    self.clearance_grace = 0.0

            friction = HIGH_FRICTION if self.high_friction > 0 else (
                AIR_FRICTION[SURFACE_ID] if self.z >= WORLD_SCALE else GROUND_FRICTION[SURFACE_ID]
            )
            self.vel *= friction ** tick_scale
            if self.vel.length() < BALL_STOP_SPEED:
                self.vel.update(0, 0)
            remaining -= step

    def draw(self, surface, camera):
        ground = world_to_screen(self.pos, camera)
        shadow_size = clamp(22 - self.z * 0.08, 10, 22)
        shadow_alpha = clamp(150 - self.z * 0.75, 36, 150)
        shadow = pygame.Surface((44, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(
            shadow,
            (*SHADOW, round(shadow_alpha)),
            pygame.Rect(22 - shadow_size, 11 - shadow_size * 0.32, shadow_size * 2, shadow_size * 0.65),
        )
        surface.blit(shadow, shadow.get_rect(center=ground))

        scale = clamp(1.0 + self.z / 120, 1.0, 1.85)
        image = pygame.transform.rotozoom(self.image, pygame.time.get_ticks() * -0.2, scale)
        draw_pos = pygame.Vector2(ground.x, ground.y - self.z)
        surface.blit(image, image.get_rect(center=draw_pos))


class Player:
    def __init__(
        self,
        name,
        team,
        pos,
        images,
        slide_image=None,
        controlled=False,
        keeper=False,
        player_class="Ranger",
        visual=None,
    ):
        self.name = name
        self.team = team
        self.player_class = player_class
        self.pos = pygame.Vector2(pos)
        self.home = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.images = images if isinstance(images, list) else [images]
        self.image = self.images[0]
        self.slide_image = slide_image or self.image
        self.visual = visual
        self.controlled = controlled
        self.keeper = keeper
        self.facing = pygame.Vector2(0, -1 if team == "blue" else 1)
        self.walk_time = random.uniform(0.0, 1.0)
        self.cooldown = 0.0
        self.slide = 0.0
        self.slide_visual = 0.0
        self.slide_visual_duration = 0.0
        self.dive = 0.0
        self.dive_recovery = 0.0
        self.slide_cooldown = 0.0
        self.stun = 0.0
        self.stun_duration = 0.0
        self.anim_time = random.uniform(0.0, 2.0)
        self.anim_surface_cache = {}
        self.ai_react = random.uniform(0.0, 0.25)
        self.ai_decision_timer = random.uniform(AI_REACTION_MIN, AI_REACTION_MAX)
        self.ai_cached_target = pygame.Vector2(pos)
        self.ai_cached_speed = 0.0

    def reset_for_kickoff(self):
        self.pos.update(self.home)
        self.vel.update(0, 0)
        self.facing.update(0, -1 if self.team == "blue" else 1)
        self.walk_time = 0.0
        self.cooldown = 0.0
        self.slide = 0.0
        self.slide_visual = 0.0
        self.slide_visual_duration = 0.0
        self.dive = 0.0
        self.dive_recovery = 0.0
        self.slide_cooldown = 0.0
        self.stun = 0.0
        self.stun_duration = 0.0
        self.anim_time = 0.0
        self.anim_surface_cache.clear()
        self.ai_cached_target.update(self.home)
        self.ai_cached_speed = 0.0

    def has_ball(self, ball):
        return ball.carrier is self

    def stat(self, key):
        return PLAYER_CLASSES.get(self.player_class, PLAYER_CLASSES["Ranger"])[key]

    def visual_scale(self):
        if self.team != "blue" or self.keeper:
            return 1.0
        return self.stat("visual_scale")

    def update(self, dt, ball, keys, players, sprinting=False):
        self.anim_time += dt
        if self.vel.length_squared() > 9 and self.stun <= 0:
            self.walk_time += dt * clamp(self.vel.length() / 140, 0.65, 1.9)
        else:
            self.walk_time = 0.0
        self.cooldown = max(0, self.cooldown - dt)
        self.slide = max(0, self.slide - dt)
        if self.has_ball(ball):
            self.slide_visual = 0.0
        else:
            self.slide_visual = max(0, self.slide_visual - dt)
        self.dive = max(0, self.dive - dt)
        self.dive_recovery = max(0, self.dive_recovery - dt)
        self.slide_cooldown = max(0, self.slide_cooldown - dt)
        self.stun = max(0, self.stun - dt)
        if self.stun <= 0:
            self.stun_duration = 0.0

        if self.keeper and self.dive_recovery > 0:
            self.vel *= 0.78
        elif self.stun > 0:
            self.vel *= 0.82
        elif self.slide > 0:
            self.vel = self.facing * self.stat("slide_speed")
        elif self.controlled:
            move = pygame.Vector2(
                (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0),
                (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0),
            )
            arrow_move = pygame.Vector2(
                (1 if keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_LEFT] else 0),
                (1 if keys[pygame.K_DOWN] else 0) - (1 if keys[pygame.K_UP] else 0),
            )
            move += arrow_move
            move = safe_normalize(move, pygame.Vector2())
            speed = self.stat("run") if not self.has_ball(ball) else self.stat("dribble")
            if sprinting and not self.has_ball(ball):
                speed = self.stat("sprint")
            elif sprinting and self.player_class == "Ranger":
                speed = self.stat("sprint_dribble")
            self.vel = move * speed
            if move.length_squared() > 0:
                self.facing = move
        else:
            self.update_ai(ball, players, dt)

        self.pos += self.vel * dt
        margin = 24
        self.pos.x = clamp(self.pos.x, FIELD.left + margin, FIELD.right - margin)
        self.pos.y = clamp(self.pos.y, FIELD.top + margin, FIELD.bottom - margin)

    def update_ai(self, ball, players, dt):
        attack_dir = -1 if self.team == "blue" else 1
        if self.keeper:
            if self.dive_recovery > 0:
                target = self.pos
            elif self.has_ball(ball):
                self.punt_ball(ball)
                target = self.home
            else:
                target = pygame.Vector2(clamp(ball.pos.x, FIELD.centerx - GOAL_W, FIELD.centerx + GOAL_W), self.home.y)
            if ball.carrier is None and self.pos.distance_to(ball.pos) < 105 and ball.z < 72:
                target = ball.pos
            speed = 220
        elif self.team == "blue":
            lead = next((p for p in players if p.team == "blue" and p.controlled), self)
            follow_offset = clamp(lead.pos.y - lead.home.y, -220, 220)
            target = self.home + pygame.Vector2(0, follow_offset * 0.55)
            speed = 175
        elif self.has_ball(ball):
            target = pygame.Vector2(FIELD.centerx, FIELD.top + 90 if self.team == "blue" else FIELD.bottom - 90)
            speed = 220
        else:
            dist = self.pos.distance_to(ball.pos)
            own_team_has_ball = ball.carrier is not None and ball.carrier.team == self.team
            enemy_has_ball = ball.carrier is not None and ball.carrier.team != self.team
            carrier_is_teammate = own_team_has_ball and ball.carrier is not self
            teammates = [p for p in players if p.team == self.team and not p.keeper]
            closest_on_team = min(
                teammates,
                key=lambda p: p.pos.distance_to(ball.pos),
                default=self,
            )
            closest_to_carrier = None
            carrier_dist = 9999
            if enemy_has_ball:
                carrier_dist = self.pos.distance_to(ball.carrier.pos)
                closest_to_carrier = min(
                    teammates,
                    key=lambda p: p.pos.distance_to(ball.carrier.pos),
                    default=self,
                )
            should_chase = (
                ball.carrier is None
                and closest_on_team is self
                and (dist < 230 or self.team != ball.last_touch)
            )
            may_pressure_carrier = ball.possession_grace <= 0
            if enemy_has_ball and may_pressure_carrier and closest_to_carrier is self:
                target = ball.carrier.pos
                speed = 214
                if ball.possession_grace <= 0 and carrier_dist < 58 and self.slide_cooldown <= 0 and random.random() < 0.35:
                    self.facing = safe_normalize(ball.carrier.pos - self.pos, self.facing)
                    self.start_slide()
            elif enemy_has_ball:
                shape_offset = clamp(ball.carrier.pos.y - ball.carrier.home.y, -190, 190)
                target = self.home + pygame.Vector2(0, shape_offset * 0.45)
                speed = 172
            elif carrier_is_teammate:
                support = pygame.Vector2(self.home.x, self.home.y + attack_dir * 115)
                target = support
                speed = 190
            elif should_chase:
                target = ball.pos
                speed = 216
            else:
                target = self.home
                speed = 180

        self.ai_cached_target = pygame.Vector2(target)
        self.ai_cached_speed = speed
        target = self.ai_cached_target
        speed = self.ai_cached_speed

        desired = target - self.pos
        if desired.length_squared() < 64:
            self.vel.update(0, 0)
        else:
            self.vel = safe_normalize(desired, pygame.Vector2()) * min(speed, desired.length() * 4)
        if self.vel.length_squared() > 1:
            self.facing = self.vel.normalize()

        if self.team == "blue" and not self.controlled and not self.keeper:
            return

        if self.cooldown <= 0:
            if ball.carrier is None and ball.can_be_collected() and self.pos.distance_to(ball.pos) < PICKUP_RADIUS:
                ball.collect(self)
            elif self.has_ball(ball):
                goal = pygame.Vector2(FIELD.centerx, FIELD.top - 80 if self.team == "blue" else FIELD.bottom + 80)
                if self.pos.distance_to(goal) < 520 or random.random() < 0.006:
                    speed, lift, high_friction = kickabout_impulse(random.uniform(96, 256), high=False, special_low=self.player_class == "Hotshot")
                    ball.release(add_aim_error(goal - self.pos, AI_SHOT_ERROR_DEGREES), speed, lift, self.team, high_friction=high_friction)
                    self.cooldown = 0.55
            elif (
                self.pos.distance_to(ball.pos) < 42
                and 30 <= ball.z <= 125
                and not (
                    ball.protected_clearance_team is not None
                    and ball.protected_clearance_team != self.team
                )
            ):
                goal = pygame.Vector2(FIELD.centerx, FIELD.top - 80 if self.team == "blue" else FIELD.bottom + 80)
                speed, lift, _ = kickabout_impulse(160, high=ball.z > 60, special_low=False)
                ball.release(add_aim_error(goal - self.pos, AI_SHOT_ERROR_DEGREES), speed, lift, self.team)
                self.cooldown = 0.65

    def start_slide(self):
        if self.slide_cooldown > 0 or self.stun > 0:
            return False
        self.slide = 0.28
        self.slide_visual = 0.58
        self.slide_visual_duration = self.slide_visual
        self.slide_cooldown = 0.9
        self.cooldown = 0.22
        return True

    def attacking_goal(self):
        return pygame.Vector2(FIELD.centerx, FIELD.top if self.team == "blue" else FIELD.bottom)

    def near_attacking_goal(self):
        goal = self.attacking_goal()
        return self.pos.distance_to(goal) < 430 or ball_side_near_goal(self.pos, self.team)

    def punt_ball(self, ball):
        attack_dir = -1 if self.team == "blue" else 1
        punt_dir = pygame.Vector2(random.uniform(-0.18, 0.18), attack_dir)
        speed, lift, _ = kickabout_impulse(220, high=True, special_low=False)
        ball.release(punt_dir, speed, lift, self.team, uncatchable=BALL_UNCATCHABLE_HIGH)
        ball.clearance_grace = 8.0
        ball.protected_clearance_team = self.team
        self.cooldown = 0.9
        return None

    def pass_ball(self, ball, players, target=None, charge=0.0):
        if not self.has_ball(ball):
            return None
        direction = self.facing if target is None else target - self.pos
        self.facing = safe_normalize(direction, self.facing)
        power_value = charge * 256
        speed, lift, high_friction = kickabout_impulse(
            power_value,
            high=False,
            special_low=self.player_class == "Hotshot",
        )
        ball.release(
            direction,
            speed * self.stat("shot_power"),
            lift,
            self.team,
            uncatchable=BALL_UNCATCHABLE_LOW,
            high_friction=high_friction,
        )
        self.cooldown = 0.25
        return None

    def shoot_ball(self, ball, charge, target=None):
        if not self.has_ball(ball):
            return None
        target = target or pygame.Vector2(FIELD.centerx, FIELD.top - 120 if self.team == "blue" else FIELD.bottom + 120)
        self.facing = safe_normalize(target - self.pos, self.facing)
        power_value = charge * 256
        speed, lift, high_friction = kickabout_impulse(power_value, high=True, special_low=False)
        ball.release(
            target - self.pos,
            speed * self.stat("shot_power"),
            lift,
            self.team,
            uncatchable=BALL_UNCATCHABLE_HIGH,
            high_friction=high_friction,
        )
        self.cooldown = 0.35
        return None

    def chip_ball(self, ball):
        if not self.has_ball(ball):
            return None
        ball.release(self.facing, 355, 455, self.team)
        self.cooldown = 0.42
        return "CHIP"

    def low_strike(self, ball, charge, target=None):
        if self.cooldown > 0 or ball.carrier is not None or ball.z > 52:
            return None
        target = target or self.pos + self.facing
        self.facing = safe_normalize(target - self.pos, self.facing)
        to_ball = ball.pos - self.pos
        forward = to_ball.dot(self.facing)
        lane_distance = (ball.pos - (self.pos + self.facing * max(0, forward))).length()
        reach = (88 + 48 * charge) * self.stat("tackle_range")
        if self.near_attacking_goal():
            reach += 32
        if self.pos.distance_to(ball.pos) > reach and not (0 <= forward <= reach + 34 and lane_distance < 48):
            return None
        if self.start_slide():
            self.pos += safe_normalize(ball.pos - self.pos, self.facing) * min(34, self.pos.distance_to(ball.pos) * 0.45)
            power_value = charge * 256
            speed, lift, high_friction = kickabout_impulse(
                power_value,
                high=False,
                special_low=self.player_class == "Hotshot",
            )
            ball.release(
                target - self.pos,
                speed * self.stat("tackle_power"),
                lift,
                self.team,
                uncatchable=BALL_UNCATCHABLE_LOW,
                high_friction=high_friction,
            )
            self.cooldown = 0.32
            return None
        return None

    def aerial(self, ball, target=None, charge=0.0):
        if self.cooldown > 0 or ball.carrier is not None:
            return None
        if ball.protected_clearance_team is not None and ball.protected_clearance_team != self.team:
            return None
        near_goal = self.near_attacking_goal()
        reach = (74 + 34 * charge) * self.stat("aerial_range")
        if near_goal:
            reach = (155 + 65 * charge) * self.stat("aerial_range")
        if self.pos.distance_to(ball.pos) > reach:
            return None
        target = target or pygame.Vector2(FIELD.centerx, FIELD.top - 120 if self.team == "blue" else FIELD.bottom + 120)
        direction = safe_normalize(target - self.pos, self.facing)
        if 48 <= ball.z <= 155:
            self.pos += safe_normalize(ball.pos - self.pos, self.facing) * min(52 if near_goal else 28, self.pos.distance_to(ball.pos) * 0.55)
            power_value = charge * 256
            speed, lift, _ = kickabout_impulse(power_value, high=False, special_low=False)
            ball.release(direction, speed * self.stat("aerial_power"), lift, self.team)
            self.cooldown = 0.48
            return None
        if 12 <= ball.z < 70:
            self.pos += safe_normalize(ball.pos - self.pos, self.facing) * min(42 if near_goal else 24, self.pos.distance_to(ball.pos) * 0.45)
            power_value = charge * 256
            speed, lift, _ = kickabout_impulse(power_value, high=False, special_low=False)
            ball.release(direction, speed * 1.08, lift, self.team)
            self.cooldown = 0.48
            return None
        return None

    def animation_state(self, ball, animation_db):
        if self.stun > 0:
            elapsed = max(0, self.stun_duration - self.stun)
            getup_duration = sequence_duration(animation_db, ANIM_GET_UP) or 0.7
            if self.stun_duration and self.stun <= getup_duration:
                return ANIM_GET_UP, max(0, getup_duration - self.stun), False
            return ANIM_TACKLED, elapsed, False
        if self.slide > 0 or self.slide_visual > 0:
            slide_left = max(self.slide, self.slide_visual)
            elapsed = max(0, self.slide_visual_duration - slide_left)
            return ANIM_SLIDE, elapsed, False
        if self.vel.length_squared() <= 9:
            return ANIM_IDLE, self.anim_time, True
        return ANIM_POSSESS, self.anim_time, True

    def animated_image(self, animation_db, sequence_id, elapsed, loop):
        if not self.visual or not animation_db:
            return None
        frame_index = sequence_frame(animation_db, sequence_id, elapsed, loop)
        if frame_index is None:
            return None
        heading_index = direction_frame_index(self.facing, len(self.visual.frames))
        cache_key = (sequence_id, frame_index, heading_index)
        cached = self.anim_surface_cache.get(cache_key)
        if cached is not None:
            return cached
        mesh = animated_mesh_for_frame(self.visual.mesh, animation_db, frame_index)
        image = render_mesh(
            mesh,
            render_yaw_for_frame(heading_index),
            color_map=self.visual.color_map,
        )
        if len(self.anim_surface_cache) >= 384:
            self.anim_surface_cache.clear()
        self.anim_surface_cache[cache_key] = image
        return image

    def draw(self, surface, camera, ball=None, animation_db=None):
        pos = world_to_screen(self.pos, camera)
        if pos.x < -140 or pos.x > SCREEN_W + 140 or pos.y < -190 or pos.y > SCREEN_H + 90:
            return
        directional = len(self.images) > 1
        animation_state = self.animation_state(ball, animation_db) if ball is not None else None
        animated = self.animated_image(animation_db, *animation_state) if animation_state is not None else None
        if animated is not None:
            image = animated
            center = (pos.x, pos.y - 54)
        elif directional:
            frames = self.slide_image if (self.slide_visual > 0 or self.dive > 0 or self.dive_recovery > 0) else self.images
            if not isinstance(frames, list):
                frames = self.images
            image = frames[direction_frame_index(self.facing, len(frames))]
            center = (pos.x, pos.y - 54)
        else:
            angle = -math.degrees(math.atan2(self.facing.x, -self.facing.y)) + SPRITE_FACING_OFFSET
            if self.slide_visual > 0 or self.dive > 0 or self.dive_recovery > 0:
                image = pygame.transform.rotozoom(self.slide_image, angle, self.visual_scale())
            else:
                image = pygame.transform.rotozoom(self.image, angle, self.visual_scale())
            center = pos
        rect = image.get_rect(center=center)
        shadow_w = 38 if directional else 30
        pygame.draw.ellipse(surface, (0, 0, 0, 55), (pos.x - shadow_w / 2, pos.y + 13, shadow_w, 11))
        if self.controlled:
            marker_y = rect.top - 10
            points = [
                (pos.x, marker_y + 12),
                (pos.x - 9, marker_y),
                (pos.x + 9, marker_y),
            ]
            pygame.draw.polygon(surface, YELLOW, points)
            pygame.draw.polygon(surface, INK, points, 2)
            pygame.draw.circle(surface, YELLOW, (round(pos.x), round(pos.y + 20)), 24, 3)
        surface.blit(image, rect)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Kickabout 2.5D Prototype")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.small = pygame.font.SysFont("arial", 16, bold=True)
        self.animation_db = load_animation_database()
        self.assets = self.load_assets()
        self.choosing_formation = True
        self.reset()

    def load_assets(self):
        blue_frames = load_character_frames("Blue", frames=(1,))
        red_frames = load_character_frames("Red", frames=(1,))
        white = load_character("White", 1)
        white_slide = load_character("White", 11, 2.45)
        assets = {
            "ball": load_image(ASSETS / "Equipment" / "ball_soccer1.png", 1.35),
            "blue": blue_frames,
            "blue_slide": load_character("Blue", 11, 2.45),
            "hotshot": blue_frames,
            "hotshot_slide": load_character("Blue", 11, 2.45),
            "ranger": blue_frames,
            "ranger_slide": load_character("Blue", 11, 2.45),
            "tank": blue_frames,
            "tank_slide": load_character("Blue", 11, 2.45),
            "red": red_frames,
            "red_slide": load_character("Red", 11, 2.45),
            "white": white,
            "white_slide": white_slide,
            "blue_keeper": blue_frames,
            "blue_keeper_slide": load_character("Blue", 11, 2.45),
            "red_keeper": red_frames,
            "red_keeper_slide": load_character("Red", 11, 2.45),
            "special": load_character("Special", 1),
            "special_slide": load_character("Special", 11, 2.45),
        }
        for name, (prefix, class_id, primary, secondary, keeper) in VN_CLASS_ASSETS.items():
            key = PLAYER_CLASSES[name]["asset"] if name in PLAYER_CLASSES else "keeper"
            variants = []
            red_variants = []
            for _, head_index, body_base_color in HEAD_VARIANTS[class_id]:
                try:
                    frames, mesh, color_map = load_player_surfaces(prefix, head_index, body_base_color, primary, secondary, keeper)
                except Exception:
                    continue
                variants.append(VNVisual(frames, mesh, color_map))
                if name in PLAYER_CLASSES:
                    try:
                        red_frames, red_mesh, red_color_map = load_player_surfaces(prefix, head_index, body_base_color, 16, 31, keeper)
                    except Exception:
                        red_frames = frames
                        red_mesh = mesh
                        red_color_map = color_map
                    red_variants.append(VNVisual(red_frames, red_mesh, red_color_map))
            if not variants:
                continue
            assets[f"{key}_variants"] = variants
            assets[key] = variants[0].frames
            assets[f"{key}_slide"] = variants[0].frames
            if name in PLAYER_CLASSES:
                assets[f"red_{key}_variants"] = red_variants or variants
                assets[f"red_{key}"] = (red_variants or variants)[0].frames
                assets[f"red_{key}_slide"] = (red_variants or variants)[0].frames
            if name == "Keeper":
                assets["blue_keeper_variants"] = variants
                assets["red_keeper_variants"] = variants
                assets["blue_keeper"] = variants[0].frames
                assets["blue_keeper_slide"] = variants[0].frames
                assets["red_keeper"] = variants[0].frames
                assets["red_keeper_slide"] = variants[0].frames
        return assets

    def random_visual(self, key):
        variants = self.assets.get(f"{key}_variants")
        if variants:
            return random.choice(variants)
        return None

    def player_visual_assets(self, player_class, team):
        asset = PLAYER_CLASSES[player_class]["asset"]
        key = asset if team == "blue" else f"red_{asset}"
        fallback = asset if team == "blue" else "red"
        visual = self.random_visual(key)
        frames = visual.frames if visual else self.assets[fallback]
        return frames, frames, visual

    def keeper_visual_assets(self, team):
        key = f"{team}_keeper"
        visual = self.random_visual(key)
        frames = visual.frames if visual else self.assets[key]
        return frames, frames, visual

    def reset(self):
        self.ball = Ball(self.assets["ball"])
        self.formation_index = getattr(self, "formation_index", 0)
        self.class_choices = getattr(self, "class_choices", ["Hotshot", "Ranger", "Tank", "Ranger"])
        self.selected_class_slot = getattr(self, "selected_class_slot", 0)
        self.enemy_formation_index = random.randrange(len(FORMATION_NAMES))
        cx = FIELD.centerx
        blue_assets = []
        for player_class in self.class_choices:
            frames, slide_frames, visual = self.player_visual_assets(player_class, "blue")
            blue_assets.append((frames, slide_frames, visual, player_class))
        blue_keeper, blue_keeper_slide, blue_keeper_visual = self.keeper_visual_assets("blue")
        red_keeper, red_keeper_slide, red_keeper_visual = self.keeper_visual_assets("red")
        red_hotshot, red_hotshot_slide, red_hotshot_visual = self.player_visual_assets("Hotshot", "red")
        red_ranger_a, red_ranger_a_slide, red_ranger_a_visual = self.player_visual_assets("Ranger", "red")
        red_tank, red_tank_slide, red_tank_visual = self.player_visual_assets("Tank", "red")
        red_ranger_b, red_ranger_b_slide, red_ranger_b_visual = self.player_visual_assets("Ranger", "red")
        self.players = [
            Player("Blue 1", "blue", (cx, FIELD.centery + 170), blue_assets[0][0], blue_assets[0][1], controlled=True, player_class=blue_assets[0][3], visual=blue_assets[0][2]),
            Player("Blue 2", "blue", (cx - 190, FIELD.centery + 330), blue_assets[1][0], blue_assets[1][1], player_class=blue_assets[1][3], visual=blue_assets[1][2]),
            Player("Blue 3", "blue", (cx + 190, FIELD.centery + 330), blue_assets[2][0], blue_assets[2][1], player_class=blue_assets[2][3], visual=blue_assets[2][2]),
            Player("Blue 4", "blue", (cx, FIELD.centery + 520), blue_assets[3][0], blue_assets[3][1], player_class=blue_assets[3][3], visual=blue_assets[3][2]),
            Player("Blue GK", "blue", (cx, FIELD.bottom - 60), blue_keeper, blue_keeper_slide, keeper=True, visual=blue_keeper_visual),
            Player("Red 1", "red", (cx, FIELD.centery - 170), red_hotshot, red_hotshot_slide, player_class="Hotshot", visual=red_hotshot_visual),
            Player("Red 2", "red", (cx - 190, FIELD.centery - 330), red_ranger_a, red_ranger_a_slide, player_class="Ranger", visual=red_ranger_a_visual),
            Player("Red 3", "red", (cx + 190, FIELD.centery - 330), red_tank, red_tank_slide, player_class="Tank", visual=red_tank_visual),
            Player("Red 4", "red", (cx, FIELD.centery - 520), red_ranger_b, red_ranger_b_slide, player_class="Ranger", visual=red_ranger_b_visual),
            Player("Red GK", "red", (cx, FIELD.top + 60), red_keeper, red_keeper_slide, keeper=True, visual=red_keeper_visual),
        ]
        self.apply_formation()
        self.controlled_index = 0
        self.score = {"blue": 0, "red": 0}
        self.bursts = []
        self.timer = 180.0
        self.match_over = False
        self.paused_goal = 0.0
        self.camera = pygame.Vector2(0, 0)
        self.shoot_charge = 0.0
        self.pass_charge = 0.0
        self.shoot_charge_elapsed = 0.0
        self.pass_charge_elapsed = 0.0
        self.charging = False
        self.pass_charging = False
        self.defense_slide_charging = False
        self.sprint_key_down = False
        self.manual_switch_lock = 0.0
        self.formation_nav_cooldown = 0.0
        self.formation_prev_button = pygame.Rect(0, 0, 0, 0)
        self.formation_next_button = pygame.Rect(0, 0, 0, 0)
        self.formation_slot_buttons = []
        self.class_button_rects = {}
        self.ball.reset(direction=1)

    def current_formation_name(self):
        return FORMATION_NAMES[self.formation_index]

    def enemy_formation_name(self):
        return FORMATION_NAMES[self.enemy_formation_index]

    def formation_position(self, team, slot):
        name = self.current_formation_name() if team == "blue" else self.enemy_formation_name()
        x_ratio, y_ratio = FORMATIONS[name][team][slot]
        return pygame.Vector2(
            FIELD.centerx + x_ratio * FIELD.width,
            FIELD.centery + y_ratio * FIELD.height,
        )

    def apply_formation(self):
        slots = {"blue": 0, "red": 0}
        for player in self.players:
            if player.keeper:
                player.home.update(FIELD.centerx, FIELD.bottom - 60 if player.team == "blue" else FIELD.top + 60)
                continue
            slot = slots[player.team]
            slots[player.team] += 1
            player.home = self.formation_position(player.team, slot)
            if not player.controlled and not player.has_ball(self.ball):
                player.pos.update(player.home)

    def reset_players_for_kickoff(self):
        for player in self.players:
            player.reset_for_kickoff()
        self.players[self.controlled_index].controlled = False
        self.controlled_index = 0
        self.players[self.controlled_index].controlled = True

    def set_formation(self, index):
        self.formation_index = index % len(FORMATION_NAMES)
        self.apply_formation()
        self.add_burst(self.current_formation_name().upper(), self.hero.pos)

    def preview_formation(self, delta):
        self.formation_index = (self.formation_index + delta) % len(FORMATION_NAMES)
        self.apply_formation()
        self.bursts.clear()
        self.formation_nav_cooldown = 0.18

    def apply_class_choices(self):
        blue_players = [p for p in self.players if p.team == "blue" and not p.keeper]
        for player, player_class in zip(blue_players, self.class_choices):
            frames, slide_frames, visual = self.player_visual_assets(player_class, "blue")
            player.player_class = player_class
            player.images = frames
            player.image = player.images[0]
            player.slide_image = slide_frames
            player.visual = visual
            player.anim_surface_cache.clear()

    def set_slot_class(self, slot, player_class):
        if not 0 <= slot < len(self.class_choices):
            return
        self.selected_class_slot = slot
        self.class_choices[slot] = player_class
        self.apply_class_choices()

    def cycle_slot_class(self, slot):
        if not 0 <= slot < len(self.class_choices):
            return
        current = PLAYER_CLASS_ORDER.index(self.class_choices[slot])
        self.set_slot_class(slot, PLAYER_CLASS_ORDER[(current + 1) % len(PLAYER_CLASS_ORDER)])

    def choose_formation(self, index):
        self.set_formation(index)
        self.choosing_formation = False
        self.bursts.clear()
        self.timer = 180.0
        self.ball.reset(direction=1)
        self.reset_players_for_kickoff()
        self.update_camera(0)

    @property
    def hero(self):
        return self.players[self.controlled_index]

    def controllable_blue_indices(self):
        return [i for i, p in enumerate(self.players) if p.team == "blue" and not p.keeper]

    def add_burst(self, text, pos, color=YELLOW):
        if not text:
            return
        self.bursts.append(Burst(text, pygame.Vector2(pos.x, pos.y - 46), color))

    def mouse_world(self, pos=None):
        return screen_to_world(pos or pygame.mouse.get_pos(), self.camera)

    def update_hero_mouse_aim(self, pos=None):
        if self.charging or self.pass_charging:
            target = self.mouse_world(pos)
            self.hero.facing = safe_normalize(target - self.hero.pos, self.hero.facing)

    def pass_target_from_mouse(self, pos=None):
        target = self.mouse_world(pos)
        origin = self.hero.pos
        aim = safe_normalize(target - origin, self.hero.facing)
        teammates = [
            p for p in self.players
            if p.team == "blue" and not p.keeper and p is not self.hero and p.stun <= 0
        ]
        if not teammates:
            return target

        best_player = None
        best_score = float("inf")
        for player in teammates:
            to_player = player.pos - origin
            forward = to_player.dot(aim)
            if forward <= -30:
                continue
            projected = origin + aim * max(0, forward)
            lane_distance = player.pos.distance_to(projected)
            mouse_distance = player.pos.distance_to(target)
            score = lane_distance * 1.35 + mouse_distance * 0.25
            if score < best_score:
                best_score = score
                best_player = player

        if best_player is None:
            best_player = min(teammates, key=lambda p: p.pos.distance_to(target))
        return best_player.pos

    def switch_player(self):
        blue_players = self.controllable_blue_indices()
        current_slot = blue_players.index(self.controlled_index) if self.controlled_index in blue_players else -1
        self.players[self.controlled_index].controlled = False
        if self.ball.carrier and self.ball.carrier.team == "blue" and not self.ball.carrier.keeper:
            self.controlled_index = self.players.index(self.ball.carrier)
        else:
            ordered = sorted(blue_players, key=lambda i: self.players[i].pos.distance_to(self.ball.pos))
            self.controlled_index = ordered[0] if ordered[0] != self.controlled_index else blue_players[(current_slot + 1) % len(blue_players)]
        self.players[self.controlled_index].controlled = True

    def switch_to_closest_to_ball(self):
        blue_players = self.controllable_blue_indices()
        self.players[self.controlled_index].controlled = False
        self.controlled_index = min(blue_players, key=lambda i: self.players[i].pos.distance_to(self.ball.pos))
        self.players[self.controlled_index].controlled = True

    def set_controlled_player(self, index, announce=False):
        if index == self.controlled_index:
            return
        self.players[self.controlled_index].controlled = False
        self.controlled_index = index
        self.players[self.controlled_index].controlled = True

    def auto_select_defender(self):
        if self.ball.carrier and self.ball.carrier.team == "blue":
            if not self.ball.carrier.keeper:
                self.set_controlled_player(self.players.index(self.ball.carrier))
            return
        if self.charging or self.pass_charging or self.manual_switch_lock > 0:
            return
        blue_players = self.controllable_blue_indices()
        closest = min(blue_players, key=lambda i: self.players[i].pos.distance_to(self.ball.pos))
        self.set_controlled_player(closest)

    def cycle_nearest_defenders(self):
        if self.ball.carrier and self.ball.carrier.team == "blue":
            return False
        ordered = sorted(self.controllable_blue_indices(), key=lambda i: self.players[i].pos.distance_to(self.ball.pos))
        choices = ordered[:2]
        if not choices:
            return False
        next_index = choices[1] if self.controlled_index == choices[0] and len(choices) > 1 else choices[0]
        self.set_controlled_player(next_index, announce=True)
        self.manual_switch_lock = 0.55
        return True

    def switch_to_mouse_target(self, pos=None):
        if self.ball.carrier and self.ball.carrier.team == "blue":
            return False
        target = self.mouse_world(pos)
        candidates = self.controllable_blue_indices()
        if not candidates:
            return False
        index = min(candidates, key=lambda i: self.players[i].pos.distance_to(target))
        self.set_controlled_player(index, announce=True)
        self.manual_switch_lock = 0.55
        return True

    def update_camera(self, dt):
        target = self.ball.pos - pygame.Vector2(SCREEN_W / 2, SCREEN_H / 2)
        target.x = clamp(target.x, FIELD.left - 100, FIELD.right - SCREEN_W + 100)
        target.y = clamp(target.y, FIELD.top - 76, FIELD.bottom - SCREEN_H + 100)
        self.camera.update(target)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        if self.choosing_formation:
            self.formation_nav_cooldown = max(0, self.formation_nav_cooldown - dt)
            if self.formation_nav_cooldown <= 0:
                if keys[pygame.K_LEFT]:
                    self.preview_formation(-1)
                elif keys[pygame.K_RIGHT]:
                    self.preview_formation(1)
            self.update_camera(dt)
            return

        if self.match_over:
            for burst in self.bursts:
                burst.update(dt)
            self.bursts = [burst for burst in self.bursts if burst.ttl > 0]
            self.update_camera(dt)
            return

        self.timer = max(0, self.timer - dt)
        if self.timer <= 0:
            self.match_over = True
            self.charging = False
            self.pass_charging = False
            self.defense_slide_charging = False
            self.shoot_charge = 0.0
            self.pass_charge = 0.0
            self.shoot_charge_elapsed = 0.0
            self.pass_charge_elapsed = 0.0
            self.update_camera(dt)
            return

        if self.charging:
            self.shoot_charge_elapsed += dt
            self.shoot_charge = kickabout_power_from_charge(
                self.shoot_charge_elapsed,
                self.hero.stat("charge_stat"),
            ) / 256
        if self.pass_charging:
            self.pass_charge_elapsed += dt
            self.pass_charge = kickabout_power_from_charge(
                self.pass_charge_elapsed,
                self.hero.stat("charge_stat"),
            ) / 256
        self.manual_switch_lock = max(0, self.manual_switch_lock - dt)

        if self.paused_goal > 0:
            self.paused_goal -= dt
            if self.paused_goal <= 0:
                direction = 1 if self.ball.pos.y < FIELD.centery else -1
                self.ball.reset(direction)
                self.reset_players_for_kickoff()
            self.update_camera(dt)
            return

        for player in self.players:
            player.update(dt, self.ball, keys, self.players, self.sprint_key_down and player.controlled)

        self.update_hero_mouse_aim()
        self.ball.update(dt)
        self.auto_collect_ball()
        self.resolve_keeper_saves()
        self.resolve_body_contacts()
        self.resolve_slide_tackles()
        self.check_goal()

        for burst in self.bursts:
            burst.update(dt)
        self.bursts = [burst for burst in self.bursts if burst.ttl > 0]
        self.update_camera(dt)

    def auto_collect_ball(self):
        if self.pass_charging or self.charging:
            return
        if not self.ball.can_be_collected():
            return
        candidates = sorted(self.players, key=lambda p: p.pos.distance_to(self.ball.pos))
        for player in candidates:
            collect_radius = PICKUP_RADIUS
            if player.keeper:
                collect_radius = max(8, (20 - round(player.dive * TICK_RATE)) * WORLD_SCALE)
            if player.pos.distance_to(self.ball.pos) < collect_radius and player.stun <= 0:
                self.ball.collect(player)
                if player.keeper:
                    player.punt_ball(self.ball)
                elif player.team == "blue":
                    self.players[self.controlled_index].controlled = False
                    self.controlled_index = self.players.index(player)
                    player.controlled = True
                return

    def resolve_body_contacts(self):
        if self.ball.carrier or self.ball.z > 18:
            return
        for player in self.players:
            if player.team == "blue" and not player.controlled and not player.keeper:
                continue
            delta = self.ball.pos - player.pos
            dist = delta.length()
            if 0 < dist < PLAYER_R + BALL_R:
                normal = delta / dist
                self.ball.pos = player.pos + normal * (PLAYER_R + BALL_R)
                self.ball.vel += normal * 65

    def resolve_keeper_saves(self):
        if self.ball.carrier or abs(self.ball.vel.y) <= 0 or self.ball.z > 170:
            return
        for keeper in (p for p in self.players if p.keeper and p.stun <= 0 and p.dive_recovery <= 0):
            goal_y = FIELD.bottom if keeper.team == "blue" else FIELD.top
            moving_toward_goal = self.ball.vel.y > 90 if keeper.team == "blue" else self.ball.vel.y < -90
            if not moving_toward_goal:
                continue

            ticks = ((keeper.pos.y - self.ball.pos.y) / self.ball.vel.y) * TICK_RATE
            ticks = 9 * ticks / 4
            window = 20 - round(keeper.dive * TICK_RATE / 2)
            if ticks <= 2 or ticks >= window:
                continue
            time_to_line = ticks / TICK_RATE
            projected_x = self.ball.pos.x + self.ball.vel.x * time_to_line + random.uniform(-AI_KEEPER_ERROR, AI_KEEPER_ERROR)
            if not (FIELD.centerx - GOAL_W <= projected_x <= FIELD.centerx + GOAL_W):
                continue

            target_x = clamp(projected_x, FIELD.centerx - GOAL_W, FIELD.centerx + GOAL_W)
            lateral_gap = target_x - keeper.pos.x
            easy_reach = abs(lateral_gap) < 32 * WORLD_SCALE and self.ball.z < 48 and self.ball.vel.length() < 500
            if easy_reach:
                self.ball.collect(keeper)
                return

            must_dive = self.ball.vel.length() > 700 or self.ball.z >= 58 or abs(lateral_gap) > 36 * WORLD_SCALE
            if not must_dive:
                continue
            if abs(lateral_gap) > 170 * WORLD_SCALE:
                continue

            keeper.facing = pygame.Vector2(1 if lateral_gap >= 0 else -1, 0)
            keeper.dive = 0.42
            keeper.dive_recovery = 2.4
            keeper.pos.x += keeper.facing.x * min(58, abs(lateral_gap) * 0.58)
            keeper.pos.x = clamp(keeper.pos.x, FIELD.centerx - GOAL_W - 70, FIELD.centerx + GOAL_W + 70)

            if abs(keeper.pos.x - projected_x) < 68:
                away_x = 1 if projected_x >= keeper.pos.x else -1
                self.ball.carrier = None
                self.ball.last_touch = keeper.team
                self.ball.vel.update(away_x * 150, 0)
                self.ball.vz = min(self.ball.vz, -80)
                self.ball.z = max(self.ball.z, 28)
                self.ball.clearance_grace = 0.0
                self.ball.protected_clearance_team = None
                return

    def flatten_player(self, tackler, victim, take_ball=False):
        victim.stun = 2.0
        victim.stun_duration = victim.stun
        victim.anim_time = 0.0
        victim.slide = 0.0
        victim.slide_visual = 0.58
        victim.slide_cooldown = 2.2
        victim.cooldown = 2.0
        victim.vel = tackler.facing * 120
        if take_ball:
            self.ball.collect(tackler)

    def resolve_slide_tackles(self):
        tacklers = [p for p in self.players if p.slide > 0]
        for tackler in tacklers:
            hit_player = False
            if self.ball.carrier and self.ball.carrier.team != tackler.team:
                carrier = self.ball.carrier
                if not carrier.keeper and tackler.pos.distance_to(carrier.pos) < SLIDE_TACKLE_PLAYER_RANGE:
                    self.flatten_player(tackler, carrier, take_ball=True)
                    hit_player = True

            if not hit_player:
                opponents = [
                    p for p in self.players
                    if p.team != tackler.team and not p.keeper and p.stun <= 0
                ]
                for victim in sorted(opponents, key=lambda p: p.pos.distance_to(tackler.pos)):
                    offset = victim.pos - tackler.pos
                    if offset.length() >= SLIDE_TACKLE_PLAYER_RANGE:
                        continue
                    if offset.length_squared() > 0 and offset.dot(tackler.facing) < -12:
                        continue
                    self.flatten_player(tackler, victim, take_ball=self.ball.carrier is victim)
                    hit_player = True
                    break

            if not hit_player and self.ball.carrier is None and self.ball.z < 22 and tackler.pos.distance_to(self.ball.pos) < 42:
                self.ball.collect(tackler)

    def check_goal(self):
        in_goal_mouth = FIELD.centerx - GOAL_W <= self.ball.pos.x <= FIELD.centerx + GOAL_W
        if self.ball.carrier is not None:
            return
        if in_goal_mouth and self.ball.pos.y < FIELD.top:
            self.score["blue"] += 1
            self.add_burst("GOAL BLUE", pygame.Vector2(FIELD.centerx, FIELD.top + 70), BLUE)
            self.paused_goal = 1.2
            self.ball.uncatchable = 205 / TICK_RATE
        elif in_goal_mouth and self.ball.pos.y > FIELD.bottom:
            self.score["red"] += 1
            self.add_burst("GOAL RED", pygame.Vector2(FIELD.centerx, FIELD.bottom - 70), RED)
            self.paused_goal = 1.2
            self.ball.uncatchable = 205 / TICK_RATE

    def handle_keydown(self, key):
        result = None
        if self.match_over:
            if key == pygame.K_r:
                self.reset()
                self.choosing_formation = True
            return

        if self.choosing_formation:
            if pygame.K_1 <= key <= pygame.K_5:
                self.choose_formation(key - pygame.K_1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.preview_formation(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.preview_formation(1)
            elif key == pygame.K_TAB:
                self.selected_class_slot = (self.selected_class_slot + 1) % len(self.class_choices)
            elif key == pygame.K_h:
                self.set_slot_class(self.selected_class_slot, "Hotshot")
            elif key == pygame.K_t:
                self.set_slot_class(self.selected_class_slot, "Tank")
            elif key == pygame.K_r:
                self.set_slot_class(self.selected_class_slot, "Ranger")
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose_formation(self.formation_index)
            elif key == pygame.K_BACKSPACE:
                self.reset()
            return

        if key in (pygame.K_SPACE, pygame.K_LCTRL, pygame.K_RCTRL):
            self.sprint_key_down = True
        elif pygame.K_1 <= key <= pygame.K_5:
            self.set_formation(key - pygame.K_1)
        elif key == pygame.K_r:
            self.reset()
            self.choosing_formation = True

        if result:
            self.add_burst(result, self.hero.pos)

    def handle_keyup(self, key):
        if key in (pygame.K_SPACE, pygame.K_LCTRL, pygame.K_RCTRL):
            self.sprint_key_down = False

    def handle_mouse_down(self, button, pos=None):
        if self.match_over:
            return

        if self.choosing_formation:
            if button == 1:
                pos = pos or pygame.mouse.get_pos()
                if self.formation_prev_button.collidepoint(pos):
                    self.preview_formation(-1)
                elif self.formation_next_button.collidepoint(pos):
                    self.preview_formation(1)
                else:
                    for slot, rect in enumerate(self.formation_slot_buttons):
                        if rect.collidepoint(pos):
                            self.cycle_slot_class(slot)
                            return
                    for player_class, rect in self.class_button_rects.items():
                        if rect.collidepoint(pos):
                            self.set_slot_class(self.selected_class_slot, player_class)
                            return
            return

        result = None
        if button == 1:
            self.update_hero_mouse_aim(pos)
            if self.hero.has_ball(self.ball):
                self.pass_charging = True
                self.pass_charge = 0.0
                self.pass_charge_elapsed = 0.0
            elif self.ball.z > 45:
                self.pass_charging = True
                self.pass_charge = 0.0
                self.pass_charge_elapsed = 0.0
            else:
                result = self.hero.low_strike(self.ball, 0.0, self.mouse_world(pos))
                if result is None:
                    self.hero.start_slide()
                self.defense_slide_charging = True
        elif button == 3:
            self.update_hero_mouse_aim(pos)
            if self.hero.has_ball(self.ball):
                self.charging = True
                self.shoot_charge = 0.0
                self.shoot_charge_elapsed = 0.0
            else:
                self.switch_to_mouse_target(pos)

        if result:
            self.add_burst(result, self.hero.pos)

    def handle_mouse_up(self, button, pos=None):
        if self.match_over:
            return

        if button == 1 and self.pass_charging:
            self.update_hero_mouse_aim(pos)
            if self.hero.has_ball(self.ball):
                result = self.hero.pass_ball(self.ball, self.players, self.mouse_world(pos), self.pass_charge)
            elif self.ball.z > 45:
                result = self.hero.aerial(self.ball, self.mouse_world(pos), self.pass_charge)
            else:
                result = self.hero.low_strike(self.ball, self.pass_charge, self.mouse_world(pos))
            if result:
                self.add_burst(result, self.hero.pos)
            self.pass_charging = False
            self.pass_charge = 0.0
            self.pass_charge_elapsed = 0.0

        if button == 1 and self.defense_slide_charging:
            self.defense_slide_charging = False

        if button == 3 and self.charging:
            self.update_hero_mouse_aim(pos)
            if self.hero.has_ball(self.ball):
                result = self.hero.shoot_ball(self.ball, self.shoot_charge, self.mouse_world(pos))
            else:
                result = self.hero.aerial(self.ball, self.mouse_world(pos), self.shoot_charge)
            if result:
                self.add_burst(result, self.hero.pos)
            self.charging = False
            self.shoot_charge = 0.0
            self.shoot_charge_elapsed = 0.0

        if button == 3 and self.defense_slide_charging:
            self.defense_slide_charging = False

    def draw_field(self):
        self.screen.fill((25, 80, 60))
        stripe_h = FIELD.height // 18
        for i in range(18):
            color = GRASS_A if i % 2 == 0 else GRASS_B
            rect = pygame.Rect(FIELD.left, FIELD.top + i * stripe_h, FIELD.width, stripe_h + 1)
            rect.move_ip(-self.camera.x, -self.camera.y)
            pygame.draw.rect(self.screen, color, rect)

        field = FIELD.move(-self.camera.x, -self.camera.y)
        pygame.draw.rect(self.screen, LINE, field, 4)
        pygame.draw.line(self.screen, LINE, world_to_screen(pygame.Vector2(FIELD.left, FIELD.centery), self.camera), world_to_screen(pygame.Vector2(FIELD.right, FIELD.centery), self.camera), 3)
        pygame.draw.circle(self.screen, LINE, world_to_screen(pygame.Vector2(FIELD.center), self.camera), 96, 3)
        pygame.draw.circle(self.screen, LINE, world_to_screen(pygame.Vector2(FIELD.center), self.camera), 5)

        for side in (-1, 1):
            goal_y = FIELD.top if side == -1 else FIELD.bottom
            box_y = goal_y if side == -1 else goal_y - 210
            six_y = goal_y if side == -1 else goal_y - 90
            box = pygame.Rect(FIELD.centerx - 250, box_y, 500, 210).move(-self.camera.x, -self.camera.y)
            six = pygame.Rect(FIELD.centerx - 135, six_y, 270, 90).move(-self.camera.x, -self.camera.y)
            goal = pygame.Rect(FIELD.centerx - GOAL_W, goal_y - 20 if side == -1 else goal_y, GOAL_W * 2, 20).move(-self.camera.x, -self.camera.y)
            pygame.draw.rect(self.screen, LINE, box, 3)
            pygame.draw.rect(self.screen, LINE, six, 3)
            pygame.draw.rect(self.screen, WHITE, goal, 3)
            spot = world_to_screen(pygame.Vector2(FIELD.centerx, goal_y + side * 145), self.camera)
            pygame.draw.circle(self.screen, LINE, spot, 4)

    def draw_hud(self):
        pygame.draw.rect(self.screen, INK, (0, 0, SCREEN_W, 68))
        score = f"BLUE {self.score['blue']}  -  {self.score['red']} RED"
        mins = int(self.timer) // 60
        secs = int(self.timer) % 60
        score_label = self.font.render(score, True, WHITE)
        time_label = self.font.render(f"{mins}:{secs:02d}", True, YELLOW)
        self.screen.blit(score_label, score_label.get_rect(center=(SCREEN_W // 2, 22)))
        self.screen.blit(time_label, time_label.get_rect(center=(SCREEN_W // 2, 50)))

        formation = f"Formation: {self.current_formation_name()}  Class: {self.hero.player_class}  1-5 form"
        self.screen.blit(self.small.render(formation, True, WHITE), (24, 16))

    def draw_aim_guide(self):
        return

    def draw_match_over(self):
        if not self.match_over:
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((8, 12, 14, 185))
        self.screen.blit(overlay, (0, 0))

        if self.score["blue"] > self.score["red"]:
            result = "BLUE WINS"
            color = BLUE
        elif self.score["red"] > self.score["blue"]:
            result = "RED WINS"
            color = RED
        else:
            result = "DRAW"
            color = YELLOW

        title = self.font.render("FULL TIME", True, WHITE)
        winner = self.font.render(result, True, color)
        score = self.font.render(f"{self.score['blue']} - {self.score['red']}", True, WHITE)
        hint = self.small.render("Press R to play again", True, WHITE)
        center_x = SCREEN_W // 2
        self.screen.blit(title, title.get_rect(center=(center_x, SCREEN_H // 2 - 70)))
        self.screen.blit(winner, winner.get_rect(center=(center_x, SCREEN_H // 2 - 24)))
        self.screen.blit(score, score.get_rect(center=(center_x, SCREEN_H // 2 + 24)))
        self.screen.blit(hint, hint.get_rect(center=(center_x, SCREEN_H // 2 + 68)))

    def preview_formation_point(self, pitch, x_ratio, y_ratio):
        return pygame.Vector2(
            pitch.centerx + x_ratio * pitch.width * 0.82,
            pitch.centery + y_ratio * pitch.height * 0.82,
        )

    def draw_formation_button(self, rect, label):
        mouse_pos = pygame.mouse.get_pos()
        fill = (238, 189, 62) if rect.collidepoint(mouse_pos) else YELLOW
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, (255, 226, 126), rect, 2, border_radius=6)
        text = self.font.render(label, True, INK)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_formation_preview(self, pitch, name):
        self.formation_slot_buttons = []
        pygame.draw.rect(self.screen, (36, 126, 76), pitch, border_radius=5)
        stripe_h = pitch.height // 8
        for i in range(8):
            color = (42, 146, 85) if i % 2 == 0 else (34, 132, 78)
            pygame.draw.rect(self.screen, color, (pitch.left, pitch.top + i * stripe_h, pitch.width, stripe_h + 1))

        pygame.draw.rect(self.screen, LINE, pitch, 3, border_radius=5)
        pygame.draw.line(self.screen, LINE, (pitch.left, pitch.centery), (pitch.right, pitch.centery), 2)
        pygame.draw.circle(self.screen, LINE, pitch.center, 42, 2)
        pygame.draw.circle(self.screen, LINE, pitch.center, 4)

        for top in (True, False):
            goal_y = pitch.top if top else pitch.bottom
            box_h = 54
            box = pygame.Rect(pitch.centerx - 84, goal_y, 168, box_h)
            if not top:
                box.bottom = pitch.bottom
            pygame.draw.rect(self.screen, LINE, box, 2)
            goal = pygame.Rect(pitch.centerx - 42, goal_y - 8 if top else goal_y, 84, 8)
            pygame.draw.rect(self.screen, WHITE, goal, 2)

        for slot, (x_ratio, y_ratio) in enumerate(FORMATIONS[name]["blue"], start=1):
            pos = self.preview_formation_point(pitch, x_ratio, y_ratio)
            player_class = self.class_choices[slot - 1]
            class_color = PLAYER_CLASSES[player_class]["color"]
            class_scale = PLAYER_CLASSES[player_class]["visual_scale"]
            dot_radius = round(12 * class_scale)
            ring_color = YELLOW if slot - 1 == self.selected_class_slot else WHITE
            self.formation_slot_buttons.append(pygame.Rect(pos.x - 18, pos.y - 18, 36, 36))
            pygame.draw.circle(self.screen, WHITE, pos, dot_radius + 3)
            pygame.draw.circle(self.screen, class_color, pos, dot_radius)
            pygame.draw.circle(self.screen, ring_color, pos, dot_radius + 6, 2)
            number = self.small.render(str(slot), True, INK)
            self.screen.blit(number, number.get_rect(center=pos))
            label = self.small.render(player_class[0], True, WHITE)
            self.screen.blit(label, label.get_rect(center=(pos.x, pos.y + 31)))

    def draw_class_picker(self):
        self.class_button_rects = {}
        start_x = SCREEN_W // 2 - 210
        y = 604
        for index, player_class in enumerate(PLAYER_CLASS_ORDER):
            rect = pygame.Rect(start_x + index * 150, y, 132, 32)
            self.class_button_rects[player_class] = rect
            selected = self.class_choices[self.selected_class_slot] == player_class
            fill = PLAYER_CLASSES[player_class]["color"]
            pygame.draw.rect(self.screen, fill, rect, border_radius=5)
            pygame.draw.rect(self.screen, YELLOW if selected else WHITE, rect, 3 if selected else 1, border_radius=5)
            text_color = INK if player_class != "Tank" else (18, 27, 31)
            label = self.small.render(player_class, True, text_color)
            self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_formation_prompt(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 16, 18, 210))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(150, 58, 800, 612)
        pygame.draw.rect(self.screen, (18, 32, 30), panel, border_radius=6)
        pygame.draw.rect(self.screen, (76, 104, 95), panel, 2, border_radius=6)

        title = self.font.render("Choose Your Formation", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 118)))

        descriptions = {
            "Diamond": "balanced: one forward, two wide mids, one shield",
            "Box": "stable pairs: two attackers, two deeper players",
            "Wide": "stretch play: wide outlets and a central spine",
            "Y": "one high point, two connectors, one deep anchor",
            "Upside-down Y": "one deep base, two connectors, one high point",
        }
        name = self.current_formation_name()
        pitch = pygame.Rect(380, 158, 340, 360)
        self.draw_formation_preview(pitch, name)

        self.formation_prev_button = pygame.Rect(268, pitch.centery - 32, 64, 64)
        self.formation_next_button = pygame.Rect(768, pitch.centery - 32, 64, 64)
        self.draw_formation_button(self.formation_prev_button, "<")
        self.draw_formation_button(self.formation_next_button, ">")

        label = self.font.render(f"{self.formation_index + 1}. {name}", True, WHITE)
        detail = self.small.render(descriptions[name], True, (204, 220, 214))
        self.screen.blit(label, label.get_rect(center=(SCREEN_W // 2, 542)))
        self.screen.blit(detail, detail.get_rect(center=(SCREEN_W // 2, 568)))

        dots_y = 590
        for index in range(len(FORMATION_NAMES)):
            x = SCREEN_W // 2 - 48 + index * 24
            color = YELLOW if index == self.formation_index else (95, 122, 114)
            pygame.draw.circle(self.screen, color, (x, dots_y), 6)

        self.draw_class_picker()
        selected = self.class_choices[self.selected_class_slot]
        hint = self.small.render(f"Click player dots to cycle class   H/R/T set slot {self.selected_class_slot + 1}: {selected}   Enter starts", True, WHITE)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, 656)))

    def draw(self):
        self.draw_field()
        ball_drawn = False
        carrier = self.ball.carrier
        carried_ball_in_front = carrier is not None and carrier.facing.y < -0.25
        for player in sorted(self.players, key=lambda p: p.pos.y):
            if carrier is player and not carried_ball_in_front:
                self.ball.draw(self.screen, self.camera)
                ball_drawn = True
            player.draw(self.screen, self.camera, self.ball, self.animation_db)
            if carrier is player and carried_ball_in_front:
                self.ball.draw(self.screen, self.camera)
                ball_drawn = True
        if not ball_drawn:
            self.ball.draw(self.screen, self.camera)
        self.draw_aim_guide()
        for burst in self.bursts:
            burst.draw(self.screen, self.font, self.camera)
        self.draw_hud()
        if self.choosing_formation:
            self.draw_formation_prompt()
        self.draw_match_over()
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self.handle_keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event.button, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.button, event.pos)

            self.update(dt)
            self.draw()

        pygame.quit()


if __name__ == "__main__":
    Game().run()

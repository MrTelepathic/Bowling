
import pygame
import math
import random
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple, Optional

# =============================================================================
# INITIALIZATION
# =============================================================================
pygame.init()
pygame.font.init()

# Screen settings
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
COLOR_BG = (15, 15, 25)
COLOR_LANE = (139, 90, 43)
COLOR_LANE_DARK = (100, 65, 30)
COLOR_LANE_LIGHT = (180, 130, 70)
COLOR_GUTTER = (40, 35, 30)
COLOR_PIN = (255, 250, 240)
COLOR_PIN_STRIPE = (220, 20, 60)
COLOR_BALL = (30, 80, 150)
COLOR_BALL_HIGHLIGHT = (60, 130, 200)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_GOLD = (255, 215, 100)
COLOR_UI_BG = (30, 30, 40, 200)
COLOR_BUTTON = (60, 60, 80)
COLOR_BUTTON_HOVER = (80, 80, 110)
COLOR_SHADOW = (0, 0, 0, 80)

# Lane dimensions (in Fake-3D perspective)
LANE_TOP_Y = 120
LANE_BOTTOM_Y = 700
LANE_TOP_WIDTH = 200
LANE_BOTTOM_WIDTH = 500
LANE_CENTER_X = SCREEN_WIDTH // 2

# Ball settings
BALL_RADIUS = 25
BALL_START_Y = 620
BALL_MAX_POWER = 25
BALL_MIN_POWER = 3
DRAG_POWER_MULTIPLIER = 0.15

# Pin settings
PIN_RADIUS = 12
PIN_HEIGHT = 35
PIN_START_Y = 180
PIN_SPACING_X = 28
PIN_SPACING_Y = 24

# Screen shake
screen_shake = 0
shake_intensity = 0

# =============================================================================
# UTILITY CLASSES
# =============================================================================
class Vector2D:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float):
        return Vector2D(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            return Vector2D(self.x / mag, self.y / mag)
        return Vector2D(0, 0)

    def distance(self, other) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class GameState(Enum):
    MENU = auto()
    NAME_INPUT = auto()
    PLAYING = auto()
    TURN_END = auto()
    GAME_OVER = auto()


# =============================================================================
# PARTICLE SYSTEM
# =============================================================================
class Particle:
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], 
                 velocity: Vector2D, lifetime: int, size: float):
        self.pos = Vector2D(x, y)
        self.color = color
        self.velocity = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.alpha = 255

    def update(self):
        self.pos = self.pos + self.velocity
        self.velocity.y += 0.1  # gravity
        self.lifetime -= 1
        self.alpha = int(255 * (self.lifetime / self.max_lifetime))

    def draw(self, screen: pygame.Surface):
        if self.lifetime > 0:
            color_with_alpha = (*self.color[:3], self.alpha)
            surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha, 
                             (int(self.size), int(self.size)), int(self.size))
            screen.blit(surf, (int(self.pos.x - self.size), int(self.pos.y - self.size)))


# =============================================================================
# FLOATING TEXT
# =============================================================================
class FloatingText:
    def __init__(self, text: str, x: float, y: float, color: Tuple[int, int, int],
                 size: int = 48, duration: int = 120):
        self.text = text
        self.pos = Vector2D(x, y)
        self.color = color
        self.size = size
        self.duration = duration
        self.max_duration = duration
        self.alpha = 0
        self.font = pygame.font.Font(None, size)

    def update(self):
        self.duration -= 1
        self.pos.y -= 0.5  # Float upward

        # Fade in then out
        progress = 1 - (self.duration / self.max_duration)
        if progress < 0.2:
            self.alpha = int(255 * (progress / 0.2))
        elif progress > 0.7:
            self.alpha = int(255 * ((1 - progress) / 0.3))
        else:
            self.alpha = 255

    def draw(self, screen: pygame.Surface):
        if self.duration > 0 and self.alpha > 0:
            text_surf = self.font.render(self.text, True, self.color)
            text_surf.set_alpha(self.alpha)
            rect = text_surf.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            screen.blit(text_surf, rect)


# =============================================================================
# PIN CLASS
# =============================================================================
class Pin:
    def __init__(self, x: float, y: float, row: int, col: int):
        self.original_pos = Vector2D(x, y)
        self.pos = Vector2D(x, y)
        self.row = row
        self.col = col
        self.standing = True
        self.falling = False
        self.fall_angle = 0
        self.fall_velocity = Vector2D(0, 0)
        self.fall_rotation_speed = 0
        self.hit = False
        self.shadow_offset = Vector2D(8, 12)

    def get_scale(self) -> float:
        # Scale based on depth (Y position)
        depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
        return 0.6 + depth * 0.4

    def get_perspective_x(self) -> float:
        # Adjust X based on depth for perspective convergence
        depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
        lane_width_at_y = LANE_TOP_WIDTH + (LANE_BOTTOM_WIDTH - LANE_TOP_WIDTH) * (1 - depth)
        center_offset = self.pos.x - LANE_CENTER_X
        return LANE_CENTER_X + center_offset * (lane_width_at_y / LANE_BOTTOM_WIDTH)

    def hit_by_ball(self, ball_pos: Vector2D, ball_radius: float, ball_velocity: Vector2D):
        if not self.standing or self.falling:
            return False

        scale = self.get_scale()
        pin_radius = PIN_RADIUS * scale
        distance = self.pos.distance(ball_pos)

        if distance < (ball_radius + pin_radius):
            self.falling = True
            self.hit = True
            # Calculate fall direction based on ball velocity
            hit_dir = (self.pos - ball_pos).normalize()
            self.fall_velocity = hit_dir * (ball_velocity.magnitude() * 0.3 + 2)
            self.fall_rotation_speed = random.uniform(-15, 15)
            return True
        return False

    def hit_by_pin(self, other_pin):
        if not self.standing or self.falling or not other_pin.falling:
            return False

        scale = self.get_scale()
        pin_radius = PIN_RADIUS * scale
        distance = self.pos.distance(other_pin.pos)

        if distance < (pin_radius * 2.5):
            self.falling = True
            self.hit = True
            hit_dir = (self.pos - other_pin.pos).normalize()
            self.fall_velocity = hit_dir * 3
            self.fall_rotation_speed = random.uniform(-10, 10)
            return True
        return False

    def update(self):
        if self.falling:
            self.pos = self.pos + self.fall_velocity
            self.fall_velocity = self.fall_velocity * 0.95  # friction
            self.fall_angle += self.fall_rotation_speed
            self.fall_rotation_speed *= 0.98

            if abs(self.fall_angle) > 90:
                self.standing = False

    def draw_shadow(self, screen: pygame.Surface):
        scale = self.get_scale()
        shadow_x = self.get_perspective_x() + self.shadow_offset.x * scale
        shadow_y = self.pos.y + self.shadow_offset.y * scale

        shadow_surf = pygame.Surface((int(PIN_RADIUS * 3 * scale), int(PIN_RADIUS * 1.5 * scale)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, COLOR_SHADOW, 
                          shadow_surf.get_rect())
        screen.blit(shadow_surf, (int(shadow_x - PIN_RADIUS * 1.5 * scale), 
                                  int(shadow_y - PIN_RADIUS * 0.75 * scale)))

    def draw(self, screen: pygame.Surface):
        scale = self.get_scale()
        x = self.get_perspective_x()
        y = self.pos.y

        # Draw shadow first
        self.draw_shadow(screen)

        if self.standing:
            # Draw pin body (elongated for Fake-3D)
            width = PIN_RADIUS * 2 * scale
            height = PIN_HEIGHT * scale

            # Main body
            pin_rect = pygame.Rect(int(x - width/2), int(y - height/2), 
                                  int(width), int(height))
            pygame.draw.ellipse(screen, COLOR_PIN, pin_rect)

            # Red stripe
            stripe_height = height * 0.25
            stripe_rect = pygame.Rect(int(x - width/2), int(y - height * 0.1),
                                     int(width), int(stripe_height))
            pygame.draw.ellipse(screen, COLOR_PIN_STRIPE, stripe_rect)

            # Highlight
            highlight_rect = pygame.Rect(int(x - width/4), int(y - height/3),
                                        int(width/3), int(height/4))
            pygame.draw.ellipse(screen, (255, 255, 255, 100), highlight_rect)
        elif self.falling:
            # Draw falling/tilted pin
            width = PIN_RADIUS * 2 * scale
            height = PIN_HEIGHT * scale

            # Create rotated surface
            pin_surf = pygame.Surface((int(width * 2), int(height * 2)), pygame.SRCALPHA)
            body_rect = pygame.Rect(int(width/2), int(height/2 - height/2), 
                                   int(width), int(height))
            pygame.draw.ellipse(pin_surf, COLOR_PIN, body_rect)

            # Rotate
            rotated = pygame.transform.rotate(pin_surf, self.fall_angle)
            rect = rotated.get_rect(center=(int(x), int(y)))
            screen.blit(rotated, rect)


# =============================================================================
# BALL CLASS
# =============================================================================
class Ball:
    def __init__(self):
        self.pos = Vector2D(LANE_CENTER_X, BALL_START_Y)
        self.velocity = Vector2D(0, 0)
        self.radius = BALL_RADIUS
        self.rolling = False
        self.dragging = False
        self.drag_start = Vector2D(0, 0)
        self.drag_current = Vector2D(0, 0)
        self.rotation = 0
        self.returning = False
        self.shadow_offset = Vector2D(10, 15)

    def reset(self):
        self.pos = Vector2D(LANE_CENTER_X, BALL_START_Y)
        self.velocity = Vector2D(0, 0)
        self.rolling = False
        self.dragging = False
        self.rotation = 0
        self.returning = False

    def get_scale(self) -> float:
        depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
        return 0.7 + depth * 0.3

    def get_perspective_x(self) -> float:
        depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
        lane_width_at_y = LANE_TOP_WIDTH + (LANE_BOTTOM_WIDTH - LANE_TOP_WIDTH) * (1 - depth)
        center_offset = self.pos.x - LANE_CENTER_X
        return LANE_CENTER_X + center_offset * (lane_width_at_y / LANE_BOTTOM_WIDTH)

    def start_drag(self, mouse_pos: Tuple[int, int]):
        mx, my = mouse_pos
        scale = self.get_scale()
        screen_x = self.get_perspective_x()
        distance = math.sqrt((mx - screen_x) ** 2 + (my - self.pos.y) ** 2)

        if distance < self.radius * scale * 2:
            self.dragging = True
            self.drag_start = Vector2D(mx, my)
            self.drag_current = Vector2D(mx, my)

    def update_drag(self, mouse_pos: Tuple[int, int]):
        if self.dragging:
            self.drag_current = Vector2D(mouse_pos[0], mouse_pos[1])

    def release(self) -> Vector2D:
        if not self.dragging:
            return Vector2D(0, 0)

        self.dragging = False
        drag_vector = self.drag_start - self.drag_current

        # Only release if dragged backward (upward on screen)
        if drag_vector.y < 10:
            return Vector2D(0, 0)

        # Calculate velocity
        power = min(drag_vector.y * DRAG_POWER_MULTIPLIER, BALL_MAX_POWER)
        power = max(power, BALL_MIN_POWER)

        # Direction from horizontal drag
        direction_x = drag_vector.x * 0.1
        direction_x = max(-8, min(8, direction_x))

        self.velocity = Vector2D(direction_x, -power)
        self.rolling = True
        return self.velocity

    def update(self):
        global screen_shake, shake_intensity

        if self.rolling:
            self.pos = self.pos + self.velocity
            self.rotation += self.velocity.magnitude() * 2

            # Friction
            self.velocity = self.velocity * 0.995

            # Check if stopped
            if self.velocity.magnitude() < 0.5 or self.pos.y < LANE_TOP_Y - 50:
                self.rolling = False
                self.returning = True

            # Gutter check
            lane_half_width = self.get_lane_width_at_y(self.pos.y) / 2
            if abs(self.pos.x - LANE_CENTER_X) > lane_half_width + self.radius:
                # Ball in gutter - slow down faster
                self.velocity = self.velocity * 0.9

        elif self.returning:
            # Return ball to start position
            target = Vector2D(LANE_CENTER_X, BALL_START_Y)
            direction = (target - self.pos).normalize()
            distance = self.pos.distance(target)

            if distance > 5:
                speed = min(distance * 0.1, 10)
                self.pos = self.pos + direction * speed
            else:
                self.pos = target
                self.returning = False
                self.velocity = Vector2D(0, 0)

    def get_lane_width_at_y(self, y: float) -> float:
        depth = (y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
        return LANE_TOP_WIDTH + (LANE_BOTTOM_WIDTH - LANE_TOP_WIDTH) * (1 - depth)

    def draw_shadow(self, screen: pygame.Surface):
        scale = self.get_scale()
        shadow_x = self.get_perspective_x() + self.shadow_offset.x * scale
        shadow_y = self.pos.y + self.shadow_offset.y * scale

        shadow_surf = pygame.Surface((int(self.radius * 2.5 * scale), 
                                     int(self.radius * 1.2 * scale)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, COLOR_SHADOW, shadow_surf.get_rect())
        screen.blit(shadow_surf, (int(shadow_x - self.radius * 1.25 * scale),
                                  int(shadow_y - self.radius * 0.6 * scale)))

    def draw(self, screen: pygame.Surface):
        scale = self.get_scale()
        x = self.get_perspective_x()
        y = self.pos.y
        r = self.radius * scale

        # Draw shadow
        self.draw_shadow(screen)

        # Draw ball with 3D effect
        # Main body
        pygame.draw.circle(screen, COLOR_BALL, (int(x), int(y)), int(r))

        # Highlight (top-left)
        highlight_offset = r * 0.3
        pygame.draw.circle(screen, COLOR_BALL_HIGHLIGHT, 
                         (int(x - highlight_offset), int(y - highlight_offset)), 
                         int(r * 0.4))

        # Finger holes
        hole_color = (20, 20, 20)
        hole_positions = [
            (x + r * 0.3, y - r * 0.1),
            (x + r * 0.5, y + r * 0.2),
            (x + r * 0.2, y + r * 0.3)
        ]
        for hx, hy in hole_positions:
            pygame.draw.circle(screen, hole_color, (int(hx), int(hy)), int(r * 0.15))

    def draw_aim_guide(self, screen: pygame.Surface):
        if not self.dragging:
            return

        drag_vector = self.drag_start - self.drag_current
        if drag_vector.y < 10:
            return

        # Calculate predicted path
        power = min(drag_vector.y * DRAG_POWER_MULTIPLIER, BALL_MAX_POWER)
        direction_x = drag_vector.x * 0.1
        direction_x = max(-8, min(8, direction_x))

        # Draw aim line
        start_x = self.get_perspective_x()
        start_y = self.pos.y

        # Dotted line showing direction
        for i in range(10):
            t = i / 10
            dot_x = start_x + direction_x * t * 20
            dot_y = start_y - power * t * 15
            alpha = int(255 * (1 - t * 0.5))
            dot_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (255, 255, 255, alpha), (3, 3), 3)
            screen.blit(dot_surf, (int(dot_x - 3), int(dot_y - 3)))


# =============================================================================
# LANE CLASS
# =============================================================================
class Lane:
    def __init__(self):
        self.pins = []
        self.setup_pins()

    def setup_pins(self):
        self.pins = []
        # Standard 10-pin triangle formation
        for row in range(4):
            for col in range(row + 1):
                # Calculate position in Fake-3D space
                pin_y = PIN_START_Y + row * PIN_SPACING_Y
                # Center the triangle
                row_width = row * PIN_SPACING_X
                pin_x = LANE_CENTER_X - row_width / 2 + col * PIN_SPACING_X
                self.pins.append(Pin(pin_x, pin_y, row, col))

    def reset_pins(self):
        self.setup_pins()

    def get_standing_pins(self) -> int:
        return sum(1 for pin in self.pins if pin.standing)

    def get_fallen_pins(self) -> int:
        return sum(1 for pin in self.pins if not pin.standing)

    def update(self, ball: Ball, particles: List[Particle]):
        global screen_shake, shake_intensity

        if ball.rolling:
            # Check ball-pin collisions
            for pin in self.pins:
                if pin.hit_by_ball(ball.pos, ball.radius * ball.get_scale(), ball.velocity):
                    # Add particles
                    for _ in range(5):
                        vel = Vector2D(random.uniform(-2, 2), random.uniform(-2, 2))
                        particles.append(Particle(
                            pin.get_perspective_x(), pin.pos.y,
                            (200, 180, 160), vel, 30, random.uniform(2, 5)
                        ))
                    # Screen shake on strong hit
                    if ball.velocity.magnitude() > 10:
                        screen_shake = 10
                        shake_intensity = 3

            # Check pin-pin collisions (chain reaction)
            for i, pin1 in enumerate(self.pins):
                if pin1.falling:
                    for pin2 in self.pins[i+1:]:
                        pin2.hit_by_pin(pin1)

        # Update all pins
        for pin in self.pins:
            pin.update()

    def draw(self, screen: pygame.Surface):
        # Draw lane as trapezoid with gradient
        # Top edge (far)
        top_left = (LANE_CENTER_X - LANE_TOP_WIDTH // 2, LANE_TOP_Y)
        top_right = (LANE_CENTER_X + LANE_TOP_WIDTH // 2, LANE_TOP_Y)
        # Bottom edge (near)
        bottom_left = (LANE_CENTER_X - LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y)
        bottom_right = (LANE_CENTER_X + LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y)

        # Main lane surface with gradient
        lane_points = [bottom_left, bottom_right, top_right, top_left]

        # Create gradient effect
        for i in range(LANE_BOTTOM_Y - LANE_TOP_Y):
            y = LANE_TOP_Y + i
            progress = i / (LANE_BOTTOM_Y - LANE_TOP_Y)
            width = LANE_TOP_WIDTH + (LANE_BOTTOM_WIDTH - LANE_TOP_WIDTH) * (1 - progress)

            # Wood color gradient
            r = int(COLOR_LANE_DARK[0] + (COLOR_LANE_LIGHT[0] - COLOR_LANE_DARK[0]) * (1 - progress))
            g = int(COLOR_LANE_DARK[1] + (COLOR_LANE_LIGHT[1] - COLOR_LANE_DARK[1]) * (1 - progress))
            b = int(COLOR_LANE_DARK[2] + (COLOR_LANE_LIGHT[2] - COLOR_LANE_DARK[2]) * (1 - progress))

            pygame.draw.line(screen, (r, g, b), 
                           (LANE_CENTER_X - width // 2, y),
                           (LANE_CENTER_X + width // 2, y))

        # Lane borders/gutters
        # Left gutter
        left_gutter_points = [
            (0, LANE_BOTTOM_Y),
            (LANE_CENTER_X - LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y),
            (LANE_CENTER_X - LANE_TOP_WIDTH // 2, LANE_TOP_Y),
            (0, LANE_TOP_Y)
        ]
        pygame.draw.polygon(screen, COLOR_GUTTER, left_gutter_points)

        # Right gutter
        right_gutter_points = [
            (LANE_CENTER_X + LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y),
            (SCREEN_WIDTH, LANE_BOTTOM_Y),
            (SCREEN_WIDTH, LANE_TOP_Y),
            (LANE_CENTER_X + LANE_TOP_WIDTH // 2, LANE_TOP_Y)
        ]
        pygame.draw.polygon(screen, COLOR_GUTTER, right_gutter_points)

        # Lane edges
        pygame.draw.line(screen, (80, 80, 80), 
                        (LANE_CENTER_X - LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y),
                        (LANE_CENTER_X - LANE_TOP_WIDTH // 2, LANE_TOP_Y), 3)
        pygame.draw.line(screen, (80, 80, 80),
                        (LANE_CENTER_X + LANE_BOTTOM_WIDTH // 2, LANE_BOTTOM_Y),
                        (LANE_CENTER_X + LANE_TOP_WIDTH // 2, LANE_TOP_Y), 3)

        # Pin deck area (lighter)
        pin_area_height = 80
        pin_area_top = LANE_TOP_Y - 20
        pin_area_bottom = pin_area_top + pin_area_height

        # Arrow markers on lane
        arrow_y = 500
        for offset in [-60, -30, 0, 30, 60]:
            arrow_x = LANE_CENTER_X + offset
            pygame.draw.polygon(screen, (100, 70, 40), [
                (arrow_x, arrow_y),
                (arrow_x - 8, arrow_y + 15),
                (arrow_x + 8, arrow_y + 15)
            ])

        # Draw pins (back to front for proper depth)
        for pin in sorted(self.pins, key=lambda p: p.pos.y, reverse=True):
            pin.draw(screen)


# =============================================================================
# PLAYER CLASS
# =============================================================================
class Player:
    def __init__(self, name: str, player_id: int):
        self.name = name if name else f"Player {player_id}"
        self.id = player_id
        self.frames = [[] for _ in range(10)]  # 10 frames
        self.frame_scores = [0] * 10
        self.total_score = 0
        self.current_frame = 0
        self.rolls_in_frame = 0

    def add_roll(self, pins_knocked: int):
        if self.current_frame >= 10:
            return

        self.frames[self.current_frame].append(pins_knocked)
        self.rolls_in_frame += 1

        # Check for frame completion
        if self.current_frame < 9:  # Frames 1-9
            if pins_knocked == 10 or self.rolls_in_frame >= 2:
                self.current_frame += 1
                self.rolls_in_frame = 0
        else:  # Frame 10
            rolls = self.frames[9]
            if len(rolls) == 3:
                self.current_frame += 1
            elif len(rolls) == 2:
                if sum(rolls) < 10:
                    self.current_frame += 1

    def calculate_score(self) -> int:
        score = 0
        roll_index = 0
        all_rolls = []

        # Flatten frames into roll sequence
        for frame in self.frames:
            all_rolls.extend(frame)

        for frame in range(10):
            if roll_index >= len(all_rolls):
                break

            if frame < 9:
                if all_rolls[roll_index] == 10:  # Strike
                    # Next two rolls bonus
                    bonus = 0
                    if roll_index + 1 < len(all_rolls):
                        bonus += all_rolls[roll_index + 1]
                    if roll_index + 2 < len(all_rolls):
                        bonus += all_rolls[roll_index + 2]
                    score += 10 + bonus
                    roll_index += 1
                elif roll_index + 1 < len(all_rolls):
                    frame_sum = all_rolls[roll_index] + all_rolls[roll_index + 1]
                    if frame_sum == 10:  # Spare
                        bonus = all_rolls[roll_index + 2] if roll_index + 2 < len(all_rolls) else 0
                        score += 10 + bonus
                    else:
                        score += frame_sum
                    roll_index += 2
                else:
                    break
            else:  # 10th frame
                remaining = all_rolls[roll_index:]
                score += sum(remaining)

        self.total_score = score
        return score

    def is_game_over(self) -> bool:
        return self.current_frame >= 10

    def get_last_roll_pins(self) -> int:
        if self.current_frame == 0 and self.rolls_in_frame == 0:
            return 0
        if self.frames[self.current_frame - 1 if self.rolls_in_frame == 0 else self.current_frame]:
            return self.frames[self.current_frame - 1 if self.rolls_in_frame == 0 else self.current_frame][-1]
        return 0


# =============================================================================
# UI MANAGER
# =============================================================================
class UIManager:
    def __init__(self):
        self.font_large = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        self.font_tiny = pygame.font.Font(None, 28)
        self.floating_texts = []

    def add_floating_text(self, text: str, x: float, y: float, 
                         color: Tuple[int, int, int] = COLOR_TEXT_GOLD, size: int = 64):
        self.floating_texts.append(FloatingText(text, x, y, color, size))

    def update(self):
        for ft in self.floating_texts[:]:
            ft.update()
            if ft.duration <= 0:
                self.floating_texts.remove(ft)

    def draw_score_panel(self, screen: pygame.Surface, player: Player, 
                        players: List[Player], current_player_idx: int):
        # Panel background
        panel_width = 280
        panel_height = 500
        panel_x = SCREEN_WIDTH - panel_width - 20
        panel_y = 20

        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, COLOR_UI_BG, 
                        (0, 0, panel_width, panel_height), border_radius=15)
        pygame.draw.rect(panel_surf, (80, 80, 100, 150),
                        (0, 0, panel_width, panel_height), 2, border_radius=15)
        screen.blit(panel_surf, (panel_x, panel_y))

        # Title
        title = self.font_medium.render("SCOREBOARD", True, COLOR_TEXT_GOLD)
        screen.blit(title, (panel_x + (panel_width - title.get_width()) // 2, panel_y + 15))

        # Current player indicator
        y_offset = panel_y + 70
        for i, p in enumerate(players):
            # Player name
            if i == current_player_idx:
                name_color = COLOR_TEXT_GOLD
                indicator = "> "
            else:
                name_color = COLOR_TEXT
                indicator = "  "

            name_text = self.font_small.render(f"{indicator}{p.name}", True, name_color)
            screen.blit(name_text, (panel_x + 20, y_offset))

            # Score
            score_text = self.font_small.render(str(p.calculate_score()), True, name_color)
            screen.blit(score_text, (panel_x + panel_width - 60, y_offset))

            y_offset += 40

        # Current player details
        y_offset += 20
        pygame.draw.line(screen, (80, 80, 100), 
                        (panel_x + 20, y_offset), (panel_x + panel_width - 20, y_offset), 2)
        y_offset += 20

        # Frame info
        cp = players[current_player_idx]
        frame_text = self.font_small.render(f"Frame: {min(cp.current_frame + 1, 10)}/10", True, COLOR_TEXT)
        screen.blit(frame_text, (panel_x + 20, y_offset))
        y_offset += 35

        # Roll info
        roll_text = self.font_small.render(f"Roll: {cp.rolls_in_frame + 1}", True, COLOR_TEXT)
        screen.blit(roll_text, (panel_x + 20, y_offset))
        y_offset += 35

        # Current frame score preview
        if cp.current_frame < 10 and cp.frames[cp.current_frame]:
            frame_rolls = cp.frames[cp.current_frame]
            roll_str = " | ".join(str(r) for r in frame_rolls)
            preview = self.font_tiny.render(f"This frame: {roll_str}", True, (180, 180, 180))
            screen.blit(preview, (panel_x + 20, y_offset))

        # Frame grid
        y_offset += 50
        cell_width = 24
        cell_height = 30

        for frame_idx in range(10):
            col = frame_idx % 5
            row = frame_idx // 5
            cell_x = panel_x + 15 + col * (cell_width + 5)
            cell_y = y_offset + row * (cell_height + 25)

            # Frame number
            num_text = self.font_tiny.render(str(frame_idx + 1), True, (150, 150, 150))
            screen.blit(num_text, (cell_x + 5, cell_y - 18))

            # Frame cell
            bg_color = (50, 50, 60) if frame_idx >= cp.current_frame else (60, 70, 80)
            pygame.draw.rect(screen, bg_color, (cell_x, cell_y, cell_width, cell_height), border_radius=3)

            # Frame score
            if frame_idx < len(cp.frames) and cp.frames[frame_idx]:
                if frame_idx == 9:
                    # 10th frame special display
                    score_str = "".join(str(r)[0] for r in cp.frames[frame_idx])
                else:
                    total = sum(cp.frames[frame_idx])
                    if cp.frames[frame_idx][0] == 10:
                        score_str = "X"
                    elif total == 10:
                        score_str = "/"
                    else:
                        score_str = str(total)

                score_text = self.font_tiny.render(score_str, True, COLOR_TEXT)
                screen.blit(score_text, (cell_x + 5, cell_y + 5))

    def draw_button(self, screen: pygame.Surface, text: str, x: int, y: int, 
                   width: int, height: int, hovered: bool = False) -> pygame.Rect:
        color = COLOR_BUTTON_HOVER if hovered else COLOR_BUTTON
        rect = pygame.Rect(x, y, width, height)

        # Button shadow
        shadow_rect = rect.copy()
        shadow_rect.move_ip(3, 3)
        pygame.draw.rect(screen, (20, 20, 25), shadow_rect, border_radius=10)

        # Button body
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, 2, border_radius=10)

        # Text
        text_surf = self.font_small.render(text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

        return rect

    def draw_text_input(self, screen: pygame.Surface, label: str, value: str, 
                       x: int, y: int, width: int, active: bool = False):
        # Label
        label_surf = self.font_small.render(label, True, COLOR_TEXT)
        screen.blit(label_surf, (x, y - 30))

        # Input box
        rect = pygame.Rect(x, y, width, 45)
        bg_color = (50, 50, 65) if active else (40, 40, 50)
        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 130) if active else (70, 70, 90), rect, 2, border_radius=8)

        # Text
        text_surf = self.font_small.render(value + ("|" if active else ""), True, COLOR_TEXT)
        screen.blit(text_surf, (x + 10, y + 8))

        return rect

    def draw(self, screen: pygame.Surface):
        for ft in self.floating_texts:
            ft.draw(screen)


# =============================================================================
# MENU MANAGER
# =============================================================================
class MenuManager:
    def __init__(self, ui_manager: UIManager):
        self.ui = ui_manager
        self.state = GameState.MENU
        self.selected_mode = None
        self.player_count = 2
        self.player_names = ["", ""]
        self.active_input = 0
        self.buttons = {}
        self.text_inputs = {}

    def reset(self):
        self.state = GameState.MENU
        self.selected_mode = None
        self.player_count = 2
        self.player_names = ["", ""]
        self.active_input = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        mouse_pos = pygame.mouse.get_pos()

        if self.state == GameState.MENU:
            return self._handle_menu_event(event, mouse_pos)
        elif self.state == GameState.NAME_INPUT:
            return self._handle_name_input_event(event, mouse_pos)

        return None

    def _handle_menu_event(self, event: pygame.event.Event, mouse_pos) -> Optional[dict]:
        solo_rect = self.buttons.get("solo")
        multi_rect = self.buttons.get("multi")

        if event.type == pygame.MOUSEBUTTONDOWN:
            if solo_rect and solo_rect.collidepoint(mouse_pos):
                return {"action": "start_solo"}
            elif multi_rect and multi_rect.collidepoint(mouse_pos):
                self.state = GameState.NAME_INPUT
                self.player_count = 2
                self.player_names = ["", ""]

        return None

    def _handle_name_input_event(self, event: pygame.event.Event, mouse_pos) -> Optional[dict]:
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check input field clicks
            for i, rect in self.text_inputs.items():
                if rect.collidepoint(mouse_pos):
                    self.active_input = i
                    return None

            # Check buttons
            if self.buttons.get("back") and self.buttons["back"].collidepoint(mouse_pos):
                self.state = GameState.MENU
                return None

            if self.buttons.get("start") and self.buttons["start"].collidepoint(mouse_pos):
                names = [n if n else f"Player {i+1}" for i, n in enumerate(self.player_names)]
                return {"action": "start_multi", "names": names}

            if self.buttons.get("add_player") and self.buttons["add_player"].collidepoint(mouse_pos):
                if self.player_count < 4:
                    self.player_count += 1
                    self.player_names.append("")

        elif event.type == pygame.KEYDOWN:
            if self.active_input < len(self.player_names):
                if event.key == pygame.K_BACKSPACE:
                    self.player_names[self.active_input] = self.player_names[self.active_input][:-1]
                elif event.key == pygame.K_TAB:
                    self.active_input = (self.active_input + 1) % len(self.player_names)
                elif event.key == pygame.K_RETURN:
                    names = [n if n else f"Player {i+1}" for i, n in enumerate(self.player_names)]
                    return {"action": "start_multi", "names": names}
                elif event.unicode.isprintable() and len(self.player_names[self.active_input]) < 12:
                    self.player_names[self.active_input] += event.unicode

        return None

    def draw(self, screen: pygame.Surface):
        if self.state == GameState.MENU:
            self._draw_menu(screen)
        elif self.state == GameState.NAME_INPUT:
            self._draw_name_input(screen)

    def _draw_menu(self, screen: pygame.Surface):
        # Title
        title = self.ui.font_large.render("BOWLING 3D", True, COLOR_TEXT_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(title, title_rect)

        # Subtitle
        subtitle = self.ui.font_small.render("Fake-3D Bowling Experience", True, (180, 180, 200))
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 270))
        screen.blit(subtitle, sub_rect)

        # Buttons
        mouse_pos = pygame.mouse.get_pos()

        solo_hover = False
        multi_hover = False

        solo_rect = self.ui.draw_button(screen, "Solo Mode", 
                                       SCREEN_WIDTH // 2 - 125, 380, 250, 60,
                                       solo_hover)
        multi_rect = self.ui.draw_button(screen, "Multiplayer",
                                        SCREEN_WIDTH // 2 - 125, 470, 250, 60,
                                        multi_hover)

        # Check hover
        if solo_rect.collidepoint(mouse_pos):
            solo_hover = True
        if multi_rect.collidepoint(mouse_pos):
            multi_hover = True

        # Redraw with hover state
        solo_rect = self.ui.draw_button(screen, "Solo Mode",
                                       SCREEN_WIDTH // 2 - 125, 380, 250, 60,
                                       solo_hover)
        multi_rect = self.ui.draw_button(screen, "Multiplayer",
                                        SCREEN_WIDTH // 2 - 125, 470, 250, 60,
                                        multi_hover)

        self.buttons["solo"] = solo_rect
        self.buttons["multi"] = multi_rect

        # Instructions
        instruct = self.ui.font_tiny.render("Drag mouse backward to aim, release to throw", 
                                           True, (150, 150, 170))
        inst_rect = instruct.get_rect(center=(SCREEN_WIDTH // 2, 650))
        screen.blit(instruct, inst_rect)

    def _draw_name_input(self, screen: pygame.Surface):
        # Title
        title = self.ui.font_medium.render("Enter Player Names", True, COLOR_TEXT_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 120))
        screen.blit(title, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        self.text_inputs = {}

        # Input fields
        start_y = 200
        for i in range(self.player_count):
            rect = self.ui.draw_text_input(screen, f"Player {i+1}", 
                                          self.player_names[i],
                                          SCREEN_WIDTH // 2 - 150, start_y + i * 80, 
                                          300, active=(i == self.active_input))
            self.text_inputs[i] = rect

        # Buttons
        back_hover = self.buttons.get("back") and self.buttons["back"].collidepoint(mouse_pos)
        start_hover = self.buttons.get("start") and self.buttons["start"].collidepoint(mouse_pos)

        back_rect = self.ui.draw_button(screen, "Back", 
                                       SCREEN_WIDTH // 2 - 160, 600, 140, 50, back_hover)
        start_rect = self.ui.draw_button(screen, "Start Game",
                                        SCREEN_WIDTH // 2 + 20, 600, 140, 50, start_hover)

        self.buttons["back"] = back_rect
        self.buttons["start"] = start_rect


# =============================================================================
# GAME MANAGER
# =============================================================================
class GameManager:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bowling 3D - Fake-3D Bowling Game")
        self.clock = pygame.time.Clock()
        self.running = True

        self.ui_manager = UIManager()
        self.menu_manager = MenuManager(self.ui_manager)
        self.lane = Lane()
        self.ball = Ball()
        self.players = []
        self.current_player_idx = 0
        self.particles = []

        self.state = GameState.MENU
        self.turn_ended = False
        self.turn_end_timer = 0
        self.pins_before_roll = 10
        self.waiting_for_ball_return = False

    def start_solo(self):
        self.players = [Player("Solo", 1)]
        self.current_player_idx = 0
        self.state = GameState.PLAYING
        self.reset_turn()

    def start_multiplayer(self, names: List[str]):
        self.players = [Player(name, i+1) for i, name in enumerate(names)]
        self.current_player_idx = 0
        self.state = GameState.PLAYING
        self.reset_turn()

    def reset_ball_only(self):
        """Reset only the ball position without resetting pins.
        Used between rolls in the same frame."""
        self.ball.reset()
        self.ball.dragging = False
        self.ball.rolling = False
        self.ball.returning = False
        self.ball.velocity = Vector2D(0, 0)
        self.turn_ended = False
        self.turn_end_timer = 0
        self.pins_before_roll = self.lane.get_standing_pins()
        self.waiting_for_ball_return = False
        self.state = GameState.PLAYING

    def reset_turn(self):
        """Reset both ball and pins for a new frame."""
        self.lane.reset_pins()
        self.ball.reset()
        self.ball.dragging = False
        self.ball.rolling = False
        self.ball.returning = False
        self.ball.velocity = Vector2D(0, 0)
        self.turn_ended = False
        self.turn_end_timer = 0
        self.pins_before_roll = 10
        self.waiting_for_ball_return = False
        self.state = GameState.PLAYING

    def is_frame_complete(self, player: Player) -> bool:
        """Check if the roll just made completed a frame.
        
        A frame is complete if:
        - For frames 1-9: either a strike was rolled, or 2 rolls were made
        - For frame 10: 3 rolls if strike/spare, or 2 rolls if open
        
        We detect this by checking if the current frame (pointed to by current_frame)
        has any rolls in it. If it does, we're still in the middle of a frame.
        If it doesn't, we just started a new frame (meaning the previous one completed).
        """
        if player.current_frame >= 10:
            return True  # Game over
        
        current_frame_rolls = player.frames[player.current_frame]
        
        # If current frame has rolls, we're in the middle of a frame
        if len(current_frame_rolls) > 0:
            return False
        
        # Current frame has no rolls, meaning we just advanced to it
        # So the previous frame was completed
        return True

    def next_turn(self):
        current_player = self.players[self.current_player_idx]
        
        # Check if frame is complete
        if self.is_frame_complete(current_player):
            # Frame complete - move to next player and reset pins
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
            if self.current_player_idx == 0:
                # Check if game is over
                if all(p.is_game_over() for p in self.players):
                    self.state = GameState.GAME_OVER
                    return
            
            if not self.players[self.current_player_idx].is_game_over():
                self.reset_turn()
            else:
                self.state = GameState.GAME_OVER
        else:
            # Frame not complete - same player, keep pins as they are
            self.reset_ball_only()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == GameState.MENU or self.state == GameState.NAME_INPUT:
                result = self.menu_manager.handle_event(event)
                if result:
                    if result["action"] == "start_solo":
                        self.start_solo()
                    elif result["action"] == "start_multi":
                        self.start_multiplayer(result["names"])

            elif self.state == GameState.PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.ball.rolling and not self.ball.returning and not self.turn_ended:
                        self.ball.start_drag(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.ball.dragging:
                        velocity = self.ball.release()
                        if velocity.magnitude() > 0:
                            self.pins_before_roll = self.lane.get_standing_pins()

                elif event.type == pygame.MOUSEMOTION:
                    self.ball.update_drag(event.pos)

            elif self.state == GameState.TURN_END:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.next_turn()

            elif self.state == GameState.GAME_OVER:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    restart_rect = self.ui_manager.draw_button(
                        self.screen, "Play Again", SCREEN_WIDTH // 2 - 75, 550, 150, 50
                    )
                    if restart_rect.collidepoint(mouse_pos):
                        self.menu_manager.reset()
                        self.state = GameState.MENU
                        self.players = []

    def update(self):
        global screen_shake, shake_intensity

        self.ui_manager.update()

        if self.state == GameState.PLAYING:
            # Update ball
            self.ball.update()

            # Update lane and collisions
            self.lane.update(self.ball, self.particles)

            # Update particles
            for p in self.particles[:]:
                p.update()
                if p.lifetime <= 0:
                    self.particles.remove(p)

            # Check for turn end
            if self.ball.rolling:
                self.waiting_for_ball_return = True

            if self.waiting_for_ball_return and not self.ball.rolling and not self.ball.returning:
                # Ball has stopped, calculate score
                fallen = self.pins_before_roll - self.lane.get_standing_pins()
                current_player = self.players[self.current_player_idx]
                current_player.add_roll(fallen)
                current_player.calculate_score()

                # Show result text
                if fallen == 10 and self.pins_before_roll == 10:
                    self.ui_manager.add_floating_text("STRIKE!", SCREEN_WIDTH // 2, 300, 
                                                     (255, 215, 0), 72)
                elif fallen == self.pins_before_roll and self.pins_before_roll < 10:
                    self.ui_manager.add_floating_text("SPARE!", SCREEN_WIDTH // 2, 300,
                                                     (100, 200, 255), 72)
                elif fallen > 0:
                    self.ui_manager.add_floating_text(f"{fallen} PINS!", SCREEN_WIDTH // 2, 300,
                                                     (200, 200, 200), 56)
                else:
                    self.ui_manager.add_floating_text("GUTTER!", SCREEN_WIDTH // 2, 300,
                                                     (150, 150, 150), 56)

                self.turn_ended = True
                self.turn_end_timer = 120  # 2 seconds at 60 FPS
                self.waiting_for_ball_return = False

            if self.turn_ended:
                self.turn_end_timer -= 1
                if self.turn_end_timer <= 0:
                    self.state = GameState.TURN_END

        # Screen shake decay
        if screen_shake > 0:
            screen_shake -= 1

    def draw(self):
        global screen_shake, shake_intensity

        # Apply screen shake
        shake_x = 0
        shake_y = 0
        if screen_shake > 0:
            shake_x = random.randint(-shake_intensity, shake_intensity)
            shake_y = random.randint(-shake_intensity, shake_intensity)

        # Background
        self.screen.fill(COLOR_BG)

        # Draw ambient lighting effect
        for i in range(5):
            alpha = 20 - i * 3
            radius = 400 + i * 50
            light_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(light_surf, (255, 255, 255, alpha), (radius, radius), radius)
            self.screen.blit(light_surf, (LANE_CENTER_X - radius, 100 - radius // 2))

        if self.state == GameState.PLAYING or self.state == GameState.TURN_END:
            # Draw lane
            self.lane.draw(self.screen)

            # Draw ball
            self.ball.draw(self.screen)
            self.ball.draw_aim_guide(self.screen)

            # Draw particles
            for p in self.particles:
                p.draw(self.screen)

            # Draw score panel
            if self.players:
                self.ui_manager.draw_score_panel(self.screen, 
                    self.players[self.current_player_idx], 
                    self.players, self.current_player_idx)

            # Draw turn indicator
            if self.state == GameState.TURN_END and self.players:
                player = self.players[self.current_player_idx]
                if not player.is_game_over():
                    next_text = self.ui_manager.font_medium.render(
                        f"Click to continue - {player.name}'s turn", True, COLOR_TEXT)
                    rect = next_text.get_rect(center=(SCREEN_WIDTH // 2, 750))
                    self.screen.blit(next_text, rect)

        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()

        else:
            self.menu_manager.draw(self.screen)

        # Draw floating texts
        self.ui_manager.draw(self.screen)

        # Apply shake offset
        if shake_x != 0 or shake_y != 0:
            shaken = self.screen.copy()
            self.screen.fill(COLOR_BG)
            self.screen.blit(shaken, (shake_x, shake_y))

        pygame.display.flip()

    def draw_game_over(self):
        # Title
        title = self.ui_manager.font_large.render("GAME OVER", True, COLOR_TEXT_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        # Final scores
        y_offset = 250
        sorted_players = sorted(self.players, key=lambda p: p.total_score, reverse=True)

        for i, player in enumerate(sorted_players):
            rank_color = COLOR_TEXT_GOLD if i == 0 else COLOR_TEXT
            name_text = self.ui_manager.font_medium.render(
                f"{i+1}. {player.name}", True, rank_color)
            score_text = self.ui_manager.font_medium.render(
                str(player.total_score), True, rank_color)

            self.screen.blit(name_text, (SCREEN_WIDTH // 2 - 150, y_offset + i * 60))
            self.screen.blit(score_text, (SCREEN_WIDTH // 2 + 100, y_offset + i * 60))

        # Restart button
        mouse_pos = pygame.mouse.get_pos()
        restart_rect = pygame.Rect(SCREEN_WIDTH // 2 - 75, 550, 150, 50)
        hover = restart_rect.collidepoint(mouse_pos)
        self.ui_manager.draw_button(self.screen, "Play Again",
                                   SCREEN_WIDTH // 2 - 75, 550, 150, 50, hover)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    game = GameManager()
    game.run()

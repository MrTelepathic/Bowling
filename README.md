# 🎳 Bowling 3D

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Pygame](https://img.shields.io/badge/Pygame-2.0+-green.svg)](https://pygame.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A cinematic Fake-3D bowling game built with Python and Pygame. Experience realistic physics, stunning visuals, and authentic bowling scoring in this polished indie game.

![Game Screenshot](screenshots/game.png)

## ✨ Features

### 🎮 Gameplay
- **Mouse-only controls** - Drag backward to aim, release to throw
- **Realistic physics** - Ball rolls, curves, and reacts to your throw
- **Authentic bowling rules** - Standard 10-frame scoring with strikes and spares
- **Two game modes** - Solo play or multiplayer (up to 4 players)

### 🌌 Visual Effects
- **Fake-3D perspective** - Lane narrows toward pins with depth scaling
- **Dynamic shadows** - Ball and pins cast realistic shadows
- **Screen shake** - Feel the impact of strong collisions
- **Floating text** - "Strike!", "Spare!", and score notifications
- **Particle effects** - Debris on pin hits

### 🎨 UI & Polish
- **Beautiful scoreboard** - Real-time score tracking with frame grid
- **Smooth animations** - Ball rolling, pin falling, and transitions
- **Professional styling** - Modern, clean interface

## 🚀 Installation & Running

### Prerequisites
- Python 3.8 or higher
- Pygame 2.0 or higher

### Setup

```bash
# Clone or download the repository
git clone https://github.com/MrTelepathic/bowling.git
cd bowling

# Install dependencies
pip install pygame

# Run the game
python bowling_game.py
```

## 🎯 Controls

| Action | Control |
|--------|---------|
| **Aim** | Click and drag **backward** on the ball |
| **Direction** | Drag **left/right** while dragging backward |
| **Throw** | **Release** mouse button |
| **Menu navigation** | Mouse click on buttons |
| **Name input** | Type names, Tab to switch, Enter to confirm |

### Pro Tips
- Drag further backward for more power
- Small left/right drags create subtle curves
- Large directional drags can send the ball to the gutters
- Watch the dotted aim line for trajectory preview

---

# 📚 Code Tutorial

This section provides a comprehensive walkthrough of the game's code, designed to help beginners and intermediate Python developers understand how the game works.

## Project Structure

```
bowling/
├── bowling_game.py    # Main game file (all code in one file)
├── README.md          # This file
└── screenshots/       # Game screenshots
```

The entire game is contained in a single Python file for simplicity. Here's how it's organized:

## 1. Class Overview

### GameManager

The `GameManager` is the **heart of the game**. It coordinates everything:

```python
class GameManager:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game objects
        self.ui_manager = UIManager()
        self.menu_manager = MenuManager(self.ui_manager)
        self.lane = Lane()
        self.ball = Ball()
        self.players = []
        
        # Game state
        self.state = GameState.MENU
```

**What it does:**
- Initializes Pygame and creates the game window
- Creates all game objects (ball, lane, pins, UI)
- Manages the game state (menu, playing, turn end, game over)
- Runs the main game loop

**Why it's needed:**
Every game needs a central coordinator. Without `GameManager`, we'd have scattered code with no clear flow.

### MenuManager

Handles all menu screens:

```python
class MenuManager:
    def __init__(self, ui_manager: UIManager):
        self.state = GameState.MENU
        self.selected_mode = None
        self.player_names = ["", ""]
```

**What it does:**
- Shows the main menu (Solo / Multiplayer)
- Handles player name input
- Processes button clicks and text input

**States:**
- `MENU` - Main menu with game mode selection
- `NAME_INPUT` - Screen for entering player names

### UIManager

Renders all UI elements:

```python
class UIManager:
    def __init__(self):
        self.font_large = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 48)
        self.floating_texts = []
```

**What it does:**
- Draws the scoreboard panel
- Renders buttons and text inputs
- Manages floating text animations ("Strike!", etc.)
- Updates and draws particle effects

### Lane

Represents the bowling lane with all 10 pins:

```python
class Lane:
    def __init__(self):
        self.pins = []
        self.setup_pins()
    
    def setup_pins(self):
        # Creates 10 pins in triangle formation
        for row in range(4):
            for col in range(row + 1):
                pin_y = PIN_START_Y + row * PIN_SPACING_Y
                pin_x = LANE_CENTER_X - row_width / 2 + col * PIN_SPACING_X
                self.pins.append(Pin(pin_x, pin_y, row, col))
```

**What it does:**
- Creates the 10-pin triangle formation
- Draws the lane with wood texture gradient
- Handles ball-pin collision detection
- Updates pin physics (falling, chain reactions)

**The triangle formation:**
```
    •       <- Row 0 (1 pin)
   • •      <- Row 1 (2 pins)
  • • •     <- Row 2 (3 pins)
 • • • •    <- Row 3 (4 pins)
```

### Ball

The bowling ball with physics:

```python
class Ball:
    def __init__(self):
        self.pos = Vector2D(LANE_CENTER_X, BALL_START_Y)
        self.velocity = Vector2D(0, 0)
        self.radius = BALL_RADIUS
        self.rolling = False
        self.dragging = False
```

**What it does:**
- Handles mouse drag input for aiming
- Calculates throw velocity from drag distance
- Updates position with friction
- Returns to start position after each throw
- Draws the ball with 3D effect (highlight, finger holes)

### Pin

Individual bowling pin:

```python
class Pin:
    def __init__(self, x: float, y: float, row: int, col: int):
        self.original_pos = Vector2D(x, y)
        self.pos = Vector2D(x, y)
        self.standing = True
        self.falling = False
        self.fall_angle = 0
```

**What it does:**
- Tracks standing/falling state
- Handles collision with ball and other pins
- Updates fall animation (rotation, sliding)
- Draws pin with depth scaling for Fake-3D effect

### Player

Stores player data and scoring:

```python
class Player:
    def __init__(self, name: str, player_id: int):
        self.name = name
        self.frames = [[] for _ in range(10)]  # 10 frames
        self.current_frame = 0
        self.rolls_in_frame = 0
```

**What it does:**
- Records rolls for each frame
- Calculates score with strike/spare bonuses
- Tracks current frame and roll

---

## 2. The Game Loop

Every game has a main loop that runs continuously:

```python
def run(self):
    while self.running:
        self.handle_events()   # Process input
        self.update()          # Update game logic
        self.draw()            # Render everything
        self.clock.tick(FPS)   # Limit to 60 FPS
```

### Event Handling

```python
def handle_events(self):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            self.running = False
        
        elif self.state == GameState.PLAYING:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.ball.start_drag(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.ball.release()
            elif event.type == pygame.MOUSEMOTION:
                self.ball.update_drag(event.pos)
```

**What happens:**
1. Check for window close (QUIT event)
2. If playing, handle mouse drag for ball control
3. If turn ended, wait for click to continue

### Update Logic

```python
def update(self):
    if self.state == GameState.PLAYING:
        self.ball.update()
        self.lane.update(self.ball, self.particles)
        
        # Check if turn should end
        if self.ball_stopped():
            self.calculate_score()
            self.state = GameState.TURN_END
```

**What happens:**
1. Update ball position and physics
2. Check for collisions with pins
3. Update pin animations
4. If ball stopped, end the turn

### Draw Logic

```python
def draw(self):
    self.screen.fill(COLOR_BG)
    self.lane.draw(self.screen)
    self.ball.draw(self.screen)
    self.ui_manager.draw_score_panel(...)
    pygame.display.flip()
```

**Drawing order matters!** We draw from back to front:
1. Background
2. Lane (with gradient)
3. Pins (back to front for depth)
4. Ball
5. UI elements (scoreboard)

---

## 3. Key Code Explained

### Mouse Drag Mechanics

**How velocity is calculated:**

```python
def release(self) -> Vector2D:
    drag_vector = self.drag_start - self.drag_current
    
    # Only release if dragged backward (upward on screen)
    if drag_vector.y < 10:
        return Vector2D(0, 0)
    
    # Power from vertical drag distance
    power = min(drag_vector.y * DRAG_POWER_MULTIPLIER, BALL_MAX_POWER)
    power = max(power, BALL_MIN_POWER)
    
    # Direction from horizontal drag
    direction_x = drag_vector.x * 0.1
    direction_x = max(-8, min(8, direction_x))
    
    self.velocity = Vector2D(direction_x, -power)
    return self.velocity
```

**How it works:**
1. Calculate vector from drag start to current position
2. Vertical component (y) = power (drag further = more power)
3. Horizontal component (x) = direction (drag left = ball goes left)
4. Negative Y because screen Y increases downward

**Visual example:**
```
Drag path:        Result:
    ↑              Ball goes
    |              straight
    ●              forward
    
    ↖              Ball goes
   /               left
  ●                

    ↗              Ball goes
    \              right
     ●
```

### Fake-3D Perspective Math

**Depth scaling:**

```python
def get_scale(self) -> float:
    # Scale based on depth (Y position)
    depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
    return 0.6 + depth * 0.4
```

**What it does:**
- Objects farther away (smaller Y) appear smaller
- At the top of the lane (pins): scale = 0.6
- At the bottom (player): scale = 1.0

**Perspective X adjustment:**

```python
def get_perspective_x(self) -> float:
    depth = (self.pos.y - LANE_TOP_Y) / (LANE_BOTTOM_Y - LANE_TOP_Y)
    lane_width_at_y = LANE_TOP_WIDTH + (LANE_BOTTOM_WIDTH - LANE_TOP_WIDTH) * (1 - depth)
    center_offset = self.pos.x - LANE_CENTER_X
    return LANE_CENTER_X + center_offset * (lane_width_at_y / LANE_BOTTOM_WIDTH)
```

**What it does:**
- Adjusts X position based on depth
- Creates the "trapezoid" effect where the lane narrows toward the pins
- Objects at the same logical X position appear more centered when far away

### Collision Detection

**Ball-Pin collision:**

```python
def hit_by_ball(self, ball_pos: Vector2D, ball_radius: float, ball_velocity: Vector2D):
    scale = self.get_scale()
    pin_radius = PIN_RADIUS * scale
    distance = self.pos.distance(ball_pos)
    
    if distance < (ball_radius + pin_radius):
        self.falling = True
        # Calculate fall direction from ball velocity
        hit_dir = (self.pos - ball_pos).normalize()
        self.fall_velocity = hit_dir * (ball_velocity.magnitude() * 0.3 + 2)
        return True
    return False
```

**How it works:**
1. Calculate distance between ball and pin centers
2. If distance < sum of radii, they collide
3. Pin starts falling in direction away from ball
4. Fall velocity depends on ball speed (faster ball = pins fly further)

**Pin-Pin collision (chain reaction):**

```python
def hit_by_pin(self, other_pin):
    if not self.standing or self.falling or not other_pin.falling:
        return False
    
    distance = self.pos.distance(other_pin.pos)
    if distance < (pin_radius * 2.5):
        self.falling = True
        return True
```

This allows pins to knock over other pins, creating realistic chain reactions!

### State Machine

The game uses a state machine to manage flow:

```python
class GameState(Enum):
    MENU = auto()        # Main menu
    NAME_INPUT = auto()  # Entering player names
    PLAYING = auto()     # Active gameplay
    TURN_END = auto()    # Between turns
    GAME_OVER = auto()   # Final results
```

**State transitions:**
```
MENU → NAME_INPUT → PLAYING → TURN_END → PLAYING → ... → GAME_OVER → MENU
       (multiplayer)    ↑___________|
```

**Why use a state machine?**
- Clear separation of concerns
- Easy to add new states
- Prevents bugs from mixed logic

### Score Calculation

Bowling scoring is complex! Here's how it works:

```python
def calculate_score(self) -> int:
    score = 0
    roll_index = 0
    all_rolls = []
    
    # Flatten frames into one list
    for frame in self.frames:
        all_rolls.extend(frame)
    
    for frame in range(10):
        if frame < 9:  # Frames 1-9
            if all_rolls[roll_index] == 10:  # Strike!
                # Bonus: next 2 rolls
                bonus = all_rolls[roll_index + 1] + all_rolls[roll_index + 2]
                score += 10 + bonus
                roll_index += 1
            elif all_rolls[roll_index] + all_rolls[roll_index + 1] == 10:  # Spare!
                # Bonus: next 1 roll
                bonus = all_rolls[roll_index + 2]
                score += 10 + bonus
                roll_index += 2
            else:  # Open frame
                score += all_rolls[roll_index] + all_rolls[roll_index + 1]
                roll_index += 2
        else:  # Frame 10
            score += sum(all_rolls[roll_index:])
    
    return score
```

**Scoring rules:**
- **Strike** (10 on first roll): 10 + next 2 rolls
- **Spare** (10 total in 2 rolls): 10 + next 1 roll
- **Open frame**: Sum of both rolls

**Example:**
```
Frame 1: Strike (X) → 10 + 5 + 3 = 18
Frame 2: 5, 3 → 8
Frame 3: Spare (6, /) → 10 + 4 = 14
Frame 4: 4, 2 → 6
Total: 46
```

### Turn Reset Logic

**The pin reset bug fix:**

```python
def reset_ball_only(self):
    """Reset only the ball for second roll of a frame."""
    self.ball.reset()
    self.turn_ended = False
    self.state = GameState.PLAYING
    # Pins are NOT reset!

def reset_turn(self):
    """Reset ball AND pins for a new frame."""
    self.lane.reset_pins()  # Full reset
    self.ball.reset()
    self.turn_ended = False
    self.state = GameState.PLAYING

def next_turn(self):
    current_player = self.players[self.current_player_idx]
    
    if self.is_frame_complete(current_player):
        # Frame done - move to next player, reset pins
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        self.reset_turn()
    else:
        # Same frame - keep pins as they are
        self.reset_ball_only()
```

**Why this matters:**
- In bowling, you get 2 rolls per frame (unless you get a strike)
- After the first roll, remaining pins stay standing
- Pins only reset when a frame is complete

---

## 4. Code Walkthrough by Section

### Initialization (Lines 1-60)

```python
import pygame
import math
import random

pygame.init()
pygame.font.init()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
```

**What it does:**
- Imports required libraries
- Initializes Pygame
- Sets screen dimensions and frame rate

**Why it's needed:**
Without initialization, Pygame functions won't work.

### Utility Classes (Lines 65-100)

```python
class Vector2D:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y
```

**What it does:**
Provides 2D vector math operations (addition, subtraction, magnitude, etc.)

**Why it's needed:**
Game physics requires vector math. This class makes the code cleaner.

### Ball Class (Lines 290-440)

```python
class Ball:
    def __init__(self):
        self.pos = Vector2D(LANE_CENTER_X, BALL_START_Y)
        self.velocity = Vector2D(0, 0)
```

**Key methods:**
- `start_drag()` - Begins tracking mouse drag
- `update_drag()` - Updates aim while dragging
- `release()` - Calculates velocity and starts ball rolling
- `update()` - Updates position with physics
- `draw()` - Renders ball with 3D effect

### Lane Class (Lines 470-605)

```python
class Lane:
    def __init__(self):
        self.pins = []
        self.setup_pins()
```

**Key methods:**
- `setup_pins()` - Creates 10 pins in triangle formation
- `update()` - Handles ball-pin and pin-pin collisions
- `draw()` - Renders lane with wood gradient

### GameManager Class (Lines 1020-1280)

```python
class GameManager:
    def __init__(self):
        # Initialize everything
        
    def handle_events(self):
        # Process input
        
    def update(self):
        # Update game state
        
    def draw(self):
        # Render everything
        
    def run(self):
        # Main game loop
```

This is the largest class, coordinating all game functionality.

---

## 5. How Key Features Work

### Floating Text Animation

```python
class FloatingText:
    def update(self):
        self.duration -= 1
        self.pos.y -= 0.5  # Float upward
        
        # Fade in then out
        progress = 1 - (self.duration / self.max_duration)
        if progress < 0.2:
            self.alpha = int(255 * (progress / 0.2))  # Fade in
        elif progress > 0.7:
            self.alpha = int(255 * ((1 - progress) / 0.3))  # Fade out
```

**What it does:**
- Text floats upward
- Fades in quickly, stays visible, fades out slowly
- Creates a polished "notification" effect

### Screen Shake

```python
# Global variables
screen_shake = 0
shake_intensity = 0

# When collision happens:
screen_shake = 10  # Shake for 10 frames
shake_intensity = 3  # Shake by 3 pixels

# In draw():
if screen_shake > 0:
    shake_x = random.randint(-shake_intensity, shake_intensity)
    shake_y = random.randint(-shake_intensity, shake_intensity)
    # Apply offset to entire screen
```

**What it does:**
- Randomly offsets the screen for a few frames
- Creates a "impact" feeling on strong collisions
- Intensity and duration can be adjusted

### Particle Effects

```python
class Particle:
    def update(self):
        self.pos = self.pos + self.velocity
        self.velocity.y += 0.1  # Gravity
        self.lifetime -= 1
        self.alpha = int(255 * (self.lifetime / self.max_lifetime))
```

**What it does:**
- Small particles fly out from collision point
- Affected by gravity
- Fade out over time

---

## 6. Tips for Learning

### For Beginners

1. **Start with the game loop** - Understand `handle_events()`, `update()`, `draw()`
2. **Trace a single throw** - Follow the code from mouse click to pin hit
3. **Modify constants** - Change `BALL_MAX_POWER` or `PIN_RADIUS` to see effects
4. **Add print statements** - Debug by printing values at key points

### For Intermediate Developers

1. **Study the state machine** - See how `GameState` cleanly separates logic
2. **Analyze the physics** - Understand vector math and collision detection
3. **Review the scoring** - Bowling scoring is a great algorithm exercise
4. **Consider optimizations** - How would you handle 100 pins? 1000?

### Experiment Ideas

```python
# Try these modifications:

# 1. Change ball size
BALL_RADIUS = 50  # Giant ball!

# 2. Add more power
DRAG_POWER_MULTIPLIER = 0.3  # Super fast throws

# 3. Change lane color
COLOR_LANE = (100, 50, 150)  # Purple lane

# 4. Add more pins (requires setup_pins modification)
# Try a 5-row triangle: 1+2+3+4+5 = 15 pins
```

---

## 🔮 Future Improvements

Potential features to add:

- [ ] **Sound effects** - Ball roll, pin hits, crowd cheers
- [ ] **High scores** - Save best scores to file
- [ ] **Different ball colors** - Unlockable skins
- [ ] **Lane oil patterns** - Affect ball curve
- [ ] **Replay system** - Save and watch throws
- [ ] **AI opponents** - Play against computer
- [ ] **Online multiplayer** - Network play

---

## 🙏 Credits

- Built with [Pygame](https://pygame.org)
- Inspired by classic bowling games
- Created as an educational Python project

---

## 🤝 Contributing

Contributions are welcome! Here are some ways to help:

1. **Report bugs** - Open an issue with steps to reproduce
2. **Suggest features** - Open an issue with your idea
3. **Submit code** - Fork, modify, and create a pull request
4. **Improve documentation** - Help make this README better

---

**Happy Bowling! 🎳**

"""
Global configuration for pathfinding rules and behaviors.
"""

# Rule: Paths must never step on walls (always enforced by neighbor checks)
NO_WALL_CONTACT = True

# Use pure step-based cost (each move = 1). When False, penalties may apply.
PURE_SHORTEST_PATH = True

# Use A* (with Manhattan heuristic) instead of pure Dijkstra for performance
USE_ASTAR = True

# Optional: Near-wall penalty (only used if PURE_SHORTEST_PATH is False)
USE_OBSTACLE_PENALTY = False
NEAR_WALL_PENALTY = 0.1

# Optional validation: Verify the returned path length equals the BFS shortest path
VERIFY_OPTIMALITY_WITH_BFS = True

# Enhanced validation settings for robust wall detection
STRICT_PATH_VALIDATION = True
CLEAN_INVALID_POSITIONS = True

# Dual Algorithm Settings for Ghost Avoidance
USE_DUAL_ALGORITHM = True  # Enable dual algorithm approach
GHOST_AVOIDANCE_RADIUS = 8  # Increased from 6 to 8 for much better safety margin
GHOST_PENALTY_MULTIPLIER = 15  # Increased from 10 for stronger ghost avoidance
ALLOW_RISKY_PATHS = True  # Allow slightly dangerous paths if much shorter
RISKY_PATH_THRESHOLD = 1.3  # Reduced from 1.5 - prefer safer paths more

# Path Safety Evaluation  
SAFETY_DANGER_THRESHOLD = 0.10  # Reduced from 0.15 for even stricter safety
EMERGENCY_UPDATE_INTERVAL_MS = 30  # Reduced from 50ms for faster response
NEAR_DANGER_UPDATE_INTERVAL_MS = 100  # Reduced from 200ms for quicker updates
NORMAL_UPDATE_INTERVAL_MS = 250  # Reduced from 400ms for more frequent updates

# Logging and Debugging
ENABLE_GHOST_AVOIDANCE_LOGGING = True  # Log dual algorithm decisions
LOG_PATH_EVERY_N_STEPS = 5  # Log progress every N steps

# Movement Speed Settings (blocks per second - independent of FPS)
# These speeds represent how many grid blocks the character moves per second
PACMAN_SPEED = 4.0  # Pacman moves 4 blocks per second
GHOST_SPEED = 3.0   # Ghost moves 3 blocks per second (slower than Pacman)
GHOST_EYES_SPEED = 5.0  # Ghost eyes return speed (fastest - 5 blocks per second)
PACMAN_LEGACY_SPEED = 4.0  # Legacy speed for compatibility

# Dynamic Speed Control Settings
ENABLE_DYNAMIC_SPEED = False  # Enable/disable Pacman slowdown when near ghosts
DYNAMIC_SPEED_VERY_CLOSE = 0.5  # Speed multiplier when ghost is very close (≤2 blocks)
DYNAMIC_SPEED_CLOSE = 0.7       # Speed multiplier when ghost is close (≤4 blocks)  
DYNAMIC_SPEED_NEARBY = 0.85     # Speed multiplier when ghost is nearby (≤6 blocks)

# FPS Settings
TARGET_FPS = 60  # Target frame rate (can be changed without affecting movement speed)
MAX_DELTA_TIME = 1.0 / 30.0  # Cap delta time to prevent large jumps (minimum 30 FPS)

# Performance Optimization Settings
COLLISION_CHECK_DISTANCE = 60  # Max distance to check for dot collisions (pixels)
ENABLE_SPATIAL_OPTIMIZATION = True  # Use spatial partitioning for collision detection

# Auto Mode Speed Control Settings
AUTO_MODE_SPEED_LEVELS = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]  # Các mức tốc độ: 0.5x, 1x, 1.5x, 2x, 3x, 5x
AUTO_MODE_DEFAULT_SPEED_INDEX = 1  # Index mặc định (1.0x - tốc độ bình thường)

# UI - Right Control Panel (font sizes)
# Increase these values if the right-side control panel text is too small.
RIGHT_PANEL_TITLE_FONT_SIZE = 18
RIGHT_PANEL_SMALL_FONT_SIZE = 16
RIGHT_PANEL_TINY_FONT_SIZE = 14
RIGHT_PANEL_LINE_HEIGHT = 20

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
GHOST_AVOIDANCE_RADIUS = 6  # Increased from 4 to 6 for better safety margin
GHOST_PENALTY_MULTIPLIER = 10  # Base multiplier for ghost penalties
ALLOW_RISKY_PATHS = True  # Allow slightly dangerous paths if much shorter
RISKY_PATH_THRESHOLD = 1.5  # Allow paths up to 50% longer if avoidance path exists

# Path Safety Evaluation
SAFETY_DANGER_THRESHOLD = 0.15  # Reduced from 0.2 for stricter safety
EMERGENCY_UPDATE_INTERVAL_MS = 50  # Reduced from 100ms for faster response
NEAR_DANGER_UPDATE_INTERVAL_MS = 200  # Reduced from 400ms for quicker updates
NORMAL_UPDATE_INTERVAL_MS = 400  # Reduced from 800ms for more frequent updates

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

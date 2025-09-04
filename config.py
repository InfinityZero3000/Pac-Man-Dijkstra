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

# Movement Speed Settings (blocks per second)
PACMAN_SPEED = 4  # Tăng tốc độ Pacman để xử lý kịp với thuật toán né ma mới
GHOST_SPEED = 3   # Ghost movement speed (slower than Pacman)
GHOST_EYES_SPEED = 4.0  # Ghost eyes return speed (fastest)
PACMAN_LEGACY_SPEED = 4  # Tăng legacy speed để theo kịp

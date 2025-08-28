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
GHOST_AVOIDANCE_RADIUS = 4  # How far to avoid ghosts (in blocks)
GHOST_PENALTY_MULTIPLIER = 10  # Base multiplier for ghost penalties
ALLOW_RISKY_PATHS = True  # Allow slightly dangerous paths if much shorter
RISKY_PATH_THRESHOLD = 1.5  # Allow paths up to 50% longer if avoidance path exists

# Path Safety Evaluation
SAFETY_DANGER_THRESHOLD = 0.2  # Maximum fraction of dangerous positions allowed
EMERGENCY_UPDATE_INTERVAL_MS = 300  # How often to recalculate path in danger
NEAR_DANGER_UPDATE_INTERVAL_MS = 800  # How often to recalculate when ghost is near
NORMAL_UPDATE_INTERVAL_MS = 1500  # Normal path recalculation interval

# Logging and Debugging
ENABLE_GHOST_AVOIDANCE_LOGGING = True  # Log dual algorithm decisions
LOG_PATH_EVERY_N_STEPS = 5  # Log progress every N steps

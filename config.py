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

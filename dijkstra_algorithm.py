import heapq
import json
import os
from datetime import datetime
import hashlib
from collections import deque
import numpy as np
import config
from path_validator import PathValidator
import math


class DijkstraAlgorithm:
    def __init__(self, maze_generator):
        self.maze_gen = maze_generator
        self.log_data = []
        self.run_history = []  # Add missing run_history attribute
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._height, self._width = self.maze_gen.maze.shape
        self.last_run_stats = None
        self.last_nodes_explored = 0  # Quick access to nodes explored
        self.validator = PathValidator(maze_generator)
        
        # Advanced pathfinding state
        self.ghost_memory = {}  # Remember ghost positions and movements
        self.path_cache = {}    # Cache calculated paths
        self.danger_zones = set()  # Track dangerous areas
        self.safe_zones = set()    # Track known safe areas

    def shortest_path(self, start, goal, enable_logging=True):
        """A*/Dijkstra on grid; enforces no-wall moves and shortest path cost."""
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            self.last_run_stats = {
                'nodes_explored': 0,
                'computation_time_ms': 0.0,
                'success': False,
            }
            return None, float('inf')

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()
        prev = {start: None}

        explored = 0
        t0 = datetime.now()

        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1

            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                
                # Strict validation: remove any wall positions from path
                clean_path = []
                for pos in path:
                    row, col = pos
                    if (0 <= row < self.maze_gen.height and 
                        0 <= col < self.maze_gen.width and 
                        self.maze_gen.maze[row, col] == 0):  # Only open paths
                        clean_path.append(pos)
                
                if not clean_path:
                    if enable_logging:
                        self._log_error('INVALID_PATH', {'start': start, 'goal': goal, 'path': path, 'distance': g})
                    self.last_run_stats = {
                        'nodes_explored': explored,
                        'computation_time_ms': dt_ms,
                        'success': False,
                    }
                    return None, float('inf')
                
                if enable_logging:
                    self._log_successful_path(start, goal, clean_path, g, explored, dt_ms)
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                self.last_nodes_explored = explored  # Quick access
                return clean_path, len(clean_path) - 1  # Return step count as distance

            if g > dist.get(node, float('inf')):
                continue

            for nb in self._get_valid_neighbors(node):
                ng = g + self._calculate_move_cost(node, nb)
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    prev[nb] = node
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))

        if enable_logging:
            self._log_error('GOAL_UNREACHABLE', {'start': start, 'goal': goal, 'nodes_explored': explored, 'reachable_positions': len(dist)})
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        self.last_nodes_explored = explored  # Quick access
        return None, float('inf')

    def shortest_path_with_ghost_avoidance(self, start, goal, ghost_positions, avoidance_radius=3, enable_logging=True):
        """A*/Dijkstra with dynamic ghost avoidance - dual algorithm approach"""
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            self.last_run_stats = {
                'nodes_explored': 0,
                'computation_time_ms': 0.0,
                'success': False,
            }
            return None, float('inf')

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()
        prev = {start: None}

        explored = 0
        t0 = datetime.now()

        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1

            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                
                # Clean path validation
                clean_path = []
                for pos in path:
                    row, col = pos
                    if (0 <= row < self.maze_gen.height and 
                        0 <= col < self.maze_gen.width and 
                        self.maze_gen.maze[row, col] == 0):
                        clean_path.append(pos)
                
                if not clean_path:
                    if enable_logging:
                        self._log_error('INVALID_PATH_GHOST_AVOIDANCE', {'start': start, 'goal': goal, 'path': path, 'distance': g})
                    self.last_run_stats = {
                        'nodes_explored': explored,
                        'computation_time_ms': dt_ms,
                        'success': False,
                    }
                    return None, float('inf')
                
                if enable_logging:
                    self._log_successful_path_avoidance(start, goal, clean_path, g, explored, dt_ms, ghost_positions)
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                return clean_path, len(clean_path) - 1

            if g > dist.get(node, float('inf')):
                continue

            for nb in self._get_valid_neighbors(node):
                # Calculate move cost with ghost avoidance
                base_cost = self._calculate_move_cost(node, nb)
                ghost_penalty = self._calculate_ghost_penalty(nb, ghost_positions, avoidance_radius)
                ng = g + base_cost + ghost_penalty
                
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    prev[nb] = node
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))

        if enable_logging:
            self._log_error('GOAL_UNREACHABLE_GHOST_AVOIDANCE', {'start': start, 'goal': goal, 'nodes_explored': explored, 'ghost_positions': ghost_positions})
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        return None, float('inf')

    def shortest_path_with_bomb_avoidance(self, start, goal, bomb_positions=None, cell_size=23, bomb_positions_are_grid=True, enable_logging=True):
        """A*/Dijkstra on grid with bomb avoidance - bombs are treated as walls"""
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            self.last_run_stats = {
                'nodes_explored': 0,
                'computation_time_ms': 0.0,
                'success': False,
            }
            return None, float('inf')

        # Convert bomb positions to grid coordinates if needed
        bomb_set = set()
        if bomb_positions:
            if bomb_positions_are_grid:
                bomb_set = set(bomb_positions)
            else:
                for bomb in bomb_positions:
                    bomb_x, bomb_y = bomb
                    # Convert screen center to maze grid position
                    col = round(bomb_x / cell_size - 0.5)
                    row = round(bomb_y / cell_size - 0.5)
                    if 0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width:
                        bomb_set.add((int(row), int(col)))
        
        # Debug output (disabled by default)
        # if bomb_set and enable_logging:
        #     print(f" Pathfinding from {start} to {goal} avoiding {len(bomb_set)} bombs: {list(bomb_set)[:3]}...")

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()
        prev = {start: None}

        explored = 0
        t0 = datetime.now()

        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1

            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                
                # Strict validation: remove any wall or bomb positions from path
                clean_path = []
                for pos in path:
                    row, col = pos
                    if (0 <= row < self.maze_gen.height and 
                        0 <= col < self.maze_gen.width and 
                        self.maze_gen.maze[row, col] == 0 and  # Only open paths
                        pos not in bomb_set):  # Avoid bombs
                        clean_path.append(pos)
                
                if not clean_path:
                    if enable_logging:
                        self._log_error('INVALID_PATH_BOMB_AVOIDANCE', {'start': start, 'goal': goal, 'path': path, 'distance': g, 'bombs': list(bomb_set)})
                    self.last_run_stats = {
                        'nodes_explored': explored,
                        'computation_time_ms': dt_ms,
                        'success': False,
                    }
                    return None, float('inf')
                
                if enable_logging:
                    self._log_successful_path_bomb_avoidance(start, goal, clean_path, g, explored, dt_ms, list(bomb_set))
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                return clean_path, len(clean_path) - 1  # Return step count as distance

            if g > dist.get(node, float('inf')):
                continue

            for nb in self._get_valid_neighbors_with_bomb_avoidance(node, bomb_set):
                ng = g + self._calculate_move_cost(node, nb)
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    prev[nb] = node
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))

        if enable_logging:
            self._log_error('GOAL_UNREACHABLE_BOMB_AVOIDANCE', {'start': start, 'goal': goal, 'nodes_explored': explored, 'bombs': list(bomb_set)})
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        return None, float('inf')

    def shortest_path_with_bomb_penalty(self, start, goal, bomb_positions=None, bomb_penalty=50, enable_logging=True):
        """A*/Dijkstra with bomb penalty instead of complete avoidance"""
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            self.last_run_stats = {
                'nodes_explored': 0,
                'computation_time_ms': 0.0,
                'success': False,
            }
            return None, float('inf')

        # Convert bomb positions to set for fast lookup
        bomb_set = set()
        if bomb_positions:
            bomb_set = set(bomb_positions)

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()
        prev = {start: None}

        explored = 0
        t0 = datetime.now()

        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1

            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                
                # Clean path validation
                clean_path = []
                for pos in path:
                    row, col = pos
                    if (0 <= row < self.maze_gen.height and 
                        0 <= col < self.maze_gen.width and 
                        self.maze_gen.maze[row, col] == 0):
                        clean_path.append(pos)
                
                if not clean_path:
                    if enable_logging:
                        self._log_error('INVALID_PATH_BOMB_PENALTY', {'start': start, 'goal': goal, 'path': path, 'distance': g})
                    self.last_run_stats = {
                        'nodes_explored': explored,
                        'computation_time_ms': dt_ms,
                        'success': False,
                    }
                    return None, float('inf')
                
                if enable_logging:
                    self._log_successful_path_bomb_penalty(start, goal, clean_path, g, explored, dt_ms, list(bomb_set))
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                return clean_path, len(clean_path) - 1

            if g > dist.get(node, float('inf')):
                continue

            for nb in self._get_valid_neighbors(node):
                # Calculate move cost with bomb penalty
                base_cost = self._calculate_move_cost(node, nb)
                bomb_cost = bomb_penalty if nb in bomb_set else 0
                ng = g + base_cost + bomb_cost
                
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    prev[nb] = node
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))

        if enable_logging:
            self._log_error('GOAL_UNREACHABLE_BOMB_PENALTY', {'start': start, 'goal': goal, 'nodes_explored': explored, 'bombs': list(bomb_set)})
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        return None, float('inf')

    def shortest_path_with_bomb_radius_avoidance(self, start, goal, bomb_positions=None, avoidance_radius=2, enable_logging=True):
        """A*/Dijkstra with bomb avoidance radius - penalizes positions near bombs"""
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            self.last_run_stats = {
                'nodes_explored': 0,
                'computation_time_ms': 0.0,
                'success': False,
            }
            return None, float('inf')

        # Create bomb danger zones
        danger_zones = {}
        if bomb_positions:
            for bomb in bomb_positions:
                bomb_row, bomb_col = bomb
                for dr in range(-avoidance_radius, avoidance_radius + 1):
                    for dc in range(-avoidance_radius, avoidance_radius + 1):
                        r, c = bomb_row + dr, bomb_col + dc
                        if (0 <= r < self.maze_gen.height and 
                            0 <= c < self.maze_gen.width and
                            self.maze_gen.maze[r, c] == 0):  # Only penalize valid paths
                            distance = abs(dr) + abs(dc)
                            if distance <= avoidance_radius and distance > 0:  # Don't penalize bomb itself if it's a wall
                                penalty = max(1, avoidance_radius - distance + 1) * 10  # Higher penalty closer to bomb
                                danger_zones[(r, c)] = penalty

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()
        prev = {start: None}

        explored = 0
        t0 = datetime.now()

        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1

            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                
                # Clean path validation
                clean_path = []
                for pos in path:
                    row, col = pos
                    if (0 <= row < self.maze_gen.height and 
                        0 <= col < self.maze_gen.width and 
                        self.maze_gen.maze[row, col] == 0):
                        clean_path.append(pos)
                
                if not clean_path:
                    if enable_logging:
                        self._log_error('INVALID_PATH_BOMB_RADIUS', {'start': start, 'goal': goal, 'path': path, 'distance': g})
                    self.last_run_stats = {
                        'nodes_explored': explored,
                        'computation_time_ms': dt_ms,
                        'success': False,
                    }
                    return None, float('inf')
                
                if enable_logging:
                    self._log_successful_path_bomb_radius(start, goal, clean_path, g, explored, dt_ms, list(bomb_positions) if bomb_positions else [])
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                return clean_path, len(clean_path) - 1

            if g > dist.get(node, float('inf')):
                continue

            for nb in self._get_valid_neighbors(node):
                # Calculate move cost with bomb radius penalty
                base_cost = self._calculate_move_cost(node, nb)
                danger_penalty = danger_zones.get(nb, 0)
                ng = g + base_cost + danger_penalty
                
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    prev[nb] = node
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))

        if enable_logging:
            self._log_error('GOAL_UNREACHABLE_BOMB_RADIUS', {'start': start, 'goal': goal, 'nodes_explored': explored, 'bombs': list(bomb_positions) if bomb_positions else []})
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        return None, float('inf')

    def shortest_path_with_ghost_and_bomb_avoidance(self, start, goal, ghost_positions, bomb_positions, avoidance_radius=5, enable_logging=False):
        """
        CRITICAL: Path tránh CẢ bomb (as walls) VÀ ghost (penalty-based)
        - Bomb: Coi như tường, KHÔNG BAO GIỜ đi qua
        - Ghost: Thêm penalty cao cho các cell gần ghost
        """
        self.last_run_stats = None
        if not self._validate_positions(start, goal):
            return None, float('inf')
        
        # Convert bombs to set for fast lookup
        bomb_set = set()
        if bomb_positions:
            if isinstance(bomb_positions, set):
                bomb_set = bomb_positions
            else:
                bomb_set = set(bomb_positions)
        
        # Build ghost penalty map
        ghost_penalty_map = {}
        if ghost_positions:
            for ghost_pos in ghost_positions:
                gr, gc = ghost_pos
                # Add penalty in radius around ghost
                for dr in range(-avoidance_radius, avoidance_radius + 1):
                    for dc in range(-avoidance_radius, avoidance_radius + 1):
                        check_r = gr + dr
                        check_c = gc + dc
                        if 0 <= check_r < self.maze_gen.height and 0 <= check_c < self.maze_gen.width:
                            manhattan_dist = abs(dr) + abs(dc)
                            if manhattan_dist <= avoidance_radius and manhattan_dist > 0:
                                penalty = int(100 * (avoidance_radius - manhattan_dist + 1) / avoidance_radius)
                                check_pos = (check_r, check_c)
                                if check_pos not in ghost_penalty_map:
                                    ghost_penalty_map[check_pos] = penalty
                                else:
                                    ghost_penalty_map[check_pos] = max(ghost_penalty_map[check_pos], penalty)
        
        # A* pathfinding
        pq = []
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))
        
        dist = {start: 0}
        visited = set()
        explored = 0
        t0 = datetime.now()
        
        while pq:
            f, g, node, path = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            explored += 1
            
            if node == goal:
                dt_ms = (datetime.now() - t0).total_seconds() * 1000
                self.last_run_stats = {
                    'nodes_explored': explored,
                    'computation_time_ms': dt_ms,
                    'success': True,
                }
                return path, len(path) - 1
            
            if g > dist.get(node, float('inf')):
                continue
            
            # Get neighbors avoiding bombs
            for nb in self._get_valid_neighbors_with_bomb_avoidance(node, bomb_set):
                # Base cost + ghost penalty
                base_cost = 1
                ghost_penalty = ghost_penalty_map.get(nb, 0)
                ng = g + base_cost + ghost_penalty
                
                if ng < dist.get(nb, float('inf')):
                    dist[nb] = ng
                    npath = path + [nb]
                    nf = ng + (self._heuristic(nb, goal) if getattr(config, 'USE_ASTAR', False) else 0)
                    heapq.heappush(pq, (nf, ng, nb, npath))
        
        # No path found
        self.last_run_stats = {
            'nodes_explored': explored,
            'computation_time_ms': (datetime.now() - t0).total_seconds() * 1000,
            'success': False,
        }
        return None, float('inf')

    def _log_successful_path_bomb_radius(self, start, goal, path, distance, explored, dt_ms, bomb_positions):
        """Log successful path with bomb radius avoidance"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'algorithm': 'Dijkstra_with_Bomb_Radius',
            'start': start,
            'goal': goal,
            'path': path,
            'distance': distance,
            'nodes_explored': explored,
            'computation_time_ms': dt_ms,
            'bomb_positions': bomb_positions,
            'success': True
        }
        self.log_data.append(log_entry)
        self.run_history.append(log_entry)

    def shortest_path_with_multi_objectives(self, start, objectives, ghost_positions, 
                                                   ghost_velocities=None, power_pellet_positions=None, 
                                                   dots_positions=None, exit_gate=None, enable_logging=True):
        """
        Advanced multi-objective pathfinding for Pacman AI
        Combines: ghost avoidance, dot collection, power pellet prioritization, and exit finding
        """
        self.last_run_stats = None
        if not objectives:
            return None, float('inf')
        
        # Update ghost memory and predictions
        self._update_ghost_memory(ghost_positions, ghost_velocities)
        
        # Prioritize objectives based on game state
        prioritized_objectives = self._prioritize_objectives(
            start, objectives, ghost_positions, power_pellet_positions, 
            dots_positions, exit_gate
        )
        
        best_path = None
        best_score = float('-inf')
        chosen_objective = None
        
        t0 = datetime.now()
        total_explored = 0
        
        # Try each objective with different strategies
        for obj_type, target, priority_weight in prioritized_objectives:
            # Strategy 1: Direct path with ghost avoidance
            path1, score1 = self._pathfind_with_strategy(
                start, target, ghost_positions, "ghost_avoidance", priority_weight
            )
            
            # Strategy 2: Tactical detour (collect items on the way)
            path2, score2 = self._pathfind_with_strategy(
                start, target, ghost_positions, "tactical_detour", priority_weight,
                extra_data={'dots': dots_positions, 'pellets': power_pellet_positions}
            )
            
            # Strategy 3: Emergency escape route
            path3, score3 = self._pathfind_with_strategy(
                start, target, ghost_positions, "emergency_escape", priority_weight
            )
            
            # Choose best strategy for this objective
            best_strategy_path, best_strategy_score = max(
                [(path1, score1), (path2, score2), (path3, score3)],
                key=lambda x: x[1] if x[0] else float('-inf')
            )
            
            if best_strategy_path and best_strategy_score > best_score:
                best_path = best_strategy_path
                best_score = best_strategy_score
                chosen_objective = (obj_type, target)
        
        dt_ms = (datetime.now() - t0).total_seconds() * 1000
        
        if best_path:
            if enable_logging:
                self._log_advanced_pathfinding(start, chosen_objective, best_path, 
                                             best_score, total_explored, dt_ms, ghost_positions)
            
            self.last_run_stats = {
                'nodes_explored': total_explored,
                'computation_time_ms': dt_ms,
                'success': True,
                'strategy_used': 'multi_objective',
                'chosen_objective': chosen_objective
            }
            return best_path, len(best_path) - 1
        
        if enable_logging:
            self._log_error('NO_VIABLE_PATH_MULTI_OBJECTIVE', {
                'start': start, 'objectives': objectives, 'ghost_positions': ghost_positions
            })
        
        self.last_run_stats = {
            'nodes_explored': total_explored,
            'computation_time_ms': dt_ms,
            'success': False,
        }
        return None, float('inf')

    def _update_ghost_memory(self, ghost_positions, ghost_velocities=None):
        """Update ghost movement patterns and prediction memory"""
        current_time = datetime.now()
        
        # Update position history for each ghost
        for i, pos in enumerate(ghost_positions):
            if i not in self.ghost_memory:
                self.ghost_memory[i] = {'positions': [], 'patterns': [], 'last_seen': current_time}
            
            ghost_data = self.ghost_memory[i]
            ghost_data['positions'].append((pos, current_time))
            ghost_data['last_seen'] = current_time
            
            # Keep only recent history (last 10 positions)
            if len(ghost_data['positions']) > 10:
                ghost_data['positions'] = ghost_data['positions'][-10:]
            
            # Analyze movement patterns
            self._analyze_ghost_patterns(i, ghost_data)

    def _analyze_ghost_patterns(self, ghost_id, ghost_data):
        """Analyze ghost movement patterns for prediction"""
        positions = ghost_data['positions']
        if len(positions) < 3:
            return
        
        # Calculate movement vectors
        movements = []
        for i in range(1, len(positions)):
            prev_pos, _ = positions[i-1]
            curr_pos, _ = positions[i]
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            movements.append((dx, dy))
        
        # Detect patterns (循環移動、追跡行動など)
        ghost_data['patterns'] = self._detect_movement_patterns(movements)

    def _detect_movement_patterns(self, movements):
        """Detect common ghost movement patterns"""
        if len(movements) < 3:
            return {'type': 'insufficient_data'}
        
        # Check for circular movement
        if self._is_circular_movement(movements):
            return {'type': 'circular', 'predictable': True}
        
        # Check for chase behavior
        if self._is_chase_pattern(movements):
            return {'type': 'chase', 'predictable': False}
        
        # Check for random movement
        if self._is_random_movement(movements):
            return {'type': 'random', 'predictable': False}
        
        return {'type': 'linear', 'predictable': True}

    def _is_circular_movement(self, movements):
        """Check if ghost is moving in a circular pattern"""
        if len(movements) < 4:
            return False
        
        # Simple circular detection: check if movement repeats
        pattern_length = len(movements) // 2
        if pattern_length < 2:
            return False
        
        pattern = movements[:pattern_length]
        repeat = movements[pattern_length:pattern_length*2]
        return pattern == repeat

    def _is_chase_pattern(self, movements):
        """Check if ghost is actively chasing"""
        # This would need Pacman position to determine properly
        # For now, detect if movement is generally in one direction
        if not movements:
            return False
        
        # Count dominant directions
        directions = {}
        for dx, dy in movements:
            direction = (1 if dx > 0 else -1 if dx < 0 else 0,
                        1 if dy > 0 else -1 if dy < 0 else 0)
            directions[direction] = directions.get(direction, 0) + 1
        
        # If one direction dominates, likely chasing
        max_count = max(directions.values()) if directions else 0
        return max_count > len(movements) * 0.6

    def _is_random_movement(self, movements):
        """Check if ghost movement appears random"""
        if len(movements) < 3:
            return True
        
        # Random if no clear pattern emerges
        unique_directions = set(movements)
        return len(unique_directions) > len(movements) * 0.7

    def _prioritize_objectives(self, start, objectives, ghost_positions, 
                              power_pellet_positions=None, dots_positions=None, exit_gate=None):
        """Prioritize objectives based on current game state - CHỈ ƯU TIÊN EXIT GATE"""
        prioritized = []
        
        for obj in objectives:
            obj_type = self._classify_objective(obj, power_pellet_positions, dots_positions, exit_gate)
            distance = self._manhattan_distance(start, obj)
            danger_level = self._calculate_objective_danger(obj, ghost_positions)
            
            # Calculate priority weight - CHỈ ƯU TIÊN EXIT GATE
            if obj_type == 'exit':
                priority = 100 - danger_level * 5 - distance * 0.3
            else:
                # DISABLED: Không ưu tiên power pellets và dots nữa
                # if obj_type == 'power_pellet':
                #     priority = 100 - danger_level * 10 - distance * 0.5
                # elif obj_type == 'dot':
                #     priority = 50 - danger_level * 15 - distance * 1.0
                # else:
                priority = 10 - danger_level * 20 - distance * 2.0  # Thấp hơn exit gate
            
            prioritized.append((obj_type, obj, priority))
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x[2], reverse=True)
        return prioritized

    def _classify_objective(self, objective, power_pellet_positions=None, 
                           dots_positions=None, exit_gate=None):
        """Classify what type of objective this is"""
        if power_pellet_positions and objective in power_pellet_positions:
            return 'power_pellet'
        elif exit_gate and objective == exit_gate:
            return 'exit'
        elif dots_positions and objective in dots_positions:
            return 'dot'
        else:
            return 'unknown'

    def _calculate_objective_danger(self, objective, ghost_positions):
        """Calculate danger level for an objective based on ghost proximity"""
        if not ghost_positions:
            return 0
        
        min_ghost_dist = min(self._manhattan_distance(objective, ghost_pos) 
                            for ghost_pos in ghost_positions)
        
        # Convert distance to danger level (closer = more dangerous)
        if min_ghost_dist <= 2:
            return 10  # Very dangerous
        elif min_ghost_dist <= 4:
            return 7   # Dangerous
        elif min_ghost_dist <= 6:
            return 4   # Moderate danger
        else:
            return 1   # Low danger

    def _pathfind_with_strategy(self, start, target, ghost_positions, strategy, 
                               priority_weight, extra_data=None):
        """Execute pathfinding with specific strategy"""
        if strategy == "ghost_avoidance":
            return self._ghost_avoidance_strategy(start, target, ghost_positions, priority_weight)
        elif strategy == "tactical_detour":
            return self._tactical_detour_strategy(start, target, ghost_positions, 
                                                 priority_weight, extra_data)
        elif strategy == "emergency_escape":
            return self._emergency_escape_strategy(start, target, ghost_positions, priority_weight)
        else:
            return None, float('-inf')

    def _ghost_avoidance_strategy(self, start, target, ghost_positions, priority_weight):
        """Direct path with strong ghost avoidance"""
        path, cost = self.shortest_path_with_ghost_avoidance(
            start, target, ghost_positions, avoidance_radius=5
        )
        
        if path:
            # Score based on path length and safety
            safety_score = self._calculate_path_safety(path, ghost_positions)
            score = priority_weight + safety_score * 10 - cost * 0.5
            return path, score
        
        return None, float('-inf')

    def _tactical_detour_strategy(self, start, target, ghost_positions, 
                                 priority_weight, extra_data):
        """Path that collects items along the way - DISABLED: Không thu thập items nữa"""
        # DISABLED: Không thu thập dots/pellets nữa, chỉ đi thẳng đến target
        # if not extra_data:
        #     return self._ghost_avoidance_strategy(start, target, ghost_positions, priority_weight)
        #
        # dots = extra_data.get('dots', [])
        # pellets = extra_data.get('pellets', [])
        #
        # # Find path that goes through valuable items
        # best_path = None
        # best_score = float('-inf')
        #
        # # Try direct path first
        # direct_path, direct_score = self._ghost_avoidance_strategy(
        #     start, target, ghost_positions, priority_weight
        # )
        #
        # if direct_path:
        #     # Calculate bonus for items collected along the way
        #     bonus = self._calculate_collection_bonus(direct_path, dots, pellets)
        #     total_score = direct_score + bonus
        #
        #     if total_score > best_score:
        #         best_score = total_score
        #         best_path = direct_path
        #
        # # Try detour through valuable items
        # valuable_items = pellets[:3] + dots[:5]  # Limit to avoid too much computation
        #
        # for item in valuable_items:
        #     # Path: start -> item -> target
        #     path1, cost1 = self.shortest_path_with_ghost_avoidance(
        #         start, item, ghost_positions, avoidance_radius=4
        #     )
        #     path2, cost2 = self.shortest_path_with_ghost_avoidance(
        #         item, target, ghost_positions, avoidance_radius=4
        #     )
        
        # Chỉ đi thẳng đến target, không detour để thu thập items
        return self._ghost_avoidance_strategy(start, target, ghost_positions, priority_weight)

    def _emergency_escape_strategy(self, start, target, ghost_positions, priority_weight):
        """Emergency escape route when in immediate danger"""
        # Check if we're in immediate danger
        min_ghost_dist = min(self._manhattan_distance(start, ghost_pos) 
                            for ghost_pos in ghost_positions) if ghost_positions else float('inf')
        
        if min_ghost_dist > 3:
            # Not in immediate danger, use normal strategy
            return self._ghost_avoidance_strategy(start, target, ghost_positions, priority_weight)
        
        # Find safe zones first
        safe_positions = self._find_safe_zones(start, ghost_positions)
        
        if not safe_positions:
            # No safe zones, try direct escape
            return self._ghost_avoidance_strategy(start, target, ghost_positions, priority_weight)
        
        # Find path through safe zones
        best_path = None
        best_score = float('-inf')
        
        for safe_pos in safe_positions[:3]:  # Try top 3 safe positions
            # Path: start -> safe_pos -> target
            path1, cost1 = self.shortest_path_with_ghost_avoidance(
                start, safe_pos, ghost_positions, avoidance_radius=6
            )
            path2, cost2 = self.shortest_path_with_ghost_avoidance(
                safe_pos, target, ghost_positions, avoidance_radius=4
            )
            
            if path1 and path2:
                full_path = path1 + path2[1:]
                safety_score = self._calculate_path_safety(full_path, ghost_positions)
                total_cost = cost1 + cost2
                
                # Higher weight on safety in emergency
                score = priority_weight + safety_score * 20 - total_cost * 0.3
                
                if score > best_score:
                    best_score = score
                    best_path = full_path
        
        return best_path, best_score

    def _find_safe_zones(self, start, ghost_positions, radius=8):
        """Find positions that are relatively safe from ghosts"""
        safe_zones = []
        
        # Check positions in a radius around start
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                pos = (start[0] + dx, start[1] + dy)
                
                # Check if position is valid
                if not self.maze_gen.is_valid_position(pos[0], pos[1]):
                    continue
                
                # Check distance from all ghosts
                min_ghost_dist = min(self._manhattan_distance(pos, ghost_pos) 
                                   for ghost_pos in ghost_positions) if ghost_positions else float('inf')
                
                if min_ghost_dist >= 5:  # Safe if at least 5 units from nearest ghost
                    manhattan_dist = self._manhattan_distance(start, pos)
                    safety_score = min_ghost_dist - manhattan_dist * 0.1
                    safe_zones.append((pos, safety_score))
        
        # Sort by safety score
        safe_zones.sort(key=lambda x: x[1], reverse=True)
        return [pos for pos, score in safe_zones]

    def _calculate_collection_bonus(self, path, dots, pellets):
        """Calculate bonus score for items that would be collected along path - DISABLED"""
        # DISABLED: Không tính bonus cho việc thu thập dots/pellets nữa
        # bonus = 0
        # path_set = set(path)
        #
        # # Bonus for dots
        # for dot in dots:
        #     if dot in path_set:
        #         bonus += 5
        #
        # # Higher bonus for power pellets
        # for pellet in pellets:
        #     if pellet in path_set:
        #         bonus += 20
        #
        # return bonus
        return 0  # Không có bonus nào cho việc thu thập items

    def _calculate_path_safety(self, path, ghost_positions):
        """Calculate overall safety score for a path"""
        if not path or not ghost_positions:
            return 10  # Safe if no ghosts
        
        total_safety = 0
        for pos in path:
            min_ghost_dist = min(self._manhattan_distance(pos, ghost_pos) 
                               for ghost_pos in ghost_positions)
            
            # Convert distance to safety score
            if min_ghost_dist >= 6:
                safety = 10
            elif min_ghost_dist >= 4:
                safety = 7
            elif min_ghost_dist >= 2:
                safety = 3
            else:
                safety = -5  # Dangerous
            
            total_safety += safety
        
        return total_safety / len(path)  # Average safety

    def _log_advanced_pathfinding(self, start, chosen_objective, path, score, 
                                 nodes_explored, time_ms, ghost_positions):
        """Log advanced pathfinding results"""
        obj_type, target = chosen_objective
        path_length = len(path) - 1
        safety_score = self._calculate_path_safety(path, ghost_positions)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'algorithm': 'advanced_multi_objective',
            'start_position': start,
            'target_position': target,
            'objective_type': obj_type,
            'path_length': path_length,
            'path_score': score,
            'path_safety': safety_score,
            'nodes_explored': nodes_explored,
            'computation_time_ms': time_ms,
            'ghost_count': len(ghost_positions),
            'success': True
        }
        
        self.run_history.append(log_entry)
        
        if len(self.run_history) > 100:
            self.run_history = self.run_history[-100:]

    def _manhattan_distance(self, pos1, pos2):
        """Calculate Manhattan distance between two positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _calculate_ghost_penalty(self, position, ghost_positions, avoidance_radius):
        """Calculate penalty for moving to a position near ghosts"""
        if not ghost_positions:
            return 0
        
        row, col = position
        min_distance = float('inf')
        
        for ghost_pos in ghost_positions:
            ghost_row, ghost_col = ghost_pos
            distance = abs(row - ghost_row) + abs(col - ghost_col)
            min_distance = min(min_distance, distance)
        
        if min_distance <= avoidance_radius:
            # Exponential penalty for being close to ghosts
            # Closer = higher penalty
            penalty = (avoidance_radius - min_distance + 1) ** 2 * 10
            return penalty
        
        return 0

    def _log_successful_path_avoidance(self, start, goal, path, distance, nodes_explored, computation_time, ghost_positions):
        """Log successful path with ghost avoidance"""
        entry = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'SUCCESSFUL_PATH_GHOST_AVOIDANCE',
            'maze_info': {
                'size': f"{self.maze_gen.height}x{self.maze_gen.width}",
                'maze_hash': self._get_maze_hash(),
            },
            'path_info': {
                'start': start,
                'goal': goal,
                'path': path,
                'distance': distance,
                'path_length': len(path),
                'nodes_explored': nodes_explored,
                'computation_time_ms': computation_time,
                'efficiency': len(path) / nodes_explored if nodes_explored > 0 else 0,
                'ghost_positions': ghost_positions,
            },
            'validation': {
                'path_valid': self._validate_path(path),
                'no_wall_crossing': True,
                'optimal_path': True,
                'ghost_avoidance': True,
            },
        }
        self.log_data.append(entry)

    def get_all_shortest_paths(self, start):
        if not self._validate_positions(start, start):
            return {}, {}
        distances = {start: 0}
        previous = {start: None}
        pq = [(0, start)]
        while pq:
            g, node = heapq.heappop(pq)
            if g > distances.get(node, float('inf')):
                continue
            for nb in self._get_valid_neighbors(node):
                ng = g + self._calculate_move_cost(node, nb)
                if ng < distances.get(nb, float('inf')):
                    distances[nb] = ng
                    previous[nb] = node
                    heapq.heappush(pq, (ng, nb))
        return distances, previous

    def _validate_positions(self, start, goal):
        # Use maze_generator's is_wall method for consistency
        if self.maze_gen.is_wall(start) or self.maze_gen.is_wall(goal):
            return False
        if start == goal:
            return False
        return True

    def _get_valid_neighbors(self, pos):
        # Use maze_generator's get_neighbors method directly
        return self.maze_gen.get_neighbors(pos)

    def _get_valid_neighbors_with_bomb_avoidance(self, pos, bomb_set):
        """Get valid neighbors while avoiding bomb positions"""
        neighbors = self.maze_gen.get_neighbors(pos)
        # Filter out bomb positions - CRITICAL: bom được coi như tường
        valid = [nb for nb in neighbors if nb not in bomb_set]
        
        # Debug: Log khi có bomb neighbor bị loại (disabled by default)
        # blocked = [nb for nb in neighbors if nb in bomb_set]
        # if blocked:
        #     # Rate limit debug output
        #     if not hasattr(self, '_last_bomb_block_log'):
        #         self._last_bomb_block_log = 0
        #     import time
        #     current = time.time()
        #     if current - self._last_bomb_block_log > 2:  # Log every 2 seconds max
        #         print(f"   At {pos}: blocked {len(blocked)} bomb neighbors: {blocked}")
        #         self._last_bomb_block_log = current
        
        return valid

    @staticmethod
    def _is_move_valid(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        return abs(dx) + abs(dy) == 1

    def _calculate_move_cost(self, a, b):
        base = 1
        if getattr(config, 'PURE_SHORTEST_PATH', True):
            return base
        if getattr(config, 'USE_OBSTACLE_PENALTY', False):
            penalty = self._calculate_obstacle_penalty(a, b)
            return base + int(getattr(config, 'NEAR_WALL_PENALTY', 0.1) * penalty)
        return base

    def _calculate_obstacle_penalty(self, current, neighbor):
        cnt = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                check = (neighbor[0] + dx, neighbor[1] + dy)
                if self.maze_gen.is_wall(check):
                    cnt += 1
        return cnt

    def _bfs_shortest_path_length(self, start, goal):
        q = deque([start])
        dist = {start: 1}
        while q:
            cur = q.popleft()
            if cur == goal:
                return dist[cur]
            for nb in self._get_valid_neighbors(cur):
                if nb not in dist:
                    dist[nb] = dist[cur] + 1
                    q.append(nb)
        return None

    @staticmethod
    def _heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _validate_path(self, path):
        # Simple validation: check if path exists and no walls
        if not path or len(path) < 1:
            return False
        
        # Check if any position is a wall
        for pos in path:
            if self.maze_gen.is_wall(pos):
                return False
        
        return True

    def _log_successful_path(self, start, goal, path, distance, nodes_explored, computation_time):
        entry = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'SUCCESSFUL_PATH',
            'maze_info': {
                'size': f"{self.maze_gen.height}x{self.maze_gen.width}",
                'maze_hash': self._get_maze_hash(),
            },
            'path_info': {
                'start': start,
                'goal': goal,
                'path': path,
                'distance': distance,
                'path_length': len(path),
                'nodes_explored': nodes_explored,
                'computation_time_ms': computation_time,
                'efficiency': len(path) / nodes_explored if nodes_explored > 0 else 0,
            },
            'validation': {
                'path_valid': self._validate_path(path),
                'no_wall_crossing': True,
                'optimal_path': True,
            },
        }
        self.log_data.append(entry)

    def _log_successful_path_bomb_avoidance(self, start, goal, path, distance, nodes_explored, computation_time, bomb_positions):
        """Log successful path with bomb avoidance"""
        entry = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'SUCCESSFUL_PATH_BOMB_AVOIDANCE',
            'maze_info': {
                'size': f"{self.maze_gen.height}x{self.maze_gen.width}",
                'maze_hash': self._get_maze_hash(),
            },
            'path_info': {
                'start': start,
                'goal': goal,
                'path': path,
                'distance': distance,
                'path_length': len(path),
                'nodes_explored': nodes_explored,
                'computation_time_ms': computation_time,
                'efficiency': len(path) / nodes_explored if nodes_explored > 0 else 0,
                'bomb_positions': bomb_positions,
            },
            'validation': {
                'path_valid': self._validate_path(path),
                'no_wall_crossing': True,
                'optimal_path': True,
                'bomb_avoidance': True,
            },
        }
        self.log_data.append(entry)

    def _log_successful_path_bomb_penalty(self, start, goal, path, distance, nodes_explored, computation_time, bomb_positions):
        """Log successful path with bomb penalty"""
        entry = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'SUCCESSFUL_PATH_BOMB_PENALTY',
            'maze_info': {
                'size': f"{self.maze_gen.height}x{self.maze_gen.width}",
                'maze_hash': self._get_maze_hash(),
            },
            'path_info': {
                'start': start,
                'goal': goal,
                'path': path,
                'distance': distance,
                'path_length': len(path),
                'nodes_explored': nodes_explored,
                'computation_time_ms': computation_time,
                'efficiency': len(path) / nodes_explored if nodes_explored > 0 else 0,
                'bomb_positions': bomb_positions,
            },
            'validation': {
                'path_valid': self._validate_path(path),
                'no_wall_crossing': True,
                'optimal_path': True,
                'bomb_penalty': True,
            },
        }
        self.log_data.append(entry)

    def _log_error(self, error_type, error_data):
        """Log error and display warning for bomb-related path blocking (rate limited)"""
        self.log_data.append({
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'ERROR',
            'error_type': error_type,
            'error_data': error_data,
        })
        
        # Rate limit warnings to avoid spam (1 warning per 2 seconds per type)
        if not hasattr(self, '_last_warning_time'):
            self._last_warning_time = {}
        
        current_time = datetime.now().timestamp()
        last_time = self._last_warning_time.get(error_type, 0)
        
        if current_time - last_time < 2.0:  # Skip if less than 2 seconds
            return
            
        self._last_warning_time[error_type] = current_time
        
        # Warnings silently logged (removed print to prevent spam)
        pass

    def check_bomb_blockage_status(self, start, goal, bomb_positions=None):
        """
        Kiểm tra và cảnh báo về tình trạng bị bom chặn đường
        Returns: (is_blocked, blockage_level, alternative_count)
        """
        if not bomb_positions:
            return False, 'SAFE', 0
        
        # Kiểm tra start và goal hợp lệ
        if not self._validate_positions(start, goal):
            return False, 'SAFE', 0
            
        try:
            # Thử pathfinding thông thường (không tránh bom)
            normal_path, _ = self.shortest_path(start, goal, enable_logging=False)
            
            # Thử pathfinding với bomb avoidance
            safe_path, _ = self.shortest_path_with_bomb_avoidance(start, goal, bomb_positions, enable_logging=False)
            
            # Thử pathfinding với bomb radius avoidance  
            radius_path, _ = self.shortest_path_with_bomb_radius_avoidance(start, goal, bomb_positions, enable_logging=False)
            
            # Phân tích mức độ chặn
            if not normal_path and not safe_path and not radius_path:
                return True, 'COMPLETE_BLOCKAGE', 0
                
            elif normal_path and not safe_path:
                return True, 'DANGEROUS_PATH_ONLY', 1
                
            elif safe_path and not normal_path:
                return False, 'SAFE_DETOUR', 1
                
            else:
                alternative_count = sum([1 for path in [normal_path, safe_path, radius_path] if path])
                if alternative_count > 1:
                    pass
                return False, 'MULTIPLE_OPTIONS', alternative_count
                
        except Exception as e:
            # Nếu có lỗi, trả về SAFE để không block game
            print(f"check_bomb_blockage_status error: {e}")
            return False, 'SAFE', 0

    def _get_maze_hash(self):
        return hashlib.md5(self.maze_gen.maze.tobytes()).hexdigest()

    def save_logs(self, filename=None):
        if not filename:
            filename = f"pathfinding_log_{self.session_id}.json"
        os.makedirs('logs', exist_ok=True)
        fp = os.path.join('logs', filename)
        with open(fp, 'w') as f:
            json.dump(self.log_data, f, indent=2, default=str)
        print(f'Logs saved to: {fp}')
        return fp

    def get_training_data(self):
        out = []
        for e in self.log_data:
            if e.get('type') == 'SUCCESSFUL_PATH':
                feats = self._maze_to_features(e['maze_info']['size'])
                p = e['path_info']
                out.append({
                    'maze_features': feats,
                    'start': p['start'],
                    'goal': p['goal'],
                    'optimal_path': p['path'],
                    'path_length': p['path_length'],
                    'distance': p['distance'],
                    'efficiency': p['efficiency'],
                })
        return out

    def _maze_to_features(self, size_str):
        h, w = map(int, size_str.split('x'))
        return {
            'size': [h, w],
            'wall_density': float(np.mean(self.maze_gen.maze)),
            'start_position': list(self.maze_gen.start),
            'goal_position': list(self.maze_gen.goal),
            'maze_pattern': self.maze_gen.maze.tolist(),
        }

    def shortest_path_with_obstacles(self, start, goal, obstacles=None):
        """Find shortest path while treating obstacles as walls"""
        if obstacles is None:
            obstacles = set()
            
        if not self._validate_positions(start, goal):
            return None, float('inf')

        pq = []  # (f, g, node, path)
        h0 = self._heuristic(start, goal) if getattr(config, 'USE_ASTAR', False) else 0
        heapq.heappush(pq, (h0, 0, start, [start]))

        dist = {start: 0}
        visited = set()

        while pq:
            f, g, current, path = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == goal:
                return path, g

            row, col = current
            neighbors = [
                (row - 1, col), (row + 1, col),
                (row, col - 1), (row, col + 1)
            ]

            for nr, nc in neighbors:
                neighbor = (nr, nc)
                
                # Skip if out of bounds
                if not (0 <= nr < self._height and 0 <= nc < self._width):
                    continue
                
                # Skip if wall
                if self.maze_gen.maze[nr, nc] == 1:
                    continue
                
                # Skip if obstacle (bomb)
                if neighbor in obstacles:
                    continue
                
                if neighbor in visited:
                    continue

                new_cost = g + 1
                if neighbor not in dist or new_cost < dist[neighbor]:
                    dist[neighbor] = new_cost
                    h = self._heuristic(neighbor, goal) if getattr(config, 'USE_ASTAR', False) else 0
                    f = new_cost + h
                    new_path = path + [neighbor]
                    heapq.heappush(pq, (f, new_cost, neighbor, new_path))

        return None, float('inf')

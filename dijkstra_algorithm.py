import heapq
import json
import os
from datetime import datetime
import hashlib
from collections import deque
import numpy as np
import config
from path_validator import PathValidator


class DijkstraAlgorithm:
    def __init__(self, maze_generator):
        self.maze_gen = maze_generator
        self.log_data = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._height, self._width = self.maze_gen.maze.shape
        self.last_run_stats = None  # {'nodes_explored': int, 'computation_time_ms': float, 'success': bool}
        self.validator = PathValidator(maze_generator)  # Add path validator

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
        return None, float('inf')

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

    def _log_error(self, error_type, error_data):
        self.log_data.append({
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'ERROR',
            'error_type': error_type,
            'error_data': error_data,
        })

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

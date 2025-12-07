"""
BFS Utilities for Pacman AI - Strategic Planning & Analysis
============================================================

BFS được sử dụng cho:
1. FLOOD FILL - Phân tích vùng có thể di chuyển
2. ESCAPE ROUTE ANALYSIS - Tìm lối thoát tối ưu khi bị ma/bom bao vây
3. MULTI-TARGET SEARCH - Tìm mục tiêu gần nhất trong nhiều targets
4. AREA CONTROL - Đánh giá kiểm soát khu vực

KHÔNG dùng BFS cho pathfinding chính (đã có A*/Dijkstra)
BFS là công cụ phân tích chiến thuật để hỗ trợ AI decision making
"""

import pygame
from collections import deque
from datetime import datetime
import math


class BFSUtilities:
    """
    BFS Utilities cho Pacman AI Strategic Planning
    Hỗ trợ AI tránh ma và bom thông minh hơn
    """
    
    def __init__(self, game_instance):
        """
        Khởi tạo BFS utilities
        
        Args:
            game_instance: Instance của PacmanGame
        """
        self.game = game_instance
        self.maze_gen = game_instance.maze_gen
        
        # Cache for performance optimization
        self.cache = {}
        self.cache_timeout = 500  # ms
        self.last_cache_clear = pygame.time.get_ticks()
        
        # Statistics
        self.stats = {
            'flood_fills': 0,
            'escape_routes_found': 0,
            'cache_hits': 0,
            'total_nodes_explored': 0
        }
    
    # ============================================================================
    # FLOOD FILL - Phân tích vùng có thể di chuyển
    # ============================================================================
    
    def flood_fill_reachable_area(self, start_pos, max_distance=12, 
                                   obstacles=None, return_distances=True):
        """
        FLOOD FILL: Tìm TẤT CẢ vị trí có thể reach được từ start_pos
        
        Use case:
        - Kiểm tra xem Pacman có bị kẹt/trapped không
        - Tính "freedom of movement" - càng nhiều ô reach được = càng an toàn
        - Phân tích xem bom/ma có block area không
        
        Args:
            start_pos: (row, col) vị trí bắt đầu
            max_distance: Khoảng cách tối đa để explore (default 12)
            obstacles: Set các vị trí cần tránh (bombs, ghosts)
            return_distances: Trả về khoảng cách đến mỗi vị trí
            
        Returns:
            nếu return_distances=True: dict {position: distance}
            nếu return_distances=False: set của positions
        """
        obstacles = obstacles or set()
        queue = deque([(start_pos, 0)])
        visited = {start_pos: 0} if return_distances else {start_pos}
        nodes_explored = 0
        
        while queue:
            current, distance = queue.popleft()
            nodes_explored += 1
            
            # Limit search depth
            if distance >= max_distance:
                continue
            
            # Explore neighbors
            for neighbor in self._get_valid_neighbors(current):
                # Skip obstacles
                if neighbor in obstacles:
                    continue
                
                # Skip if already visited
                if return_distances:
                    if neighbor in visited:
                        continue
                    visited[neighbor] = distance + 1
                else:
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                
                queue.append((neighbor, distance + 1))
        
        # Update stats
        self.stats['flood_fills'] += 1
        self.stats['total_nodes_explored'] += nodes_explored
        
        return visited
    
    def calculate_movement_freedom(self, pacman_pos, ghost_positions, 
                                   bomb_positions=None, radius=10):
        """
        Tính toán "tự do di chuyển" - metric quan trọng cho AI
        
        Use case:
        - Quyết định có nên aggressive hay defensive
        - Detect trapped situations sớm
        - Choose safer routes
        
        Args:
            pacman_pos: (row, col)
            ghost_positions: List[(row, col)]
            bomb_positions: List[(row, col)] hoặc None
            radius: Bán kính phân tích (default 10)
            
        Returns:
            dict {
                'total_reachable': int,
                'safe_positions': int,
                'danger_positions': int,
                'freedom_percentage': float,
                'is_trapped': bool,
                'threat_level': str
            }
        """
        bomb_positions = bomb_positions or []
        
        # FLOOD FILL để tìm tất cả positions có thể reach
        obstacles = set(bomb_positions)  # Bom là obstacles cứng
        reachable_with_distances = self.flood_fill_reachable_area(
            pacman_pos, max_distance=radius, obstacles=obstacles
        )
        
        total_reachable = len(reachable_with_distances)
        safe_positions = 0
        danger_positions = 0
        moderate_danger = 0
        
        # Phân tích từng position
        for pos, distance in reachable_with_distances.items():
            # Tính khoảng cách đến ma gần nhất
            min_ghost_dist = min(
                abs(pos[0] - g[0]) + abs(pos[1] - g[1])
                for g in ghost_positions
            ) if ghost_positions else float('inf')
            
            # Phân loại safety level
            if min_ghost_dist >= 6:
                safe_positions += 1
            elif min_ghost_dist >= 3:
                moderate_danger += 1
            else:
                danger_positions += 1
        
        # Calculate freedom percentage (chỉ tính safe + moderate)
        freedom_percentage = ((safe_positions + moderate_danger) / total_reachable * 100) \
                            if total_reachable > 0 else 0
        
        # Determine threat level
        if freedom_percentage >= 70:
            threat_level = 'SAFE'
        elif freedom_percentage >= 40:
            threat_level = 'MODERATE'
        elif freedom_percentage >= 20:
            threat_level = 'DANGEROUS'
        else:
            threat_level = 'TRAPPED'
        
        # Trapped nếu freedom < 25% hoặc safe positions < 5
        is_trapped = freedom_percentage < 25 or safe_positions < 5
        
        result = {
            'total_reachable': total_reachable,
            'safe_positions': safe_positions,
            'moderate_danger': moderate_danger,
            'danger_positions': danger_positions,
            'freedom_percentage': freedom_percentage,
            'is_trapped': is_trapped,
            'threat_level': threat_level,
            'analysis_time': pygame.time.get_ticks()
        }
        
        return result
    
    def check_area_blocked_by_bombs(self, start, goal, bomb_positions):
        """
        Kiểm tra xem bom có HOÀN TOÀN chặn đường từ start → goal không
        
        Use case:
        - Validate xem có thể đến goal không trước khi plan route
        - Cảnh báo sớm về bomb blockage
        - Quyết định có nên tìm đường khác không
        
        Args:
            start: (row, col)
            goal: (row, col)
            bomb_positions: List[(row, col)]
            
        Returns:
            dict {
                'is_blocked': bool,
                'reachable_from_start': int,
                'can_reach_goal': bool
            }
        """
        if start == goal:
            return {
                'is_blocked': False,
                'reachable_from_start': 1,
                'can_reach_goal': True
            }
        
        # FLOOD FILL from start, treating bombs as obstacles
        obstacles = set(bomb_positions)
        reachable = self.flood_fill_reachable_area(
            start, max_distance=999, obstacles=obstacles, return_distances=False
        )
        
        can_reach_goal = goal in reachable
        
        return {
            'is_blocked': not can_reach_goal,
            'reachable_from_start': len(reachable),
            'can_reach_goal': can_reach_goal,
            'blocking_bombs': len(bomb_positions)
        }
    
    # ============================================================================
    # ESCAPE ROUTE ANALYSIS - Tìm lối thoát tối ưu
    # ============================================================================
    
    def find_all_escape_routes(self, pacman_pos, ghost_positions, 
                               bomb_positions=None, min_safe_distance=8,
                               max_search_depth=15, max_routes=5):
        """
        ESCAPE ROUTE ANALYSIS: Tìm TẤT CẢ lối thoát an toàn
        
        Use case:
        - Emergency escape khi bị nhiều ma bao vây
        - Plan B, C, D... nếu route A bị block
        - Chọn route an toàn nhất (không chỉ ngắn nhất)
        
        Args:
            pacman_pos: (row, col)
            ghost_positions: List[(row, col)]
            bomb_positions: List[(row, col)] hoặc None
            min_safe_distance: Khoảng cách an toàn tối thiểu từ ma (default 8)
            max_search_depth: Độ sâu tìm kiếm tối đa (default 15)
            max_routes: Số lượng routes tối đa trả về (default 5)
            
        Returns:
            List[dict] sorted by safety_score, mỗi dict chứa:
            {
                'destination': (row, col),
                'path': List[(row, col)],
                'distance': int,
                'safety_score': float,
                'min_ghost_distance': float,
                'is_junction': bool,
                'escape_directions': List[str]
            }
        """
        bomb_positions = bomb_positions or []
        bomb_set = set(bomb_positions)
        
        queue = deque([(pacman_pos, 0, [pacman_pos])])
        visited = {pacman_pos}
        escape_routes = []
        nodes_explored = 0
        
        while queue and len(escape_routes) < max_routes * 2:  # Explore more to find best
            current, distance, path = queue.popleft()
            nodes_explored += 1
            
            # Calculate safety metrics for current position
            min_ghost_dist = min(
                abs(current[0] - g[0]) + abs(current[1] - g[1])
                for g in ghost_positions
            ) if ghost_positions else float('inf')
            
            # Calculate distance to nearest bomb
            min_bomb_dist = min(
                abs(current[0] - b[0]) + abs(current[1] - b[1])
                for b in bomb_positions
            ) if bomb_positions else float('inf')
            
            # Check if this is a valid escape destination
            is_safe_from_ghosts = min_ghost_dist >= min_safe_distance
            is_safe_from_bombs = min_bomb_dist >= 3 or not bomb_positions
            is_far_enough = distance >= 5  # Phải di chuyển ít nhất 5 bước
            
            if is_safe_from_ghosts and is_safe_from_bombs and is_far_enough:
                # Calculate comprehensive safety score
                safety_score = self._calculate_escape_safety_score(
                    current, ghost_positions, bomb_positions, distance
                )
                
                # Check if junction (có nhiều lối thoát từ đây)
                is_junction = self._is_junction(current)
                
                # Get escape directions available
                escape_dirs = self._get_escape_directions(current, ghost_positions)
                
                escape_routes.append({
                    'destination': current,
                    'path': path.copy(),
                    'distance': distance,
                    'safety_score': safety_score,
                    'min_ghost_distance': min_ghost_dist,
                    'min_bomb_distance': min_bomb_dist,
                    'is_junction': is_junction,
                    'escape_directions': escape_dirs,
                    'neighbor_count': len(self._get_valid_neighbors(current))
                })
            
            # Continue exploring if not too deep
            if distance < max_search_depth:
                for neighbor in self._get_valid_neighbors(current):
                    # Skip bombs
                    if neighbor in bomb_set:
                        continue
                    
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, distance + 1, path + [neighbor]))
        
        # Sort by safety score (highest first)
        escape_routes.sort(key=lambda x: (
            x['safety_score'],          # Primary: safety
            -x['distance'],              # Secondary: prefer closer (negative for reverse)
            x['is_junction']             # Tertiary: prefer junctions
        ), reverse=True)
        
        # Update stats
        self.stats['escape_routes_found'] += len(escape_routes)
        self.stats['total_nodes_explored'] += nodes_explored
        
        # Return top routes
        return escape_routes[:max_routes]
    
    def find_best_escape_direction(self, pacman_pos, ghost_positions, 
                                   bomb_positions=None):
        """
        Tìm HƯỚNG DI CHUYỂN TỐT NHẤT ngay lập tức để thoát hiểm
        
        Use case:
        - Emergency response khi ma quá gần
        - Quick decision making
        - Real-time escape planning
        
        Args:
            pacman_pos: (row, col)
            ghost_positions: List[(row, col)]
            bomb_positions: List[(row, col)] hoặc None
            
        Returns:
            dict {
                'direction': [dx, dy],
                'safety_score': float,
                'escape_route': dict (from find_all_escape_routes)
            } hoặc None nếu không có lối thoát
        """
        # Find escape routes
        escape_routes = self.find_all_escape_routes(
            pacman_pos, ghost_positions, bomb_positions,
            min_safe_distance=6, max_search_depth=10, max_routes=3
        )
        
        if not escape_routes:
            return None
        
        # Get best route
        best_route = escape_routes[0]
        
        # Get direction to first step of path
        if len(best_route['path']) < 2:
            return None
        
        next_pos = best_route['path'][1]  # Next position in path
        direction = [
            next_pos[1] - pacman_pos[1],  # dx (col)
            next_pos[0] - pacman_pos[0]   # dy (row)
        ]
        
        return {
            'direction': direction,
            'safety_score': best_route['safety_score'],
            'escape_route': best_route,
            'reason': 'BFS escape route analysis'
        }
    
    def find_safe_waiting_position(self, pacman_pos, ghost_positions, 
                                   bomb_positions=None, wait_radius=6):
        """
        Tìm vị trí AN TOÀN để "chờ" ma đi qua
        
        Use case:
        - Khi không thể đến goal ngay (bị ma chặn)
        - Cần chờ ghost pattern thay đổi
        - Defensive strategy
        
        Args:
            pacman_pos: (row, col)
            ghost_positions: List[(row, col)]
            bomb_positions: List[(row, col)] hoặc None
            wait_radius: Khoảng cách tìm kiếm (default 6)
            
        Returns:
            dict {
                'position': (row, col),
                'path': List[(row, col)],
                'safety_score': float,
                'has_multiple_exits': bool
            } hoặc None
        """
        bomb_positions = bomb_positions or []
        bomb_set = set(bomb_positions)
        
        queue = deque([(pacman_pos, 0, [pacman_pos])])
        visited = {pacman_pos}
        safe_positions = []
        
        while queue:
            current, distance, path = queue.popleft()
            
            if distance > wait_radius:
                continue
            
            # Calculate safety
            min_ghost_dist = min(
                abs(current[0] - g[0]) + abs(current[1] - g[1])
                for g in ghost_positions
            ) if ghost_positions else float('inf')
            
            # Safe position criteria
            if min_ghost_dist >= 5 and distance >= 2:
                # Check có nhiều exits không (junction)
                exits = self._get_valid_neighbors(current)
                has_multiple_exits = len(exits) >= 3
                
                safety_score = min_ghost_dist * 10
                if has_multiple_exits:
                    safety_score += 20  # Bonus for junctions
                
                safe_positions.append({
                    'position': current,
                    'path': path.copy(),
                    'distance': distance,
                    'safety_score': safety_score,
                    'min_ghost_distance': min_ghost_dist,
                    'has_multiple_exits': has_multiple_exits,
                    'exit_count': len(exits)
                })
            
            # Continue exploring
            for neighbor in self._get_valid_neighbors(current):
                if neighbor not in bomb_set and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1, path + [neighbor]))
        
        if not safe_positions:
            return None
        
        # Sort by safety score
        safe_positions.sort(key=lambda x: x['safety_score'], reverse=True)
        return safe_positions[0]
    
    # ============================================================================
    # MULTI-TARGET SEARCH - Tìm mục tiêu gần nhất
    # ============================================================================
    
    def find_nearest_target(self, start_pos, targets, obstacles=None, max_distance=50):
        """
        BFS tìm target GẦN NHẤT trong một set targets
        
        Use case:
        - Tìm dot gần nhất trong 50+ dots
        - Tìm power pellet gần nhất
        - Tốt hơn chạy A* 50 lần!
        
        Args:
            start_pos: (row, col)
            targets: Set hoặc List[(row, col)]
            obstacles: Set các vị trí cần tránh
            max_distance: Khoảng cách tối đa tìm kiếm
            
        Returns:
            dict {
                'target': (row, col),
                'path': List[(row, col)],
                'distance': int
            } hoặc None nếu không tìm thấy
        """
        if not targets:
            return None
        
        target_set = set(targets) if not isinstance(targets, set) else targets
        obstacles = obstacles or set()
        
        queue = deque([(start_pos, 0, [start_pos])])
        visited = {start_pos}
        
        while queue:
            current, distance, path = queue.popleft()
            
            # Found a target!
            if current in target_set:
                return {
                    'target': current,
                    'path': path,
                    'distance': distance
                }
            
            # Max distance check
            if distance >= max_distance:
                continue
            
            # Explore neighbors
            for neighbor in self._get_valid_neighbors(current):
                if neighbor not in obstacles and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1, path + [neighbor]))
        
        return None
    
    def find_k_nearest_targets(self, start_pos, targets, k=3, obstacles=None):
        """
        Tìm K targets GẦN NHẤT (thay vì chỉ 1)
        
        Use case:
        - Có nhiều options để chọn
        - Planning ahead với multiple goals
        
        Args:
            start_pos: (row, col)
            targets: Set hoặc List[(row, col)]
            k: Số lượng targets cần tìm (default 3)
            obstacles: Set các vị trí cần tránh
            
        Returns:
            List[dict] sorted by distance, mỗi dict chứa:
            {'target': (row, col), 'path': List, 'distance': int}
        """
        if not targets:
            return []
        
        target_set = set(targets) if not isinstance(targets, set) else targets
        obstacles = obstacles or set()
        
        queue = deque([(start_pos, 0, [start_pos])])
        visited = {start_pos}
        found_targets = []
        
        while queue and len(found_targets) < k:
            current, distance, path = queue.popleft()
            
            # Found a target!
            if current in target_set:
                found_targets.append({
                    'target': current,
                    'path': path.copy(),
                    'distance': distance
                })
                # Remove from target set
                target_set.discard(current)
            
            # Continue exploring
            for neighbor in self._get_valid_neighbors(current):
                if neighbor not in obstacles and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1, path + [neighbor]))
        
        return found_targets
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _get_valid_neighbors(self, position):
        """Lấy các vị trí láng giềng hợp lệ (không phải tường)"""
        row, col = position
        neighbors = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if self.game.is_valid_position(new_col, new_row):
                neighbors.append((new_row, new_col))
        
        return neighbors
    
    def _is_junction(self, position):
        """Kiểm tra vị trí có phải là ngã rẽ không (≥3 hướng đi)"""
        return len(self._get_valid_neighbors(position)) >= 3
    
    def _calculate_escape_safety_score(self, position, ghost_positions, 
                                       bomb_positions, distance):
        """
        Tính safety score cho escape route
        Higher score = safer
        """
        score = 0.0
        
        # 1. Distance from ghosts (most important)
        if ghost_positions:
            min_ghost_dist = min(
                abs(position[0] - g[0]) + abs(position[1] - g[1])
                for g in ghost_positions
            )
            score += min_ghost_dist * 15  # Heavy weight
            
            # Average distance to all ghosts
            avg_ghost_dist = sum(
                abs(position[0] - g[0]) + abs(position[1] - g[1])
                for g in ghost_positions
            ) / len(ghost_positions)
            score += avg_ghost_dist * 5
        else:
            score += 100  # No ghosts = very safe
        
        # 2. Distance from bombs
        if bomb_positions:
            min_bomb_dist = min(
                abs(position[0] - b[0]) + abs(position[1] - b[1])
                for b in bomb_positions
            )
            score += min_bomb_dist * 8
        
        # 3. Junction bonus (nhiều lối thoát)
        if self._is_junction(position):
            score += 25
        
        # 4. Path length penalty (không muốn quá xa)
        score -= distance * 2
        
        return score
    
    def _get_escape_directions(self, position, ghost_positions):
        """
        Lấy các hướng có thể escape từ position
        Trả về list các hướng: ['up', 'down', 'left', 'right']
        """
        directions = []
        direction_map = {
            (-1, 0): 'up',
            (1, 0): 'down',
            (0, -1): 'left',
            (0, 1): 'right'
        }
        
        neighbors = self._get_valid_neighbors(position)
        
        for neighbor in neighbors:
            # Check if moving to neighbor increases distance from nearest ghost
            if ghost_positions:
                current_min_dist = min(
                    abs(position[0] - g[0]) + abs(position[1] - g[1])
                    for g in ghost_positions
                )
                neighbor_min_dist = min(
                    abs(neighbor[0] - g[0]) + abs(neighbor[1] - g[1])
                    for g in ghost_positions
                )
                
                # Only include if moving away from ghost
                if neighbor_min_dist >= current_min_dist:
                    dr = neighbor[0] - position[0]
                    dc = neighbor[1] - position[1]
                    directions.append(direction_map[(dr, dc)])
            else:
                # No ghosts, all directions are escape directions
                dr = neighbor[0] - position[0]
                dc = neighbor[1] - position[1]
                directions.append(direction_map[(dr, dc)])
        
        return directions
    
    def clear_cache(self):
        """Clear cache để tránh memory leak"""
        self.cache.clear()
        self.last_cache_clear = pygame.time.get_ticks()
    
    def get_statistics(self):
        """Lấy thống kê sử dụng BFS"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset statistics"""
        self.stats = {
            'flood_fills': 0,
            'escape_routes_found': 0,
            'cache_hits': 0,
            'total_nodes_explored': 0
        }

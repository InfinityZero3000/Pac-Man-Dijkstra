"""
A* Algorithm Implementation for Pacman Game
Thuật toán A* tìm đường đi ngắn nhất sử dụng heuristic (Manhattan distance)
"""

import heapq
from datetime import datetime


class AStarAlgorithm:
    """
    A* pathfinding algorithm với heuristic Manhattan distance
    Hiệu quả hơn Dijkstra nhờ ưu tiên các node gần đích
    """
    
    def __init__(self, maze_generator):
        self.maze_gen = maze_generator
        self.maze = maze_generator.maze
        
        # Statistics tracking
        self.nodes_explored = 0
        self.computation_time_ms = 0.0
        self.path_length = 0
        
    def manhattan_distance(self, pos1, pos2):
        """
        Heuristic function: Manhattan distance
        Khoảng cách Manhattan giữa 2 điểm (|x1-x2| + |y1-y2|)
        """
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def is_valid_position(self, row, col):
        """Kiểm tra vị trí có hợp lệ không (trong bounds và không phải tường)"""
        if 0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width:
            return self.maze[row, col] == 0  # 0 = đường đi, 1 = tường
        return False
    
    def get_neighbors(self, position):
        """Lấy các vị trí kề hợp lệ (up, down, left, right)"""
        row, col = position
        neighbors = []
        
        # 4 hướng: lên, xuống, trái, phải
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_position(new_row, new_col):
                neighbors.append((new_row, new_col))
        
        return neighbors
    
    def shortest_path(self, start, goal, obstacles=None):
        """
        Tìm đường đi ngắn nhất từ start đến goal sử dụng A*
        
        Args:
            start: tuple (row, col) - điểm bắt đầu
            goal: tuple (row, col) - điểm đích
            obstacles: list of tuples - danh sách vị trí cần tránh (bombs, ghosts)
        
        Returns:
            path: list of tuples - đường đi từ start đến goal
            distance: int - độ dài đường đi
        """
        # Reset statistics
        self.nodes_explored = 0
        start_time = datetime.now()
        
        # Chuyển đổi obstacles thành set để tìm kiếm nhanh
        obstacles_set = set(obstacles) if obstacles else set()
        
        # Priority queue: (f_score, counter, current_pos, g_score, path)
        # f_score = g_score + h_score
        # counter để đảm bảo thứ tự ổn định khi f_score bằng nhau
        counter = 0
        h_score = self.manhattan_distance(start, goal)
        pq = [(h_score, counter, start, 0, [start])]
        
        # Dictionary lưu g_score tốt nhất đến mỗi node
        g_scores = {start: 0}
        
        # Set các node đã thăm
        visited = set()
        
        while pq:
            f_score, _, current_pos, g_score, path = heapq.heappop(pq)
            
            # Nếu đã thăm node này với g_score tốt hơn, bỏ qua
            if current_pos in visited:
                continue
            
            visited.add(current_pos)
            self.nodes_explored += 1
            
            # Kiểm tra đã đến đích chưa
            if current_pos == goal:
                self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.path_length = len(path)
                return path, g_score
            
            # Explore các node kề
            for neighbor in self.get_neighbors(current_pos):
                # Bỏ qua nếu là obstacle
                if neighbor in obstacles_set:
                    continue
                
                # Bỏ qua nếu đã thăm
                if neighbor in visited:
                    continue
                
                # Tính g_score mới (mỗi bước có cost = 1)
                new_g_score = g_score + 1
                
                # Chỉ xử lý nếu tìm được đường tốt hơn
                if neighbor not in g_scores or new_g_score < g_scores[neighbor]:
                    g_scores[neighbor] = new_g_score
                    
                    # Tính f_score = g_score + h_score
                    h_score = self.manhattan_distance(neighbor, goal)
                    new_f_score = new_g_score + h_score
                    
                    # Thêm vào priority queue
                    counter += 1
                    new_path = path + [neighbor]
                    heapq.heappush(pq, (new_f_score, counter, neighbor, new_g_score, new_path))
        
        # Không tìm thấy đường đi
        self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return None, float('inf')
    
    def shortest_path_avoiding_ghosts(self, start, goal, ghost_positions, 
                                      avoidance_radius=3, bomb_positions=None):
        """
        Tìm đường đi ngắn nhất tránh ma và bom
        
        Args:
            start: tuple (row, col)
            goal: tuple (row, col)
            ghost_positions: list of tuples - vị trí các ma
            avoidance_radius: int - bán kính tránh ma
            bomb_positions: list of tuples - vị trí các bom
        
        Returns:
            path, distance
        """
        # Tạo danh sách các ô cần tránh
        obstacles = set()
        
        # Thêm bom vào obstacles
        if bomb_positions:
            obstacles.update(bomb_positions)
        
        # Thêm các ô xung quanh ma vào obstacles
        for ghost_pos in ghost_positions:
            ghost_row, ghost_col = ghost_pos
            
            # Tạo vùng tránh xung quanh ma
            for dr in range(-avoidance_radius, avoidance_radius + 1):
                for dc in range(-avoidance_radius, avoidance_radius + 1):
                    avoid_row = ghost_row + dr
                    avoid_col = ghost_col + dc
                    
                    # Kiểm tra Manhattan distance
                    if abs(dr) + abs(dc) <= avoidance_radius:
                        if self.is_valid_position(avoid_row, avoid_col):
                            obstacles.add((avoid_row, avoid_col))
        
        # Đảm bảo start và goal không bị block (trừ khi chúng là bomb)
        if start in obstacles and (not bomb_positions or start not in bomb_positions):
            obstacles.discard(start)
        if goal in obstacles and (not bomb_positions or goal not in bomb_positions):
            obstacles.discard(goal)
        
        # Tìm đường với obstacles
        return self.shortest_path(start, goal, obstacles=obstacles)
    
    def get_next_move(self, current_pos, target_pos, obstacles=None):
        """
        Lấy bước di chuyển tiếp theo từ current_pos đến target_pos
        
        Returns:
            (row, col) - vị trí tiếp theo, hoặc None nếu không có đường
        """
        path, _ = self.shortest_path(current_pos, target_pos, obstacles)
        
        if path and len(path) > 1:
            return path[1]  # Bước tiếp theo (path[0] là vị trí hiện tại)
        
        return None
    
    def get_statistics(self):
        """Lấy thống kê thuật toán"""
        return {
            'algorithm': 'A* (Manhattan)',
            'nodes_explored': self.nodes_explored,
            'computation_time_ms': self.computation_time_ms,
            'path_length': self.path_length
        }


# Test function
if __name__ == "__main__":
    from maze_generator import MazeGenerator
    
    print("Testing A* Algorithm...")
    
    # Tạo maze
    maze_gen = MazeGenerator(21, 21, complexity=0.75)
    maze, start, goal = maze_gen.generate_maze()
    
    # Khởi tạo A*
    astar = AStarAlgorithm(maze_gen)
    
    # Test 1: Đường đi cơ bản
    print("\n=== Test 1: Basic Pathfinding ===")
    path, distance = astar.shortest_path(start, goal)
    stats = astar.get_statistics()
    
    print(f"Start: {start}")
    print(f"Goal: {goal}")
    print(f"Path found: {path is not None}")
    print(f"Path length: {stats['path_length']}")
    print(f"Distance: {distance}")
    print(f"Nodes explored: {stats['nodes_explored']}")
    print(f"Computation time: {stats['computation_time_ms']:.2f}ms")
    
    # Test 2: Tránh obstacles
    print("\n=== Test 2: Avoiding Obstacles ===")
    # Tạo một vài obstacles giả
    obstacles = [(5, 5), (5, 6), (5, 7)]
    path2, distance2 = astar.shortest_path(start, goal, obstacles)
    stats2 = astar.get_statistics()
    
    print(f"Obstacles: {len(obstacles)}")
    print(f"Path found: {path2 is not None}")
    print(f"Path length: {stats2['path_length']}")
    print(f"Nodes explored: {stats2['nodes_explored']}")
    print(f"Computation time: {stats2['computation_time_ms']:.2f}ms")
    
    # Test 3: Tránh ma
    print("\n=== Test 3: Avoiding Ghosts ===")
    ghost_positions = [(10, 10), (15, 15)]
    path3, distance3 = astar.shortest_path_avoiding_ghosts(start, goal, ghost_positions, 
                                                            avoidance_radius=3)
    stats3 = astar.get_statistics()
    
    print(f"Ghost positions: {ghost_positions}")
    print(f"Avoidance radius: 3")
    print(f"Path found: {path3 is not None}")
    print(f"Path length: {stats3['path_length']}")
    print(f"Nodes explored: {stats3['nodes_explored']}")
    print(f"Computation time: {stats3['computation_time_ms']:.2f}ms")
    
    print("\n✅ A* Algorithm tests completed!")

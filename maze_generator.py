import random
import numpy as np

class MazeGenerator:
    def __init__(self, width=21, height=21, complexity=0.25):
        self.width = width if width % 2 == 1 else width + 1 
        self.height = height if height % 2 == 1 else height + 1
        self.complexity = complexity  # Controls how many paths are created (0.5-1.0)
        self.maze = np.ones((self.height, self.width), dtype=int)
        self.start = None
        self.goal = None
        self.bomb_positions = []  # Grid coordinates (row, col) for bombs

    def generate_maze(self):
        # Initialize maze with walls
        self.maze = np.ones((self.height, self.width), dtype=int)

        # Generate maze using randomized DFS from single start
        stack = []
        start_row, start_col = 1, 1
        self.maze[start_row, start_col] = 0
        stack.append((start_row, start_col))

        while stack:
            x, y = stack[-1]  # x=row, y=col
            neighbors = self.get_unvisited_neighbors(x, y)
            if neighbors:
                nx, ny = random.choice(neighbors)  # nx=row, ny=col
                self.maze[nx, ny] = 0
                # Remove wall between current and neighbor
                self.maze[(x + nx) // 2, (y + ny) // 2] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        # Add additional paths to reduce dead ends
        self.add_additional_paths()

        # Set start and goal
        self.start = (1, 1)  # (row, col)
        self.goal = (self.height - 2, self.width - 2)  # (row, col)
        self.maze[self.goal[0], self.goal[1]] = 0  # Ensure goal is open

        # Generate bomb positions AFTER maze is complete
        self.generate_bomb_positions(max_bombs=5)

        return self.maze, self.start, self.goal

    def add_additional_paths(self):
        """Add additional paths to reduce dead ends and create more escape routes"""
        # Find potential dead ends (positions with only one neighbor)
        dead_ends = []
        for i in range(1, self.height - 1):
            for j in range(1, self.width - 1):
                if self.maze[i, j] == 0:
                    neighbors = self.get_neighbors((i, j))
                    if len(neighbors) == 1:  # Dead end
                        dead_ends.append((i, j))

        # Connect some dead ends to nearby paths
        for dead_end in dead_ends[:len(dead_ends)//2]:  # Only fix half to keep some challenge
            self.connect_dead_end(dead_end)

    def connect_dead_end(self, position):
        """Connect a dead end to a nearby path by removing walls"""
        x, y = position
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        # Try to connect to adjacent walls that lead to open areas
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if (0 < nx < self.height - 1 and 0 < ny < self.width - 1 and 
                self.maze[nx, ny] == 1):  # Wall
                # Check if removing this wall opens to a path
                nnx, nny = nx + dx, ny + dy
                if (0 <= nnx < self.height and 0 <= nny < self.width and 
                    self.maze[nnx, nny] == 0):
                    self.maze[nx, ny] = 0
                    break

    def get_unvisited_neighbors(self, x, y):
        neighbors = []
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < self.height - 1 and 0 < ny < self.width - 1 and self.maze[nx, ny] == 1:
                neighbors.append((nx, ny))
        return neighbors

    def is_wall(self, position):
        x, y = position
        if 0 <= x < self.height and 0 <= y < self.width:
            return self.maze[x, y] == 1
        return True

    def is_valid_position(self, row, col):
        """Check if position is valid (within bounds and not a wall)"""
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.maze[row, col] == 0  # 0 means open space
        return False

    def get_neighbors(self, position):
        x, y = position
        neighbors = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if not self.is_wall((nx, ny)):
                neighbors.append((nx, ny))
        return neighbors

    def display_maze(self):
        for row in self.maze:
            print(''.join(['#' if cell == 1 else ' ' for cell in row]))

    def generate_bomb_positions(self, max_bombs=5):
        """
        Generate valid bomb positions on the maze paths.
        Bombs are stored as grid coordinates (row, col).
        This ensures bombs are ALWAYS valid and synchronized with maze generation.
        """
        import math
        
        self.bomb_positions = []
        
        # Step 1: Collect ALL valid path positions
        valid_positions = []
        for row in range(self.height):
            for col in range(self.width):
                # Must be a path (0)
                if self.maze[row, col] != 0:
                    continue
                
                # Skip start and goal
                if (row, col) == self.start or (row, col) == self.goal:
                    continue
                
                # Must be at least 5 cells away from start and goal
                start_dist = math.sqrt((col - self.start[1])**2 + (row - self.start[0])**2)
                goal_dist = math.sqrt((col - self.goal[1])**2 + (row - self.goal[0])**2)
                if start_dist <= 5 or goal_dist <= 5:
                    continue
                
                # Check adjacent paths (only 4 directions: up, down, left, right)
                # Bomb should only be placed at intersections (3+ paths) to avoid blocking corridors
                path_up = 0 <= row-1 < self.height and self.maze[row-1, col] == 0
                path_down = 0 <= row+1 < self.height and self.maze[row+1, col] == 0
                path_left = 0 <= col-1 < self.width and self.maze[row, col-1] == 0
                path_right = 0 <= col+1 < self.width and self.maze[row, col+1] == 0
                
                adjacent_paths = sum([path_up, path_down, path_left, path_right])
                
                # STRICT: Only allow bombs at intersections (3 or 4 adjacent paths)
                # This ensures bombs are never placed in narrow corridors or corners
                if adjacent_paths < 3:
                    continue
                
                valid_positions.append((row, col))
        
        if not valid_positions:
            print("MazeGenerator: No valid positions for bombs")
            return
        
        print(f"MazeGenerator: Found {len(valid_positions)} valid bomb positions")
        
        # Step 2: Use pathfinding to select bomb positions that don't block the path
        # Import here to avoid circular dependency
        try:
            from dijkstra_algorithm import DijkstraAlgorithm
            dijkstra = DijkstraAlgorithm(self)
            
            # Verify initial path exists
            initial_path, initial_distance = dijkstra.shortest_path(self.start, self.goal)
            if not initial_path:
                print("MazeGenerator: No path from start to goal!")
                return
            
            print(f"MazeGenerator: Initial path length: {initial_distance} steps")
            
            # Shuffle and try positions
            random.shuffle(valid_positions)
            selected_bombs = []
            
            for candidate in valid_positions:
                if len(selected_bombs) >= max_bombs:
                    break
                
                row, col = candidate
                
                # Check distance from goal again
                goal_dist = math.sqrt((col - self.goal[1])**2 + (row - self.goal[0])**2)
                if goal_dist <= 5:
                    continue
                
                # Check distance from other bombs
                too_close = any(
                    math.sqrt((col - bc)**2 + (row - br)**2) < 5
                    for br, bc in selected_bombs
                )
                if too_close:
                    continue
                
                # Skip if on critical initial path
                if initial_path and (row, col) in initial_path[:max(3, len(initial_path)//3)]:
                    continue
                
                # Test if adding this bomb still allows path to goal
                # Use shortest_path_with_bomb_avoidance to match runtime behavior
                temp_bombs = selected_bombs + [(row, col)]
                path, distance = dijkstra.shortest_path_with_bomb_avoidance(
                    self.start, self.goal, temp_bombs, bomb_positions_are_grid=True, enable_logging=False
                )
                
                if path and distance <= initial_distance * 1.5:
                    selected_bombs.append((row, col))
                    print(f"MazeGenerator: Bomb #{len(selected_bombs)} at Grid({row}, {col}) - Path still exists ({distance} steps)")
            
            # Final verification with bomb avoidance
            if selected_bombs:
                final_path, final_dist = dijkstra.shortest_path_with_bomb_avoidance(
                    self.start, self.goal, selected_bombs, bomb_positions_are_grid=True, enable_logging=False
                )
                if final_path:
                    self.bomb_positions = selected_bombs
                    print(f"MazeGenerator: {len(self.bomb_positions)} bombs generated successfully")
                    
                    # Verify each bomb is on a path
                    for i, (row, col) in enumerate(self.bomb_positions, 1):
                        maze_value = self.maze[row, col]
                        if maze_value != 0:
                            print(f"ERROR: Bomb {i} at ({row}, {col}) is NOT on path! Maze value: {maze_value}")
                        else:
                            print(f"   Bomb {i}: Grid({row}, {col}) - On path (maze[{row},{col}]=0)")
                else:
                    print("MazeGenerator: Final verification failed - no bombs added")
                    self.bomb_positions = []
            else:
                print("MazeGenerator: No suitable bomb positions found")
                
        except ImportError as e:
            print(f"MazeGenerator: Cannot import pathfinding, using simple placement: {e}")
            # Fallback: simple random selection
            selected = random.sample(valid_positions, min(max_bombs, len(valid_positions)))
            self.bomb_positions = selected
            print(f"MazeGenerator: {len(self.bomb_positions)} bombs placed (simple mode)")

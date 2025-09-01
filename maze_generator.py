import random
import numpy as np

class MazeGenerator:
    def __init__(self, width=21, height=21, complexity=0.25):
        self.width = width if width % 2 == 1 else width + 1  # Ensure odd size
        self.height = height if height % 2 == 1 else height + 1
        self.complexity = complexity  # Controls how many paths are created (0.5-1.0)
        self.maze = np.ones((self.height, self.width), dtype=int)
        self.start = None
        self.goal = None

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

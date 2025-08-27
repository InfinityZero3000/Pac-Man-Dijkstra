import random
import numpy as np

class MazeGenerator:
    def __init__(self, width=41, height=41, complexity=0.75):
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

        # Set start and goal
        self.start = (1, 1)  # (row, col)
        self.goal = (self.height - 2, self.width - 2)  # (row, col)
        self.maze[self.goal[0], self.goal[1]] = 0  # Ensure goal is open

        return self.maze, self.start, self.goal

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

import pygame
import sys
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm
from path_validator import PathValidator

class MazeGame:
    def __init__(self, width=41, height=41, cell_size=12):
        self.maze_gen = MazeGenerator(width, height)
        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
        self.path_validator = PathValidator(self.maze_gen)  # Add path validator
        self.cell_size = cell_size
        self.screen_width = width * cell_size
        self.screen_height = height * cell_size
        
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Maze Game - Pacman Style")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.YELLOW = (255, 255, 0)
        self.BLUE = (0, 0, 255)
        self.GREEN = (0, 255, 0)
        self.RED = (255, 0, 0)
        
        # Generate maze with connectivity check
        max_attempts = 10
        for attempt in range(max_attempts):
            self.maze, self.start, self.goal = self.maze_gen.generate_maze()
            path, _ = self.dijkstra.shortest_path(self.start, self.goal)
            if path is not None:
                break
        else:
            print("Warning: Could not generate connected maze after", max_attempts, "attempts")
        
        # Player position - convert from maze coordinates (row,col) to screen (col,row)
        start_row, start_col = self.start
        self.player_pos = [start_col, start_row]  # [col, row] for screen coordinates
        
        # Path
        self.path = []
        self.show_path = False
        
        # Game state
        self.running = True
        self.game_won = False

    def draw_maze(self):
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                rect = pygame.Rect(x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)
                if self.maze[y, x] == 1:  # Wall
                    pygame.draw.rect(self.screen, self.BLUE, rect)
                else:  # Path
                    pygame.draw.rect(self.screen, self.BLACK, rect)
                    pygame.draw.rect(self.screen, self.WHITE, rect, 1)  # Border

    def draw_player(self):
        # player_pos is [col, row] but we need to convert properly
        col, row = self.player_pos
        center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
        pygame.draw.circle(self.screen, self.YELLOW, center, self.cell_size // 3)

    def draw_goal(self):
        # goal is (row, col) from maze_generator
        row, col = self.goal
        center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
        pygame.draw.circle(self.screen, self.GREEN, center, self.cell_size // 3)

    def draw_path(self):
        if self.show_path and self.path:
            for pos in self.path:
                # pos is (row, col) from maze coordinates
                row, col = pos
                # Check if position is valid using maze array directly
                if (0 <= row < self.maze_gen.height and 
                    0 <= col < self.maze_gen.width and 
                    self.maze[row, col] == 0):  # 0 = open path, 1 = wall
                    # Convert to screen coordinates: col=x, row=y
                    center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
                    pygame.draw.circle(self.screen, self.RED, center, self.cell_size // 6)

    def move_player(self, dx, dy):
        # player_pos is [col, row], dx/dy are screen deltas
        new_col = self.player_pos[0] + dx
        new_row = self.player_pos[1] + dy
        
        # Check if new position is valid using maze coordinates (row, col)
        if not self.maze_gen.is_wall((new_row, new_col)):
            self.player_pos = [new_col, new_row]
            if (new_row, new_col) == self.goal:
                self.game_won = True

    def find_path(self):
        # Clear previous path first
        self.path = []
        self.show_path = False
        
        # Convert player_pos from [col, row] to (row, col) for pathfinding
        player_row = self.player_pos[1]
        player_col = self.player_pos[0]
        start_pos = (player_row, player_col)
        
        path, distance = self.dijkstra.shortest_path(start_pos, self.goal)
        if path:
            # Validate path manually - check each position in maze array
            valid_path = []
            for pos in path:
                row, col = pos
                if (0 <= row < self.maze_gen.height and 
                    0 <= col < self.maze_gen.width and 
                    self.maze[row, col] == 0):  # 0 = open path
                    valid_path.append(pos)
                else:
                    print(f"Invalid position in path: {pos} - maze[{row},{col}] = {self.maze[row, col] if 0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width else 'out of bounds'}")
            
            if valid_path:
                self.path = valid_path
                self.show_path = True
                print(f"Found valid path with {len(valid_path)} steps")
            else:
                print("All path positions are invalid!")
        else:
            print("No path found!")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.find_path()
                elif event.key == pygame.K_r:
                    # Reset game with connectivity check
                    max_attempts = 10
                    for attempt in range(max_attempts):
                        self.maze, self.start, self.goal = self.maze_gen.generate_maze()
                        # Update validator with new maze
                        self.path_validator = PathValidator(self.maze_gen)
                        # Update dijkstra with new maze
                        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
                        path, _ = self.dijkstra.shortest_path(self.start, self.goal)
                        if path is not None:
                            break
                    start_row, start_col = self.start
                    self.player_pos = [start_col, start_row]  # Reset to [col, row]
                    self.path = []
                    self.show_path = False
                    self.game_won = False
                elif not self.game_won:
                    if event.key == pygame.K_UP:
                        self.move_player(0, -1)
                    elif event.key == pygame.K_DOWN:
                        self.move_player(0, 1)
                    elif event.key == pygame.K_LEFT:
                        self.move_player(-1, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.move_player(1, 0)

    def draw_text(self, text, position):
        text_surface = self.font.render(text, True, self.WHITE)
        self.screen.blit(text_surface, position)

    def run(self):
        while self.running:
            self.handle_events()
            
            self.screen.fill(self.BLACK)
            self.draw_maze()
            self.draw_goal()
            self.draw_path()
            self.draw_player()
            
            if self.game_won:
                self.draw_text("You Win! Press R to restart", (10, self.screen_height - 30))
            else:
                self.draw_text("Use arrow keys to move, SPACE to find path, R to reset", (10, self.screen_height - 30))
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = MazeGame()
    game.run()

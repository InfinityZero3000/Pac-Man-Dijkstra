"""
Algorithm Comparison Tool - Dijkstra vs A*
So sánh trực quan hai thuật toán tìm đường trên cùng một mê cung
"""

import pygame
import sys
import heapq
import math
from datetime import datetime
from maze_generator import MazeGenerator
import numpy as np

class PathfindingAlgorithm:
    """Base class for pathfinding algorithms"""
    def __init__(self, maze_generator):
        self.maze_gen = maze_generator
        self.nodes_explored = 0
        self.computation_time_ms = 0.0
        self.path = []
        self.visited = set()
        self.current_node = None
        
    def reset_stats(self):
        """Reset algorithm statistics"""
        self.nodes_explored = 0
        self.computation_time_ms = 0.0
        self.path = []
        self.visited = set()
        self.current_node = None
        
    def is_valid_position(self, row, col):
        """Check if position is valid (within bounds and not a wall)"""
        if 0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width:
            return self.maze_gen.maze[row, col] == 0
        return False
        
    def get_neighbors(self, position):
        """Get valid neighboring positions"""
        row, col = position
        neighbors = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_position(new_row, new_col):
                neighbors.append((new_row, new_col))
        return neighbors


class DijkstraPathfinder(PathfindingAlgorithm):
    """Dijkstra algorithm implementation"""
    def __init__(self, maze_generator):
        super().__init__(maze_generator)
        self.algorithm_name = "Dijkstra"
        
    def find_path(self, start, goal):
        """Find shortest path using Dijkstra's algorithm"""
        self.reset_stats()
        start_time = datetime.now()
        
        # Priority queue: (distance, node, path)
        pq = [(0, start, [start])]
        distances = {start: 0}
        self.visited = set()
        
        while pq:
            current_dist, current_node, path = heapq.heappop(pq)
            
            if current_node in self.visited:
                continue
                
            self.visited.add(current_node)
            self.nodes_explored += 1
            self.current_node = current_node
            
            # Check if reached goal
            if current_node == goal:
                self.path = path
                self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return path, current_dist
                
            # Explore neighbors
            for neighbor in self.get_neighbors(current_node):
                new_dist = current_dist + 1  # Each step has cost 1
                
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    new_path = path + [neighbor]
                    heapq.heappush(pq, (new_dist, neighbor, new_path))
        
        self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return None, float('inf')


class AStarPathfinder(PathfindingAlgorithm):
    """A* algorithm implementation"""
    def __init__(self, maze_generator):
        super().__init__(maze_generator)
        self.algorithm_name = "A* (Manhattan)"
        
    def heuristic(self, pos1, pos2):
        """Manhattan distance heuristic"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
        
    def find_path(self, start, goal):
        """Find shortest path using A* algorithm"""
        self.reset_stats()
        start_time = datetime.now()
        
        # Priority queue: (f_score, g_score, node, path)
        # f_score = g_score + h_score
        h_start = self.heuristic(start, goal)
        pq = [(h_start, 0, start, [start])]
        g_scores = {start: 0}
        self.visited = set()
        
        while pq:
            f_score, g_score, current_node, path = heapq.heappop(pq)
            
            if current_node in self.visited:
                continue
                
            self.visited.add(current_node)
            self.nodes_explored += 1
            self.current_node = current_node
            
            # Check if reached goal
            if current_node == goal:
                self.path = path
                self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return path, g_score
                
            # Explore neighbors
            for neighbor in self.get_neighbors(current_node):
                new_g_score = g_score + 1  # Each step has cost 1
                
                if neighbor not in g_scores or new_g_score < g_scores[neighbor]:
                    g_scores[neighbor] = new_g_score
                    h_score = self.heuristic(neighbor, goal)
                    new_f_score = new_g_score + h_score
                    new_path = path + [neighbor]
                    heapq.heappush(pq, (new_f_score, new_g_score, neighbor, new_path))
        
        self.computation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return None, float('inf')


class AlgorithmComparison:
    """Main comparison visualization class"""
    def __init__(self, maze_width=41, maze_height=31, cell_size=20):
        # Maze generation
        self.maze_gen = MazeGenerator(maze_width, maze_height, complexity=0.75)
        self.maze, self.start, self.goal = self.maze_gen.generate_maze()
        
        # Display settings
        self.cell_size = cell_size
        self.maze_width = maze_width * cell_size
        self.maze_height = maze_height * cell_size
        self.ui_panel_height = 180
        
        # Screen dimensions: two mazes side by side + UI panel
        self.screen_width = self.maze_width * 2 + 3  # +3 for divider line
        self.screen_height = self.maze_height + self.ui_panel_height
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Algorithm Comparison: Dijkstra vs A*")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_small = pygame.font.SysFont("arial", 14)
        self.font_medium = pygame.font.SysFont("arial", 18, bold=True)
        self.font_large = pygame.font.SysFont("arial", 24, bold=True)
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GRAY = (128, 128, 128)
        self.DARK_GRAY = (50, 50, 50)
        self.BLUE = (33, 150, 243)
        self.GREEN = (76, 175, 80)
        self.RED = (244, 67, 54)
        self.YELLOW = (255, 235, 59)
        self.CYAN = (0, 255, 255)
        self.ORANGE = (255, 152, 0)
        self.PURPLE = (156, 39, 176)
        self.LIGHT_BLUE = (135, 206, 250)
        
        # Initialize algorithms
        self.dijkstra = DijkstraPathfinder(self.maze_gen)
        self.astar = AStarPathfinder(self.maze_gen)
        
        # Algorithm states
        self.dijkstra_path = []
        self.astar_path = []
        self.algorithms_running = False
        self.show_visited = True
        self.animation_speed = 1  # 1 = normal, 2 = faster, etc.
        
        # Animation states for moving agents
        self.animate_movement = False
        self.dijkstra_agent_pos = None
        self.astar_agent_pos = None
        self.dijkstra_step_index = 0
        self.astar_step_index = 0
        self.animation_timer = 0
        self.animation_delay = 100  # milliseconds between steps
        
        # Running flag
        self.running = True
        
    def draw_maze(self, offset_x=0):
        """Draw the maze on screen with given x offset"""
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                x = offset_x + col * self.cell_size
                y = row * self.cell_size
                
                if self.maze[row, col] == 1:  # Wall
                    pygame.draw.rect(self.screen, self.BLUE, 
                                   (x, y, self.cell_size, self.cell_size))
                else:  # Path
                    pygame.draw.rect(self.screen, self.BLACK, 
                                   (x, y, self.cell_size, self.cell_size))
                    
    def draw_visited_nodes(self, algorithm, offset_x=0, color=None):
        """Draw visited nodes for an algorithm"""
        if not self.show_visited:
            return
            
        if color is None:
            color = self.DARK_GRAY
            
        for row, col in algorithm.visited:
            x = offset_x + col * self.cell_size + 2
            y = row * self.cell_size + 2
            pygame.draw.rect(self.screen, color, 
                           (x, y, self.cell_size - 4, self.cell_size - 4))
                           
    def draw_path(self, path, offset_x=0, color=None):
        """Draw the found path"""
        if color is None:
            color = self.YELLOW
            
        for i, (row, col) in enumerate(path):
            x = offset_x + col * self.cell_size + self.cell_size // 4
            y = row * self.cell_size + self.cell_size // 4
            size = self.cell_size // 2
            pygame.draw.rect(self.screen, color, (x, y, size, size))
            
            # Draw connections between path nodes
            if i < len(path) - 1:
                next_row, next_col = path[i + 1]
                next_x = offset_x + next_col * self.cell_size + self.cell_size // 2
                next_y = next_row * self.cell_size + self.cell_size // 2
                curr_x = x + size // 2
                curr_y = y + size // 2
                pygame.draw.line(self.screen, color, (curr_x, curr_y), 
                               (next_x, next_y), 3)
                               
    def draw_start_goal(self, offset_x=0):
        """Draw start and goal positions"""
        # Start position (Green)
        start_row, start_col = self.start
        x = offset_x + start_col * self.cell_size + self.cell_size // 2
        y = start_row * self.cell_size + self.cell_size // 2
        pygame.draw.circle(self.screen, self.GREEN, (x, y), self.cell_size // 3)
        
        # Goal position (Red)
        goal_row, goal_col = self.goal
        x = offset_x + goal_col * self.cell_size + self.cell_size // 2
        y = goal_row * self.cell_size + self.cell_size // 2
        pygame.draw.circle(self.screen, self.RED, (x, y), self.cell_size // 3)
        
    def draw_ui_panel(self):
        """Draw UI panel with algorithm statistics"""
        panel_y = self.maze_height
        pygame.draw.rect(self.screen, self.DARK_GRAY, 
                        (0, panel_y, self.screen_width, self.ui_panel_height))
        
        # Calculate proper spacing for two columns with more separation
        quarter_width = self.screen_width // 4
        left_column_x = quarter_width - 100
        right_column_x = self.screen_width - quarter_width - 100
        stats_y = panel_y + 20
        
        # Dijkstra stats (left side)
        self.draw_algorithm_stats(self.dijkstra, left_column_x, stats_y, self.CYAN)
        
        # Draw vertical separator line
        separator_x = self.screen_width // 2
        pygame.draw.line(self.screen, self.GRAY, 
                        (separator_x, panel_y + 15), 
                        (separator_x, panel_y + 115), 2)
        
        # A* stats (right side)
        self.draw_algorithm_stats(self.astar, right_column_x, stats_y, self.ORANGE)
        
        # Instructions (split into two lines for better readability)
        instructions = [
            "SPACE: Run/Reset | A: Animate | V: Toggle Visited | R: New Maze",
            "+/-: Animation Speed | ESC: Quit"
        ]
        y_offset = panel_y + 125
        for instruction in instructions:
            text = self.font_small.render(instruction, True, self.WHITE)
            text_rect = text.get_rect(center=(self.screen_width // 2, y_offset))
            self.screen.blit(text, text_rect)
            y_offset += 18
            
    def draw_algorithm_stats(self, algorithm, x, y, color):
        """Draw statistics for an algorithm"""
        # Algorithm name with background box
        name_text = self.font_medium.render(algorithm.algorithm_name, True, color)
        name_rect = name_text.get_rect(topleft=(x, y))
        
        # Draw background box for better visibility
        padding = 8
        bg_rect = name_rect.inflate(padding * 2, padding)
        pygame.draw.rect(self.screen, self.BLACK, bg_rect)
        pygame.draw.rect(self.screen, color, bg_rect, 2)  # Border
        
        self.screen.blit(name_text, name_rect)
        
        # Statistics with better formatting
        stats = [
            f"Nodes: {algorithm.nodes_explored}",
            f"Path: {len(algorithm.path) if algorithm.path else 0}",
            f"Time: {algorithm.computation_time_ms:.2f}ms"
        ]
        
        y_offset = y + 35
        for stat in stats:
            text = self.font_small.render(stat, True, self.WHITE)
            self.screen.blit(text, (x + 5, y_offset))
            y_offset += 24
            
    def run_algorithms(self):
        """Run both algorithms to find paths"""
        print("Running Dijkstra...")
        self.dijkstra_path, dijkstra_dist = self.dijkstra.find_path(self.start, self.goal)
        
        print("Running A*...")
        self.astar_path, astar_dist = self.astar.find_path(self.start, self.goal)
        
        # Print comparison results
        print("\n" + "="*60)
        print("ALGORITHM COMPARISON RESULTS")
        print("="*60)
        print(f"{'Algorithm':<20} {'Nodes':<12} {'Path Length':<15} {'Time (ms)':<12}")
        print("-"*60)
        print(f"{'Dijkstra':<20} {self.dijkstra.nodes_explored:<12} "
              f"{len(self.dijkstra_path) if self.dijkstra_path else 0:<15} "
              f"{self.dijkstra.computation_time_ms:<12.2f}")
        print(f"{'A* (Manhattan)':<20} {self.astar.nodes_explored:<12} "
              f"{len(self.astar_path) if self.astar_path else 0:<15} "
              f"{self.astar.computation_time_ms:<12.2f}")
        print("="*60)
        
        # Calculate efficiency
        if self.dijkstra.nodes_explored > 0 and self.astar.nodes_explored > 0:
            efficiency = (1 - self.astar.nodes_explored / self.dijkstra.nodes_explored) * 100
            print(f"\nA* explored {efficiency:.1f}% fewer nodes than Dijkstra")
            
        if self.dijkstra.computation_time_ms > 0 and self.astar.computation_time_ms > 0:
            time_ratio = self.astar.computation_time_ms / self.dijkstra.computation_time_ms
            if time_ratio < 1:
                print(f"A* was {(1/time_ratio):.2f}x faster than Dijkstra")
            else:
                print(f"Dijkstra was {time_ratio:.2f}x faster than A*")
        print()
        
        # Initialize animation
        self.start_animation()
        
    def start_animation(self):
        """Start the agent movement animation"""
        self.animate_movement = True
        self.dijkstra_step_index = 0
        self.astar_step_index = 0
        self.animation_timer = pygame.time.get_ticks()
        
        if self.dijkstra_path:
            self.dijkstra_agent_pos = self.dijkstra_path[0]
        if self.astar_path:
            self.astar_agent_pos = self.astar_path[0]
            
    def update_animation(self):
        """Update agent positions during animation"""
        if not self.animate_movement:
            return
            
        current_time = pygame.time.get_ticks()
        if current_time - self.animation_timer >= self.animation_delay:
            self.animation_timer = current_time
            
            # Update Dijkstra agent
            if self.dijkstra_path and self.dijkstra_step_index < len(self.dijkstra_path) - 1:
                self.dijkstra_step_index += 1
                self.dijkstra_agent_pos = self.dijkstra_path[self.dijkstra_step_index]
            
            # Update A* agent
            if self.astar_path and self.astar_step_index < len(self.astar_path) - 1:
                self.astar_step_index += 1
                self.astar_agent_pos = self.astar_path[self.astar_step_index]
            
            # Check if animation is complete
            dijkstra_done = not self.dijkstra_path or self.dijkstra_step_index >= len(self.dijkstra_path) - 1
            astar_done = not self.astar_path or self.astar_step_index >= len(self.astar_path) - 1
            
            if dijkstra_done and astar_done:
                self.animate_movement = False
                print("Animation complete!")
                
    def draw_agent(self, position, offset_x, color):
        """Draw an animated agent at the given position"""
        if position is None:
            return
            
        row, col = position
        x = offset_x + col * self.cell_size + self.cell_size // 2
        y = row * self.cell_size + self.cell_size // 2
        
        # Draw outer circle
        pygame.draw.circle(self.screen, color, (x, y), self.cell_size // 3)
        # Draw inner circle for highlight
        pygame.draw.circle(self.screen, self.WHITE, (x, y), self.cell_size // 6)
        
    def generate_new_maze(self):
        """Generate a new maze and reset algorithms"""
        print("Generating new maze...")
        self.maze, self.start, self.goal = self.maze_gen.generate_maze()
        self.dijkstra.reset_stats()
        self.astar.reset_stats()
        self.dijkstra_path = []
        self.astar_path = []
        self.algorithms_running = False
        
    def handle_events(self):
        """Handle user input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    
                elif event.key == pygame.K_SPACE:
                    if not self.algorithms_running:
                        self.run_algorithms()
                        self.algorithms_running = True
                    else:
                        # Reset
                        self.dijkstra.reset_stats()
                        self.astar.reset_stats()
                        self.dijkstra_path = []
                        self.astar_path = []
                        self.algorithms_running = False
                        
                elif event.key == pygame.K_v:
                    self.show_visited = not self.show_visited
                    
                elif event.key == pygame.K_r:
                    self.generate_new_maze()
                    
                elif event.key == pygame.K_a:
                    # Toggle animation
                    if self.dijkstra_path and self.astar_path:
                        if not self.animate_movement:
                            self.start_animation()
                        else:
                            self.animate_movement = False
                            
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Speed up animation
                    self.animation_delay = max(10, self.animation_delay - 20)
                    print(f"Animation delay: {self.animation_delay}ms")
                    
                elif event.key == pygame.K_MINUS:
                    # Slow down animation
                    self.animation_delay = min(500, self.animation_delay + 20)
                    print(f"Animation delay: {self.animation_delay}ms")
                    
    def render(self):
        """Render the complete scene"""
        self.screen.fill(self.BLACK)
        
        # Draw left maze (Dijkstra)
        self.draw_maze(offset_x=0)
        if self.show_visited:
            self.draw_visited_nodes(self.dijkstra, offset_x=0, color=(30, 30, 60))
        if self.dijkstra_path:
            self.draw_path(self.dijkstra_path, offset_x=0, color=self.CYAN)
        self.draw_start_goal(offset_x=0)
        
        # Draw Dijkstra agent
        if self.dijkstra_agent_pos:
            self.draw_agent(self.dijkstra_agent_pos, 0, self.CYAN)
        
        # Draw divider line
        divider_x = self.maze_width + 1
        pygame.draw.line(self.screen, self.WHITE, 
                        (divider_x, 0), (divider_x, self.maze_height), 3)
        
        # Draw right maze (A*)
        self.draw_maze(offset_x=self.maze_width + 3)
        if self.show_visited:
            self.draw_visited_nodes(self.astar, offset_x=self.maze_width + 3, 
                                  color=(60, 40, 0))
        if self.astar_path:
            self.draw_path(self.astar_path, offset_x=self.maze_width + 3, 
                          color=self.ORANGE)
        self.draw_start_goal(offset_x=self.maze_width + 3)
        
        # Draw A* agent
        if self.astar_agent_pos:
            self.draw_agent(self.astar_agent_pos, self.maze_width + 3, self.ORANGE)
        
        # Draw labels above mazes
        dijkstra_label = self.font_large.render("DIJKSTRA", True, self.CYAN)
        dijkstra_rect = dijkstra_label.get_rect(center=(self.maze_width // 2, 
                                                         self.maze_height + 10))
        # Draw background for label
        pygame.draw.rect(self.screen, self.BLACK, 
                        dijkstra_rect.inflate(20, 10))
        self.screen.blit(dijkstra_label, dijkstra_rect)
        
        astar_label = self.font_large.render("A* (MANHATTAN)", True, self.ORANGE)
        astar_rect = astar_label.get_rect(center=(self.maze_width + 3 + self.maze_width // 2, 
                                                   self.maze_height + 10))
        pygame.draw.rect(self.screen, self.BLACK, 
                        astar_rect.inflate(20, 10))
        self.screen.blit(astar_label, astar_rect)
        
        # Draw UI panel
        self.draw_ui_panel()
        
        pygame.display.flip()
        
    def run(self):
        """Main game loop"""
        print("\n" + "="*60)
        print("ALGORITHM COMPARISON TOOL")
        print("="*60)
        print("Comparing Dijkstra and A* pathfinding algorithms")
        print("\nControls:")
        print("  SPACE - Run algorithms / Reset")
        print("  A     - Start/Stop animation")
        print("  V     - Toggle visited nodes visualization")
        print("  +/-   - Speed up/slow down animation")
        print("  R     - Generate new maze")
        print("  ESC   - Quit")
        print("="*60 + "\n")
        
        while self.running:
            self.handle_events()
            self.update_animation()  # Update agent positions
            self.render()
            self.clock.tick(60)  # 60 FPS
            
        pygame.quit()
        sys.exit()


def main():
    """Main entry point"""
    try:
        # You can customize maze size here
        comparison = AlgorithmComparison(maze_width=41, maze_height=31, cell_size=20)
        comparison.run()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Exiting gracefully...")
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()

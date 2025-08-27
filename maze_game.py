import pygame
import sys
import random
import math
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm

class PacmanGame:
    def __init__(self, width=28, height=31, cell_size=20):
        self.maze_gen = MazeGenerator(width, height)
        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
        self.cell_size = cell_size
        self.screen_width = width * cell_size
        self.screen_height = (height + 3) * cell_size  # Extra space for UI

        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Pacman AI - Intelligent Maze Game")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.large_font = pygame.font.SysFont("arial", 36, bold=True)

        # Colors - Pacman style
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.YELLOW = (255, 255, 0)
        self.BLUE = (0, 0, 255)
        self.RED = (255, 0, 0)
        self.PINK = (255, 182, 193)
        self.CYAN = (0, 255, 255)
        self.ORANGE = (255, 165, 0)
        self.DARK_BLUE = (0, 0, 139)

        # Game state
        self.running = True
        self.game_state = "playing"  # playing, paused, game_over, level_complete
        self.score = 0
        self.lives = 3
        self.level = 1

        # Pacman properties - will be set after maze generation
        self.pacman_pos = [14, 23]  # Temporary position, will be updated
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = 2
        self.pacman_animation = 0
        self.pacman_mouth_open = True

        # Generate maze
        self.generate_level()
        
        # Set Pacman starting position from maze start (black cell)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats

        # Dots and pellets
        self.dots = []
        self.power_pellets = []
        self.place_dots_and_pellets()

        # Ghosts
        self.ghosts = []
        self.create_ghosts()

        # Auto mode for Pacman AI
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None
        self.show_auto_path = False

        # Game timing
        self.last_update = pygame.time.get_ticks()
        self.animation_timer = 0
        self.auto_update_timer = 0
        self.auto_update_timer = 0

    def generate_level(self):
        """Generate maze with Pacman-style layout"""
        max_attempts = 10
        for attempt in range(max_attempts):
            self.maze, self.start, self.goal = self.maze_gen.generate_maze()
            # Ensure start and goal are in good positions
            if self.validate_pacman_layout():
                break
        else:
            print("Warning: Could not generate suitable Pacman maze")

    def validate_pacman_layout(self):
        """Ensure maze is suitable for Pacman gameplay"""
        # Check if start position is valid
        start_row, start_col = self.start
        if not (0 <= start_row < self.maze_gen.height and 0 <= start_col < self.maze_gen.width):
            return False
        if self.maze[start_row, start_col] == 1:
            return False
        return True

    def place_dots_and_pellets(self):
        """Place dots and power pellets on the maze"""
        self.dots = []
        self.power_pellets = []

        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    center = ((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)

                    # Place power pellets at corners
                    if (x in [1, self.maze_gen.width-2] and y in [1, self.maze_gen.height-2]):
                        self.power_pellets.append(center)
                    else:
                        # Place regular dots everywhere except start and goal
                        if not ((y, x) == self.start or (y, x) == self.goal):
                            self.dots.append(center)

    def create_ghosts(self):
        """Create exactly 4 ghosts with different colors and behaviors"""
        # Clear existing ghosts first to prevent duplication
        self.ghosts = []
        
        ghost_colors = [self.RED, self.PINK, self.CYAN, self.ORANGE]
        ghost_names = ["Blinky", "Pinky", "Inky", "Clyde"]

        # Create exactly 4 ghosts, no more
        for i in range(4):
            color = ghost_colors[i]
            name = ghost_names[i]
            ghost = {
                'name': name,
                'color': color,
                'pos': [14 + (i % 2), 14 + (i // 2)],  # Different starting positions
                'direction': [0, 0],
                'speed': 1.2,  # Slightly slower than pacman
                'mode': 'scatter',  # scatter, chase, frightened
                'target': None,
                'animation': 0,
                'last_direction_change': 0
            }
            self.ghosts.append(ghost)

    def draw_maze(self):
        """Draw the maze with Pacman-style walls"""
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                rect = pygame.Rect(x * self.cell_size, y * self.cell_size,
                                 self.cell_size, self.cell_size)
                if self.maze[y, x] == 1:  # Wall
                    # Draw wall with rounded corners for Pacman style
                    pygame.draw.rect(self.screen, self.BLUE, rect)
                    # Add border
                    pygame.draw.rect(self.screen, self.WHITE, rect, 1)
                else:  # Path
                    pygame.draw.rect(self.screen, self.BLACK, rect)

    def draw_dots_and_pellets(self):
        """Draw dots and power pellets"""
        # Regular dots
        for dot in self.dots:
            pygame.draw.circle(self.screen, self.WHITE, dot, 2)

        # Power pellets
        for pellet in self.power_pellets:
            pygame.draw.circle(self.screen, self.WHITE, pellet, 6)

    def draw_pacman(self):
        """Draw Pacman with animation"""
        col, row = self.pacman_pos
        center = (col * self.cell_size + self.cell_size // 2,
                 row * self.cell_size + self.cell_size // 2)

        # Calculate mouth angle based on direction
        mouth_angle = 0
        if self.pacman_direction == [1, 0]:  # Right
            mouth_angle = 0
        elif self.pacman_direction == [-1, 0]:  # Left
            mouth_angle = 180
        elif self.pacman_direction == [0, -1]:  # Up
            mouth_angle = 90
        elif self.pacman_direction == [0, 1]:  # Down
            mouth_angle = 270

        # Animate mouth
        mouth_open_angle = 45 if self.pacman_mouth_open else 5

        # Draw Pacman as a pie shape
        pygame.draw.circle(self.screen, self.YELLOW, center, self.cell_size // 2 - 2)

        if self.pacman_direction != [0, 0]:
            # Draw mouth
            start_angle = math.radians(mouth_angle - mouth_open_angle)
            end_angle = math.radians(mouth_angle + mouth_open_angle)
            pygame.draw.polygon(self.screen, self.BLACK, [
                center,
                (center[0] + math.cos(start_angle) * (self.cell_size // 2),
                 center[1] + math.sin(start_angle) * (self.cell_size // 2)),
                (center[0] + math.cos(end_angle) * (self.cell_size // 2),
                 center[1] + math.sin(end_angle) * (self.cell_size // 2))
            ])

    def draw_ghosts(self):
        """Draw ghosts with simple animation"""
        for ghost in self.ghosts:
            col, row = ghost['pos']
            center = (col * self.cell_size + self.cell_size // 2,
                     row * self.cell_size + self.cell_size // 2)

            # Ghost body (rounded rectangle)
            body_rect = pygame.Rect(center[0] - self.cell_size // 2 + 2,
                                  center[1] - self.cell_size // 2 + 2,
                                  self.cell_size - 4, self.cell_size - 4)
            pygame.draw.rect(self.screen, ghost['color'], body_rect, border_radius=5)

            # Ghost eyes
            eye_size = 4
            eye_y = center[1] - 3
            left_eye = (center[0] - 6, eye_y)
            right_eye = (center[0] + 6, eye_y)

            pygame.draw.circle(self.screen, self.WHITE, left_eye, eye_size)
            pygame.draw.circle(self.screen, self.WHITE, right_eye, eye_size)
            pygame.draw.circle(self.screen, self.BLACK, left_eye, 2)
            pygame.draw.circle(self.screen, self.BLACK, right_eye, 2)

    def draw_ui(self):
        """Draw game UI"""
        ui_y = self.maze_gen.height * self.cell_size + 10

        # Score
        score_text = self.font.render(f"Score: {self.score}", True, self.WHITE)
        self.screen.blit(score_text, (10, ui_y))

        # Lives
        lives_text = self.font.render(f"Lives: {self.lives}", True, self.WHITE)
        self.screen.blit(lives_text, (200, ui_y))

        # Level
        level_text = self.font.render(f"Level: {self.level}", True, self.WHITE)
        self.screen.blit(level_text, (350, ui_y))

        # Instructions
        if self.game_state == "playing":
            mode_text = "🤖 AUTO" if self.auto_mode else "🎮 MANUAL"
            inst_text = self.font.render(f"{mode_text} | Arrow Keys: Move | A: Auto | H: Show Path | P: Pause | R: Restart", True, self.YELLOW)
            self.screen.blit(inst_text, (10, ui_y + 30))

            if self.auto_mode and self.show_auto_path:
                path_text = self.font.render("Auto path: Cyan dots", True, (0, 255, 255))
                self.screen.blit(path_text, (10, ui_y + 55))

        elif self.game_state == "paused":
            pause_text = self.large_font.render("PAUSED", True, self.YELLOW)
            self.screen.blit(pause_text, (self.screen_width // 2 - 60, self.screen_height // 2))

        elif self.game_state == "game_over":
            game_over_text = self.large_font.render("GAME OVER", True, self.RED)
            restart_text = self.font.render("Press R to restart", True, self.WHITE)
            self.screen.blit(game_over_text, (self.screen_width // 2 - 100, self.screen_height // 2 - 20))
            self.screen.blit(restart_text, (self.screen_width // 2 - 70, self.screen_height // 2 + 20))

    def move_pacman(self):
        """Move Pacman with GRID-BASED movement - ONE BLOCK AT A TIME"""
        # Check current position validity
        current_col, current_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        if not self.is_valid_position(current_col, current_row):
            # Force Pacman to start position
            start_row, start_col = self.start
            self.pacman_pos = [float(start_col), float(start_row)]
            self.pacman_direction = [0, 0]
            return
        
        # Try to change direction if requested
        if self.pacman_next_direction != [0, 0]:
            # Calculate target block position
            target_col = int(round(self.pacman_pos[0])) + self.pacman_next_direction[0]
            target_row = int(round(self.pacman_pos[1])) + self.pacman_next_direction[1]

            # STRICT CHECK: Target block must be valid (black cell only)
            if self.is_valid_position(target_col, target_row):
                self.pacman_direction = self.pacman_next_direction[:]
                self.pacman_next_direction = [0, 0]

        # Move in current direction - BLOCK BY BLOCK
        if self.pacman_direction != [0, 0]:
            # Calculate target block position
            current_col = int(round(self.pacman_pos[0]))
            current_row = int(round(self.pacman_pos[1]))
            target_col = current_col + self.pacman_direction[0]
            target_row = current_row + self.pacman_direction[1]

            # Check if we can move to target block
            if self.is_valid_position(target_col, target_row):
                # Smooth animation towards target block
                step_size = 0.15  # Animation speed
                
                # Move towards target position
                if abs(self.pacman_pos[0] - target_col) > 0.01:
                    if target_col > current_col:
                        self.pacman_pos[0] = min(self.pacman_pos[0] + step_size, target_col)
                    else:
                        self.pacman_pos[0] = max(self.pacman_pos[0] - step_size, target_col)
                
                if abs(self.pacman_pos[1] - target_row) > 0.01:
                    if target_row > current_row:
                        self.pacman_pos[1] = min(self.pacman_pos[1] + step_size, target_row)
                    else:
                        self.pacman_pos[1] = max(self.pacman_pos[1] - step_size, target_row)
                
                # Snap to exact position when close enough
                if abs(self.pacman_pos[0] - target_col) <= 0.01:
                    self.pacman_pos[0] = float(target_col)
                if abs(self.pacman_pos[1] - target_row) <= 0.01:
                    self.pacman_pos[1] = float(target_row)
                
                # Handle screen wrapping (tunnels)
                if target_col < 0 and self.is_valid_position(self.maze_gen.width - 1, target_row):
                    self.pacman_pos[0] = float(self.maze_gen.width - 1)
                elif target_col >= self.maze_gen.width and self.is_valid_position(0, target_row):
                    self.pacman_pos[0] = 0.0
            else:
                # STOP if can't move to target block
                self.pacman_direction = [0, 0]
                # Snap to current block center
                self.pacman_pos[0] = float(current_col)
                self.pacman_pos[1] = float(current_row)

    def move_ghosts(self):
        """Move ghosts with GRID-BASED movement - ONE BLOCK AT A TIME"""
        for ghost in self.ghosts:
            # Get current block position
            current_col = int(round(ghost['pos'][0]))
            current_row = int(round(ghost['pos'][1]))
            
            # Check if ghost is in valid position
            if not self.is_valid_position(current_col, current_row):
                # Reset ghost to a safe position
                ghost['pos'] = [14.0, 14.0]  # Center of maze as float
                ghost['direction'] = [0, 0]
                continue
            
            # Get all possible directions for next block
            directions = [[0, -1], [0, 1], [-1, 0], [1, 0]]
            valid_directions = []

            # Find STRICTLY valid directions (only black cells)
            for dx, dy in directions:
                target_col = current_col + dx
                target_row = current_row + dy
                
                # STRICT CHECK: Must be valid position (black cell)
                if self.is_valid_position(target_col, target_row):
                    valid_directions.append([dx, dy])

            if valid_directions:
                # Remove opposite direction to prevent immediate reversal
                opposite_direction = [-ghost['direction'][0], -ghost['direction'][1]]
                if opposite_direction in valid_directions and len(valid_directions) > 1:
                    valid_directions.remove(opposite_direction)

                # Choose direction based on ghost personality and mode
                if ghost['mode'] == 'chase':
                    new_direction = self.get_chase_direction(ghost, valid_directions)
                elif ghost['mode'] == 'scatter':
                    new_direction = self.get_scatter_direction(ghost, valid_directions)
                elif ghost['mode'] == 'frightened':
                    new_direction = random.choice(valid_directions)
                else:
                    # Default: continue current direction or choose random
                    if ghost['direction'] in valid_directions and random.random() < 0.8:
                        new_direction = ghost['direction']
                    else:
                        new_direction = random.choice(valid_directions)

                # Calculate target block position
                target_col = current_col + new_direction[0]
                target_row = current_row + new_direction[1]
                
                # FINAL STRICT CHECK before moving
                if self.is_valid_position(target_col, target_row):
                    ghost['direction'] = new_direction
                    
                    # Smooth animation towards target block
                    step_size = 0.08  # Slower than Pacman
                    
                    # Move towards target position
                    if abs(ghost['pos'][0] - target_col) > 0.01:
                        if target_col > current_col:
                            ghost['pos'][0] = min(ghost['pos'][0] + step_size, target_col)
                        else:
                            ghost['pos'][0] = max(ghost['pos'][0] - step_size, target_col)
                    
                    if abs(ghost['pos'][1] - target_row) > 0.01:
                        if target_row > current_row:
                            ghost['pos'][1] = min(ghost['pos'][1] + step_size, target_row)
                        else:
                            ghost['pos'][1] = max(ghost['pos'][1] - step_size, target_row)
                    
                    # Snap to exact position when close enough
                    if abs(ghost['pos'][0] - target_col) <= 0.01:
                        ghost['pos'][0] = float(target_col)
                    if abs(ghost['pos'][1] - target_row) <= 0.01:
                        ghost['pos'][1] = float(target_row)
                else:
                    # Stop if invalid
                    ghost['direction'] = [0, 0]
                    # Snap to current block center
                    ghost['pos'][0] = float(current_col)
                    ghost['pos'][1] = float(current_row)

                # Switch modes occasionally
                if random.random() < 0.005:  # 0.5% chance per frame
                    ghost['mode'] = 'chase' if ghost['mode'] == 'scatter' else 'scatter'

    def get_chase_direction(self, ghost, valid_directions):
        """Get direction to chase Pacman"""
        # Simple chase: move towards Pacman's current position
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        ghost_col, ghost_row = int(ghost['pos'][0]), int(ghost['pos'][1])

        # Calculate direction to Pacman
        dx = pacman_col - ghost_col
        dy = pacman_row - ghost_row

        # Choose direction that reduces distance to Pacman
        best_direction = ghost['direction']  # Default to current
        min_distance = float('inf')

        for direction in valid_directions:
            new_col = ghost_col + direction[0]
            new_row = ghost_row + direction[1]
            distance = abs(new_col - pacman_col) + abs(new_row - pacman_row)

            if distance < min_distance:
                min_distance = distance
                best_direction = direction

        return best_direction

    def get_scatter_direction(self, ghost, valid_directions):
        """Get direction to scatter to designated corner"""
        # Each ghost has a preferred corner
        corners = {
            'Blinky': (self.maze_gen.width - 2, 1),      # Top-right
            'Pinky': (1, 1),                             # Top-left
            'Inky': (self.maze_gen.width - 2, self.maze_gen.height - 2),  # Bottom-right
            'Clyde': (1, self.maze_gen.height - 2)       # Bottom-left
        }

        target = corners.get(ghost['name'], (self.maze_gen.width // 2, self.maze_gen.height // 2))
        ghost_col, ghost_row = int(ghost['pos'][0]), int(ghost['pos'][1])

        # Choose direction that moves towards target corner
        best_direction = ghost['direction']
        min_distance = float('inf')

        for direction in valid_directions:
            new_col = ghost_col + direction[0]
            new_row = ghost_row + direction[1]
            distance = abs(new_col - target[0]) + abs(new_row - target[1])

            if distance < min_distance:
                min_distance = distance
                best_direction = direction

        return best_direction

    def toggle_auto_mode(self):
        """Toggle between manual and automatic Pacman control"""
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            print("🤖 Auto mode ON - Pacman will play automatically!")
            self.find_auto_target()
        else:
            print("🎮 Manual mode ON - You control Pacman!")
            self.auto_path = []
            self.auto_target = None
            self.pacman_direction = [0, 0]
            self.pacman_next_direction = [0, 0]

    def find_auto_target(self):
        """Find the best target for Pacman with improved strategy"""
        if not self.dots and not self.power_pellets:
            return

        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)

        # Get ghost positions for avoidance
        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts]

        # Find nearest safe power pellet first (higher priority)
        if self.power_pellets:
            best_pellet = None
            best_score = float('-inf')

            for pellet in self.power_pellets:
                # Convert screen coordinates to maze coordinates
                pellet_col = int((pellet[0] - self.cell_size // 2) / self.cell_size)
                pellet_row = int((pellet[1] - self.cell_size // 2) / self.cell_size)
                pellet_pos = (pellet_row, pellet_col)

                # Calculate safety score (distance from ghosts)
                safety_score = min([abs(pellet_row - gr) + abs(pellet_col - gc) 
                                  for gr, gc in ghost_positions]) if ghost_positions else 10

                # Calculate path distance
                path, distance = self.dijkstra.shortest_path(pacman_pos, pellet_pos)
                if path and distance > 0:
                    # Score = safety / distance (prefer safe and close targets)
                    score = safety_score / distance
                    if score > best_score:
                        best_score = score
                        best_pellet = pellet_pos

            if best_pellet:
                self.auto_target = best_pellet
                self.calculate_auto_path()
                return

        # Find best dot using improved strategy
        if self.dots:
            best_dot = None
            best_score = float('-inf')

            # Consider multiple dots and choose the best one
            for dot in self.dots[:20]:  # Limit to first 20 for performance
                # Convert screen coordinates to maze coordinates
                dot_col = int((dot[0] - self.cell_size // 2) / self.cell_size)
                dot_row = int((dot[1] - self.cell_size // 2) / self.cell_size)
                dot_pos = (dot_row, dot_col)

                # Calculate safety score (distance from ghosts)
                safety_score = min([abs(dot_row - gr) + abs(dot_col - gc) 
                                  for gr, gc in ghost_positions]) if ghost_positions else 10

                # Calculate path distance
                path, distance = self.dijkstra.shortest_path(pacman_pos, dot_pos)
                if path and distance > 0:
                    # Improved scoring: prefer safe, close targets
                    score = (safety_score * 2) / distance  # Weight safety more
                    if score > best_score:
                        best_score = score
                        best_dot = dot_pos

            if best_dot:
                self.auto_target = best_dot
                self.calculate_auto_path()

    def calculate_auto_path(self):
        """Calculate optimized path to target while intelligently avoiding ghosts"""
        if not self.auto_target:
            return

        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)

        # Get ghost positions and their predicted future positions
        ghost_danger_zones = set()
        for ghost in self.ghosts:
            ghost_col, ghost_row = int(ghost['pos'][0]), int(ghost['pos'][1])
            ghost_pos = (ghost_row, ghost_col)
            
            # Mark danger zone around each ghost (larger radius for safety)
            for dr in range(-4, 5):
                for dc in range(-4, 5):
                    if abs(dr) + abs(dc) <= 4:  # Manhattan distance <= 4
                        danger_row, danger_col = ghost_row + dr, ghost_col + dc
                        if (0 <= danger_row < self.maze_gen.height and 
                            0 <= danger_col < self.maze_gen.width):
                            ghost_danger_zones.add((danger_row, danger_col))

        # Find primary path
        path, distance = self.dijkstra.shortest_path(pacman_pos, self.auto_target)

        if path:
            # Create smart filtered path
            smart_path = []
            skip_count = 0
            
            for i, pos in enumerate(path):
                pos_row, pos_col = pos
                
                # Check if position is in danger zone
                if pos in ghost_danger_zones:
                    skip_count += 1
                    # If too many dangerous positions, force a different route
                    if skip_count > 3:
                        # Try to find alternative safe positions nearby
                        safe_alternatives = []
                        for dr in [-1, 0, 1]:
                            for dc in [-1, 0, 1]:
                                alt_row, alt_col = pos_row + dr, pos_col + dc
                                alt_pos = (alt_row, alt_col)
                                if (alt_pos not in ghost_danger_zones and
                                    not self.is_wall(alt_col, alt_row) and
                                    0 <= alt_row < self.maze_gen.height and
                                    0 <= alt_col < self.maze_gen.width):
                                    safe_alternatives.append(alt_pos)
                        
                        if safe_alternatives:
                            smart_path.append(safe_alternatives[0])
                        skip_count = 0
                else:
                    smart_path.append(pos)
                    skip_count = 0

            # If we have a reasonable safe path, use it
            if len(smart_path) >= max(3, len(path) // 3):
                self.auto_path = smart_path[1:]  # Remove starting position
            else:
                # If path is too dangerous, find nearest safe position first
                safe_positions = []
                for y in range(max(0, pacman_row - 5), min(self.maze_gen.height, pacman_row + 6)):
                    for x in range(max(0, pacman_col - 5), min(self.maze_gen.width, pacman_col + 6)):
                        test_pos = (y, x)
                        if (test_pos not in ghost_danger_zones and 
                            not self.is_wall(x, y)):
                            safe_positions.append(test_pos)
                
                if safe_positions:
                    # Go to nearest safe position first
                    nearest_safe = min(safe_positions, 
                                     key=lambda p: abs(p[0] - pacman_row) + abs(p[1] - pacman_col))
                    safe_path, _ = self.dijkstra.shortest_path(pacman_pos, nearest_safe)
                    self.auto_path = safe_path[1:] if safe_path else []
                else:
                    # Last resort: use original path but move carefully
                    self.auto_path = path[1:3]  # Only next 2 steps
        else:
            self.auto_path = []

    def move_pacman_auto(self):
        """Move Pacman automatically using improved AI with ghost avoidance"""
        current_time = pygame.time.get_ticks()

        # Check for immediate ghost danger
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        immediate_danger = False
        
        for ghost in self.ghosts:
            ghost_col, ghost_row = int(ghost['pos'][0]), int(ghost['pos'][1])
            distance = abs(pacman_col - ghost_col) + abs(pacman_row - ghost_row)
            if distance <= 2:  # Ghost is very close!
                immediate_danger = True
                break
        
        # If immediate danger, recalculate path more frequently
        update_interval = 500 if immediate_danger else 1500
        
        # Update auto path when needed
        if (current_time - self.auto_update_timer > update_interval or
            not self.auto_path or
            self.has_reached_target() or
            immediate_danger):

            self.auto_update_timer = current_time
            self.find_auto_target()

        # Emergency escape if ghost is too close
        if immediate_danger:
            # Find emergency escape directions
            emergency_directions = []
            for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                escape_col = pacman_col + dx * 2  # Look 2 steps ahead
                escape_row = pacman_row + dy * 2
                
                if not self.is_wall(escape_col, escape_row):
                    # Check if this direction moves away from ALL ghosts
                    safe_from_all = True
                    for ghost in self.ghosts:
                        ghost_col, ghost_row = int(ghost['pos'][0]), int(ghost['pos'][1])
                        current_dist = abs(pacman_col - ghost_col) + abs(pacman_row - ghost_row)
                        escape_dist = abs(escape_col - ghost_col) + abs(escape_row - ghost_row)
                        if escape_dist <= current_dist:  # Not moving away
                            safe_from_all = False
                            break
                    
                    if safe_from_all:
                        emergency_directions.append([dx, dy])
            
            if emergency_directions:
                # Choose best emergency direction
                self.pacman_next_direction = emergency_directions[0]
                return

        # Normal pathfinding
        if self.auto_path:
            # Get next position in path
            next_pos = self.auto_path[0]
            next_row, next_col = next_pos

            # Calculate direction to next position
            current_col, current_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
            dx = next_col - current_col
            dy = next_row - current_row

            # Set direction with more precise movement
            if abs(dx) > abs(dy):
                self.pacman_next_direction = [1 if dx > 0 else -1, 0]
            else:
                self.pacman_next_direction = [0, 1 if dy > 0 else -1]

            # Check if we've reached the next position (more precise)
            if abs(self.pacman_pos[0] - next_col) < 0.5 and abs(self.pacman_pos[1] - next_row) < 0.5:
                self.auto_path.pop(0)  # Remove reached position

    def has_reached_target(self):
        """Check if Pacman has reached the current auto target"""
        if not self.auto_target:
            return True

        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        target_row, target_col = self.auto_target

        return abs(pacman_col - target_col) < 1 and abs(pacman_row - target_row) < 1

    def draw_auto_path(self):
        """Draw the auto path for visualization"""
        if self.show_auto_path and self.auto_path:
            for pos in self.auto_path[:10]:  # Show first 10 steps
                row, col = pos
                center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
                pygame.draw.circle(self.screen, (0, 255, 255), center, 3)  # Cyan dots for auto path

    def is_wall(self, col, row):
        """Check if position is a wall - STRICT VERSION"""
        # Ensure coordinates are within bounds
        if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
            return True  # Out of bounds = wall
        
        # Check if it's actually a wall (blue cell)
        return self.maze[row, col] == 1
    
    def is_valid_position(self, col, row):
        """Check if position is valid for movement (black cell only)"""
        # Convert float to int for checking
        check_col, check_row = int(round(col)), int(round(row))
        
        # Must be within bounds
        if not (0 <= check_row < self.maze_gen.height and 0 <= check_col < self.maze_gen.width):
            return False
            
        # Must be open path (black cell, not blue wall)
        return self.maze[check_row, check_col] == 0

    def check_collisions(self):
        """Check collisions with dots, pellets, and ghosts"""
        pacman_center = (self.pacman_pos[0] * self.cell_size + self.cell_size // 2,
                        self.pacman_pos[1] * self.cell_size + self.cell_size // 2)

        # Check dots
        for dot in self.dots[:]:
            distance = math.hypot(pacman_center[0] - dot[0], pacman_center[1] - dot[1])
            if distance < 10:
                self.dots.remove(dot)
                self.score += 10

        # Check power pellets
        for pellet in self.power_pellets[:]:
            distance = math.hypot(pacman_center[0] - pellet[0], pacman_center[1] - pellet[1])
            if distance < 10:
                self.power_pellets.remove(pellet)
                self.score += 50
                # Make ghosts frightened (future feature)

        # Check ghosts
        for ghost in self.ghosts:
            ghost_center = (ghost['pos'][0] * self.cell_size + self.cell_size // 2,
                          ghost['pos'][1] * self.cell_size + self.cell_size // 2)
            distance = math.hypot(pacman_center[0] - ghost_center[0],
                                pacman_center[1] - ghost_center[1])
            if distance < 15:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_state = "game_over"
                else:
                    self.reset_positions()

        # Check win condition
        if not self.dots and not self.power_pellets:
            self.level += 1
            self.generate_level()
            self.place_dots_and_pellets()
            self.reset_positions()

    def reset_positions(self):
        """Reset Pacman and ghosts to starting positions - ghosts placed randomly and far from Pacman"""
        # Set Pacman to maze start position (guaranteed black cell)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.auto_path = []
        self.auto_target = None
        
        # Verify Pacman position is valid
        if not self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
            # Find first valid position
            for row in range(self.maze_gen.height):
                for col in range(self.maze_gen.width):
                    if self.is_valid_position(col, row):
                        self.pacman_pos = [float(col), float(row)]
                        break
                if self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
                    break

        # Find all valid positions for ghosts
        all_valid_positions = []
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                if self.is_valid_position(col, row):
                    all_valid_positions.append([float(col), float(row)])  # Store as floats
        
        # Filter positions that are far from Pacman (minimum distance = 8 cells)
        min_distance_from_pacman = 8
        safe_positions = []
        
        for pos in all_valid_positions:
            distance = abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1])  # Manhattan distance
            if distance >= min_distance_from_pacman:
                safe_positions.append(pos)
        
        # If not enough safe positions, use all valid positions but sort by distance
        if len(safe_positions) < 4:
            # Sort by distance from Pacman (farthest first)
            all_valid_positions.sort(key=lambda pos: abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1]), reverse=True)
            safe_positions = all_valid_positions
        
        # Randomly shuffle safe positions
        random.shuffle(safe_positions)
        
        # Place ghosts at random safe positions
        for i, ghost in enumerate(self.ghosts[:4]):  # Ensure only 4 ghosts
            if i < len(safe_positions):
                ghost['pos'] = safe_positions[i][:]
            else:
                # Fallback: place at center if no safe position
                ghost['pos'] = [float(self.maze_gen.width // 2), float(self.maze_gen.height // 2)]
            
            # Reset ghost state
            ghost['direction'] = [0, 0]
            ghost['mode'] = 'scatter'  # Start in scatter mode for safety
            ghost['target'] = None
            ghost['last_direction_change'] = 0
            
            # Verify ghost position is valid
            if not self.is_valid_position(ghost['pos'][0], ghost['pos'][1]):
                # Find nearest valid position
                for pos in all_valid_positions:
                    if self.is_valid_position(pos[0], pos[1]):
                        ghost['pos'] = pos[:]
                        break

    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.game_state = "paused" if self.game_state == "playing" else "playing"
                elif event.key == pygame.K_a:
                    self.toggle_auto_mode()
                elif event.key == pygame.K_h:
                    self.show_auto_path = not self.show_auto_path
                elif event.key == pygame.K_r:
                    self.restart_game()
                elif self.game_state == "playing":
                    if event.key == pygame.K_UP:
                        self.pacman_next_direction = [0, -1]
                    elif event.key == pygame.K_DOWN:
                        self.pacman_next_direction = [0, 1]
                    elif event.key == pygame.K_LEFT:
                        self.pacman_next_direction = [-1, 0]
                    elif event.key == pygame.K_RIGHT:
                        self.pacman_next_direction = [1, 0]

    def restart_game(self):
        """Restart the entire game while maintaining exactly 4 ghosts"""
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None
        
        self.generate_level()
        self.place_dots_and_pellets()
        
        # Only create ghosts if none exist, otherwise just reset them
        if len(self.ghosts) != 4:
            self.create_ghosts()
        
        self.reset_positions()

    def update(self):
        """Update game state"""
        current_time = pygame.time.get_ticks()

        if self.game_state == "playing":
            # Move Pacman based on mode
            if self.auto_mode:
                self.move_pacman_auto()
            else:
                self.move_pacman()
                
            self.move_ghosts()
            self.check_collisions()

            # Animate Pacman mouth
            self.animation_timer += 1
            if self.animation_timer >= 10:
                self.pacman_mouth_open = not self.pacman_mouth_open
                self.animation_timer = 0

    def draw(self):
        """Draw everything"""
        self.screen.fill(self.BLACK)
        self.draw_maze()
        self.draw_dots_and_pellets()
        self.draw_auto_path()  # Draw auto path if enabled
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_ui()
        pygame.display.flip()

    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = PacmanGame()
    game.run()

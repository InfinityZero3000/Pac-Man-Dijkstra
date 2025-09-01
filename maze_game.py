import pygame
import sys
import random
import math
import signal
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm
import config

class PacmanGame:
    def __init__(self, width=71, height=41, cell_size=23):
        self.maze_gen = MazeGenerator(width, height)
        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
        self.cell_size = cell_size
        self.screen_width = width * cell_size
        self.screen_height = (height + 3) * cell_size  # Extra space for UI

        pygame.init()
        
        # Setup signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print("\nReceived signal, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
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

        # Load ghost images
        self.load_ghost_images()

        # Game state
        self.running = True
        self.game_state = "playing"  # playing, paused, game_over, level_complete
        self.score = 0
        self.lives = 3
        self.level = 1

        # Pacman properties - will be set after maze generation
        self.pacman_pos = [14.0, 23.0]  # Temporary position, will be updated as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = 2
        self.pacman_animation = 1
        self.pacman_mouth_open = True

        # Generate maze
        self.generate_level()
        
        # Set Pacman starting position from maze start (black cell)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats

        # Exit gate - opposite corner from Pacman start
        self.exit_gate = self.calculate_exit_gate_position()

        # Dots and pellets
        self.dots = []
        self.power_pellets = []
        self.place_dots_and_pellets()

        # Bombs as obstacles
        self.bombs = []
        self.place_bombs()

        # Ghosts
        self.ghosts = []
        self.create_ghosts()

        # Auto mode for Pacman AI - ENSURE STARTS AS FALSE
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None

        # Goal-focused movement variables
        self.current_goal = None
        self.goal_locked = False
        self.goal_cooldown = 0
        self.ghost_avoidance_active = False
        self.last_ghost_check = 0
        self.last_emergency_turn = 0
        self.turn_cooldown = 0

        # Shortest path visualization
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0

        # Game timing
        self.last_update = pygame.time.get_ticks()
        self.animation_timer = 0
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

    def load_ghost_images(self):
        """Load ghost images from public folder"""
        self.ghost_images = {}
        
        # Load ghost images for each color (0-3)
        ghost_colors = ['0', '1', '2', '3']  # red, pink, cyan, orange
        
        for i, color in enumerate(ghost_colors):
            # Load right-facing (0) and left-facing (1) images
            try:
                self.ghost_images[f'ghost{i}_right'] = pygame.image.load(f'public/ghost{color}_0.png').convert_alpha()
                self.ghost_images[f'ghost{i}_left'] = pygame.image.load(f'public/ghost{color}_1.png').convert_alpha()
            except pygame.error as e:
                print(f"Warning: Could not load ghost{color} images: {e}")
                # Fallback to colored rectangles if images fail to load
                self.ghost_images[f'ghost{i}_right'] = None
                self.ghost_images[f'ghost{i}_left'] = None
        
        # Load scared ghost images
        try:
            self.ghost_images['ghost_scared_right'] = pygame.image.load('public/ghostScared_0.png').convert_alpha()
            self.ghost_images['ghost_scared_left'] = pygame.image.load('public/ghostScared_1.png').convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load scared ghost images: {e}")
            self.ghost_images['ghost_scared_right'] = None
            self.ghost_images['ghost_scared_left'] = None
        
        # Load eyes images
        try:
            self.ghost_images['eyes_right'] = pygame.image.load('public/eyes0.png').convert_alpha()
            self.ghost_images['eyes_left'] = pygame.image.load('public/eyes1.png').convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load eyes images: {e}")
            self.ghost_images['eyes_right'] = None
            self.ghost_images['eyes_left'] = None

    def calculate_exit_gate_position(self):
        """Calculate the exit gate position at the opposite corner from Pacman start"""
        start_row, start_col = self.start
        
        # Calculate opposite corner
        opposite_row = self.maze_gen.height - 1 - start_row
        opposite_col = self.maze_gen.width - 1 - start_col
        
        # Find the nearest valid position to the opposite corner
        best_pos = (opposite_row, opposite_col)
        best_distance = float('inf')
        
        # Search in a small area around the opposite corner
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                test_row = opposite_row + dr
                test_col = opposite_col + dc
                
                if (0 <= test_row < self.maze_gen.height and 
                    0 <= test_col < self.maze_gen.width and
                    self.maze[test_row, test_col] == 0):  # Valid path
                    
                    distance = abs(test_row - opposite_row) + abs(test_col - opposite_col)
                    if distance < best_distance:
                        best_distance = distance
                        best_pos = (test_row, test_col)
        
        return best_pos

    def place_dots_and_pellets(self):
        """Place dots and power pellets on the maze"""
        self.dots = []
        self.power_pellets = []

        # First, collect all valid positions (open paths)
        valid_positions = []
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    # Skip start and goal positions
                    if not ((y, x) == self.start or (y, x) == self.goal):
                        valid_positions.append((x, y))

        # Randomly select positions for power pellets with minimum distance constraint
        power_pellet_positions = []
        min_distance = 8  # Minimum distance between power pellets
        max_pellets = 12  # Maximum number of power pellets
        attempts = 0
        max_attempts = 1000

        while len(power_pellet_positions) < max_pellets and attempts < max_attempts:
            attempts += 1
            # Pick a random position
            if not valid_positions:
                break

            candidate = random.choice(valid_positions)
            x, y = candidate

            # Check if this position is far enough from existing power pellets
            is_valid = True
            for px, py in power_pellet_positions:
                distance = math.sqrt((x - px)**2 + (y - py)**2)
                if distance < min_distance:
                    is_valid = False
                    break

            if is_valid:
                power_pellet_positions.append(candidate)
                # Remove nearby positions from valid_positions to speed up search
                valid_positions = [pos for pos in valid_positions
                                 if math.sqrt((pos[0] - x)**2 + (pos[1] - y)**2) >= min_distance]

        # Place dots and power pellets
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    center = ((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)

                    if (x, y) in power_pellet_positions:
                        self.power_pellets.append(center)
                    else:
                        # Place regular dots everywhere except start and goal
                        if not ((y, x) == self.start or (y, x) == self.goal):
                            self.dots.append(center)

    def place_bombs(self):
        """Place random bombs as obstacles on the maze"""
        self.bombs = []

        # Collect all valid positions (open paths) excluding start, goal, and areas near them
        valid_positions = []
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    # Skip start and goal positions and areas near them
                    if not ((y, x) == self.start or (y, x) == self.goal):
                        # Also skip positions too close to start and goal
                        start_dist = math.sqrt((x - self.start[1])**2 + (y - self.start[0])**2)
                        goal_dist = math.sqrt((x - self.goal[1])**2 + (y - self.goal[0])**2)
                        if start_dist > 5 and goal_dist > 5:  # Keep bombs away from start/goal
                            # Check if not adjacent to walls
                            if self.is_not_adjacent_to_wall(y, x):
                                valid_positions.append((x, y))

        # Select bomb positions with minimum distance of 10 cells
        bomb_positions = self.select_positions_with_min_distance(valid_positions, min_distance=10, max_bombs=5)

        # Place bombs
        for x, y in bomb_positions:
            center = ((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)
            self.bombs.append(center)

    def is_not_adjacent_to_wall(self, y, x):
        """Check if position (y,x) is not adjacent to any wall"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                if self.maze[ny, nx] == 1:  # Wall
                    return False
        return True

    def select_positions_with_min_distance(self, positions, min_distance=10, max_bombs=5):
        """Select positions ensuring minimum distance between them"""
        selected = []
        for pos in random.sample(positions, len(positions)):  # Shuffle to randomize
            if len(selected) >= max_bombs:
                break
            if all(math.sqrt((pos[0] - s[0])**2 + (pos[1] - s[1])**2) >= min_distance for s in selected):
                selected.append(pos)
        return selected

    def create_ghosts(self):
        """Create exactly 4 ghosts with different colors and behaviors"""
        # Clear existing ghosts first to prevent duplication
        self.ghosts = []
        
        ghost_colors = [self.RED, self.PINK, self.CYAN, self.ORANGE, self.YELLOW, self.BLUE]
        ghost_names = ["Blinky", "Pinky", "Inky", "Clyde"]

        # Find a valid starting position near the center
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        
        # Search for valid positions around center
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)
        
        # Create exactly 4 ghosts starting from valid center position
        for i in range(4):
            color = ghost_colors[i]
            name = ghost_names[i]
            
            # All ghosts start at the same valid position and spread out
            ghost = {
                'name': name,
                'color': color,
                'pos': [float(ghost_start_pos[1]), float(ghost_start_pos[0])],  # [col, row] format
                'direction': [0, 0],
                'speed': 1.2,  # Slightly slower than pacman
                'mode': 'random',  # Start in random mode to spread out
                'target': None,
                'animation': 1,
                'last_direction_change': 0,
                'position_history': [],  # Track recent positions for anti-stuck
                'stuck_counter': 0,  # Count consecutive moves to same area
                'last_position': None,  # Last position for detecting loops
                'random_timer': 0,  # Timer for random mode duration
                'spread_timer': 0,  # Timer to ensure ghosts spread from center
                'scared': False,  # Whether ghost is frightened
                'scared_timer': 0  # Timer for scared state duration
            }
            self.ghosts.append(ghost)

    def find_valid_ghost_start_position(self, center_row, center_col):
        """Find a valid starting position for ghosts near the center"""
        # First, check if center itself is valid
        if (0 <= center_row < self.maze_gen.height and 
            0 <= center_col < self.maze_gen.width and
            self.maze[center_row, center_col] == 0):  # Valid path
            return (center_row, center_col)
        
        # Search in expanding circles around center
        for radius in range(1, min(self.maze_gen.height, self.maze_gen.width) // 2):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    # Only check positions on the edge of current radius
                    if abs(dr) == radius or abs(dc) == radius:
                        test_row = center_row + dr
                        test_col = center_col + dc
                        
                        if (0 <= test_row < self.maze_gen.height and 
                            0 <= test_col < self.maze_gen.width and
                            self.maze[test_row, test_col] == 0):  # Valid path
                            return (test_row, test_col)
        
        # Fallback: use Pacman's start position if nothing found
        return self.start

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

    def draw_bombs(self):
        """Draw bombs as realistic bomb obstacles"""
        for bomb in self.bombs:
            bomb_x, bomb_y = bomb
            
            # Bomb body colors
            GRAY = (128, 128, 128)
            DARK_GRAY = (64, 64, 64)
            WHITE = (255, 255, 255)
            RED = (255, 0, 0)
            
            # Draw bomb body with gradient effect
            bomb_radius = 8
            
            # Create gradient effect by drawing multiple circles of decreasing size
            for i in range(bomb_radius, 0, -1):
                # Calculate color gradient from gray to dark gray
                intensity = 128 - (i * 8)  # Decrease intensity towards center
                intensity = max(32, min(128, intensity))  # Clamp between 32 and 128
                color = (intensity, intensity, intensity)
                
                # Draw concentric circles for gradient effect
                pygame.draw.circle(self.screen, color, (int(bomb_x), int(bomb_y)), i)
            
            # Draw outer highlight (white rim)
            pygame.draw.circle(self.screen, WHITE, (int(bomb_x), int(bomb_y)), bomb_radius, 1)
            
            # Draw fuse (dây cháy)
            fuse_length = 12
            fuse_start_x = bomb_x
            fuse_start_y = bomb_y - bomb_radius - 2
            fuse_end_x = bomb_x + 3
            fuse_end_y = bomb_y - bomb_radius - fuse_length
            
            # Draw fuse line (black)
            pygame.draw.line(self.screen, self.BLACK, 
                           (int(fuse_start_x), int(fuse_start_y)), 
                           (int(fuse_end_x), int(fuse_end_y)), 2)
            
            # Draw fuse knot (red circle at end)
            pygame.draw.circle(self.screen, RED, (int(fuse_end_x), int(fuse_end_y)), 3)
            
            # Add some spark effect at the fuse end
            spark_positions = [
                (fuse_end_x + 2, fuse_end_y - 1),
                (fuse_end_x - 1, fuse_end_y + 2),
                (fuse_end_x - 2, fuse_end_y - 2)
            ]
            for spark in spark_positions:
                pygame.draw.circle(self.screen, (255, 255, 0), (int(spark[0]), int(spark[1])), 1)

    def draw_exit_gate(self):
        """Draw the exit gate at the opposite corner"""
        if hasattr(self, 'exit_gate'):
            gate_row, gate_col = self.exit_gate
            center = ((gate_col + 0.5) * self.cell_size, (gate_row + 0.5) * self.cell_size)
            
            # Draw exit gate as a glowing portal
            gate_size = self.cell_size // 2 - 2
            
            # Outer glow
            pygame.draw.circle(self.screen, (255, 255, 255), center, gate_size + 3)
            # Inner portal
            pygame.draw.circle(self.screen, (0, 255, 0), center, gate_size)
            # Center sparkle
            pygame.draw.circle(self.screen, (255, 255, 255), center, gate_size // 2)

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
        """Draw ghosts using images from public folder"""
        for ghost in self.ghosts:
            col, row = ghost['pos']
            center = (col * self.cell_size + self.cell_size // 2,
                     row * self.cell_size + self.cell_size // 2)

            # Determine direction for image selection
            direction = ghost['direction']
            facing_right = direction[0] > 0 or (direction[0] == 0 and direction[1] == 0)  # Default to right if stationary
            
            # Get ghost index (0-3) based on color
            ghost_index = 0
            if ghost['color'] == self.PINK:
                ghost_index = 1
            elif ghost['color'] == self.CYAN:
                ghost_index = 2
            elif ghost['color'] == self.ORANGE:
                ghost_index = 3
            
            # Select appropriate image
            if ghost.get('scared', False):
                # Use scared ghost image
                image_key = 'ghost_scared_right' if facing_right else 'ghost_scared_left'
            else:
                # Use normal ghost image
                image_key = f'ghost{ghost_index}_right' if facing_right else f'ghost{ghost_index}_left'
            
            ghost_image = self.ghost_images.get(image_key)
            
            if ghost_image:
                # Scale image to fit cell size
                scaled_image = pygame.transform.scale(ghost_image, (self.cell_size, self.cell_size))
                # Position image centered on ghost position
                image_rect = scaled_image.get_rect(center=center)
                self.screen.blit(scaled_image, image_rect)
            else:
                # Fallback to original drawing if image not available
                self.draw_ghost_fallback(ghost, center)

    def draw_ghost_fallback(self, ghost, center):
        """Fallback drawing method when images are not available"""
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
            mode_text = "AUTO" if self.auto_mode else "MANUAL"
            
            # Show ghost modes
            ghost_modes = [f"{g['name'][:1]}:{g['mode'][:3]}" for g in self.ghosts[:2]]  # Show first 2 ghosts
            ghost_info = f" {' '.join(ghost_modes)}"
            
            path_info = ""
            if self.show_shortest_path:
                path_steps = len(self.shortest_path) - 1 if self.shortest_path else 0
                path_info = f" | Path: {path_steps} steps"
            
            inst_text = self.font.render(f"{mode_text} | {ghost_info}{path_info} | A: Toggle Auto | H: Path | P: Pause | R: Restart", True, self.YELLOW)
            self.screen.blit(inst_text, (10, ui_y + 30))

        elif self.game_state == "paused":
            pause_text = self.large_font.render("PAUSED", True, self.YELLOW)
            self.screen.blit(pause_text, (self.screen_width // 2 - 60, self.screen_height // 2))

        elif self.game_state == "game_over":
            game_over_text = self.large_font.render("GAME OVER", True, self.RED)
            restart_text = self.font.render("Press R to restart", True, self.WHITE)
            self.screen.blit(game_over_text, (self.screen_width // 2 - 100, self.screen_height // 2 - 20))
            self.screen.blit(restart_text, (self.screen_width // 2 - 70, self.screen_height // 2 + 20))

        elif self.game_state == "level_complete":
            complete_text = self.large_font.render("LEVEL COMPLETE!", True, (0, 255, 0))
            bonus_text = self.font.render(f"Exit Gate Bonus: +1000", True, (255, 255, 0))
            next_text = self.font.render("Press N for next level", True, self.WHITE)
            self.screen.blit(complete_text, (self.screen_width // 2 - 120, self.screen_height // 2 - 40))
            self.screen.blit(bonus_text, (self.screen_width // 2 - 80, self.screen_height // 2))
            self.screen.blit(next_text, (self.screen_width // 2 - 60, self.screen_height // 2 + 40))

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
                step_size = self.pacman_speed * 0.1  # Use pacman_speed for consistent movement
                
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
        """Move ghosts with GRID-BASED movement - ONE BLOCK AT A TIME with enhanced AI"""
        for ghost in self.ghosts:
            # Get current block position
            current_col = int(round(ghost['pos'][0]))
            current_row = int(round(ghost['pos'][1]))
            
            # Check if ghost is in valid position
            if not self.is_valid_position(current_col, current_row):
                # Reset ghost to a safe position
                center_row = self.maze_gen.height // 2
                center_col = self.maze_gen.width // 2
                ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)
                ghost['pos'] = [float(ghost_start_pos[1]), float(ghost_start_pos[0])]
                ghost['direction'] = [0, 0]
                continue
            
            # Track position history for anti-stuck detection
            current_pos = (current_row, current_col)
            if ghost['last_position'] != current_pos:
                ghost['position_history'].append(current_pos)
                if len(ghost['position_history']) > 15:  # Keep more history
                    ghost['position_history'].pop(0)
                ghost['last_position'] = current_pos
                ghost['stuck_counter'] = 0
            else:
                ghost['stuck_counter'] += 1
            
            # Detect if ghost is stuck in a loop
            is_stuck = self.detect_stuck_ghost(ghost)
            
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
                # Smart direction selection with momentum preservation
                new_direction = self.get_smart_direction(ghost, valid_directions, current_pos, is_stuck)

                # Calculate target block position
                target_col = current_col + new_direction[0]
                target_row = current_row + new_direction[1]
                
                # FINAL STRICT CHECK before moving
                if self.is_valid_position(target_col, target_row):
                    ghost['direction'] = new_direction
                    
                    # Smooth animation towards target block
                    step_size = 0.12  # Slightly faster for smoother movement
                    
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

                # Update spread timer
                ghost['spread_timer'] += 1

                # Enhanced mode switching with spreading logic
                if ghost['mode'] == 'random' and ghost['spread_timer'] > 60:  # After spreading
                    # Switch to scatter or chase based on distance from center
                    center_row = self.maze_gen.height // 2
                    center_col = self.maze_gen.width // 2
                    distance_from_center = abs(current_row - center_row) + abs(current_col - center_col)
                    
                    if distance_from_center > 10:  # Far from center
                        ghost['mode'] = 'scatter' if random.random() < 0.6 else 'chase'
                        ghost['random_timer'] = 0
                    else:
                        # Stay in random mode until spread out more
                        pass
                elif random.random() < 0.001:  # Reduced frequency for mode switching
                    if ghost['mode'] == 'chase':
                        ghost['mode'] = 'scatter'
                    elif ghost['mode'] == 'scatter':
                        ghost['mode'] = 'chase'
                
                # Random mode timer (backup)
                if ghost['mode'] == 'random':
                    ghost['random_timer'] += 1
                    if ghost['random_timer'] > 300:  # 5 seconds at 60fps
                        ghost['random_timer'] = 0
                        ghost['mode'] = 'scatter'

    def get_smart_direction(self, ghost, valid_directions, current_pos, is_stuck):
        """Smart direction selection that reduces oscillation and improves flow"""
        if not valid_directions:
            return random.choice([[0, -1], [0, 1], [-1, 0], [1, 0]])
        
        current_row, current_col = current_pos
        current_direction = ghost['direction']
        
        # Check if we're in a corridor (only 2 directions available)
        is_in_corridor = len(valid_directions) == 2
        
        # Check if we're on a long straight path
        is_on_long_path = self.is_on_long_straight_path(ghost, current_pos, current_direction)
        
        # Prioritize directions based on context
        direction_scores = {}
        
        for direction in valid_directions:
            score = 10  # Base score
            
            # 1. MASSIVE momentum bonus - especially for corridors and long paths
            if direction == current_direction:
                base_momentum_bonus = 80  # Increased from 50
                
                if is_in_corridor:
                    score += base_momentum_bonus * 2  # Double bonus in corridors
                elif is_on_long_path:
                    score += base_momentum_bonus * 1.5  # 1.5x bonus on long paths
                else:
                    score += base_momentum_bonus
            
            # 2. HEAVILY penalize opposite direction unless absolutely necessary
            opposite_direction = [-current_direction[0], -current_direction[1]]
            if direction == opposite_direction:
                if len(valid_directions) == 1:
                    score += 0  # No penalty if only option
                elif is_stuck and len(valid_directions) == 2:
                    score -= 20  # Moderate penalty even when stuck in corridor
                elif is_in_corridor:
                    score -= 200  # Massive penalty for reversing in corridor
                elif is_on_long_path:
                    score -= 150  # Heavy penalty for reversing on long path
                else:
                    score -= 100  # Heavy penalty normally
            
            # 3. Prefer directions that lead to more open areas
            target_col = current_col + direction[0]
            target_row = current_row + direction[1]
            
            # Count adjacent open spaces from target position
            open_spaces = 0
            for dx, dy in [[0, -1], [0, 1], [-1, 0], [1, 0]]:
                check_col = target_col + dx
                check_row = target_row + dy
                if self.is_valid_position(check_col, check_row):
                    open_spaces += 1
            
            score += open_spaces * 5  # Bonus for leading to open areas
            
            # 4. Heavily avoid recently visited areas (stronger penalty)
            target_pos = (target_row, target_col)
            if target_pos in ghost['position_history'][-8:]:
                recent_index = len(ghost['position_history']) - ghost['position_history'][::-1].index(target_pos) - 1
                recency_penalty = (8 - (len(ghost['position_history']) - recent_index)) * 8  # Increased from 3
                score -= recency_penalty
            
            # 5. Extra penalty for positions visited very recently (last 3 moves)
            if target_pos in ghost['position_history'][-3:]:
                score -= 50  # Heavy penalty for very recent positions
            
            # 6. Mode-specific bonuses (reduced to not override momentum)
            if ghost['mode'] == 'chase':
                # Bonus for moving towards Pacman
                pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
                current_distance = abs(current_col - pacman_col) + abs(current_row - pacman_row)
                new_distance = abs(target_col - pacman_col) + abs(target_row - pacman_row)
                if new_distance < current_distance:
                    score += 8  # Reduced from 15
            
            elif ghost['mode'] == 'scatter':
                # Bonus for moving towards corner
                corners = {
                    'Blinky': (self.maze_gen.width - 2, 1),
                    'Pinky': (1, 1),
                    'Inky': (self.maze_gen.width - 2, self.maze_gen.height - 2),
                    'Clyde': (1, self.maze_gen.height - 2)
                }
                target_corner = corners.get(ghost['name'], (self.maze_gen.width // 2, self.maze_gen.height // 2))
                corner_col, corner_row = target_corner
                
                current_distance = abs(current_col - corner_col) + abs(current_row - corner_row)
                new_distance = abs(target_col - corner_col) + abs(target_row - corner_row)
                if new_distance < current_distance:
                    score += 5  # Reduced from 10
            
            direction_scores[tuple(direction)] = score
        
        # Choose direction with highest score
        best_direction = max(direction_scores.keys(), key=lambda d: direction_scores[d])
        
        # Reduce randomness to preserve momentum better
        random_chance = 0.05 if is_in_corridor or is_on_long_path else 0.1  # Reduced randomness
        
        if random.random() < random_chance:
            # But still prefer higher-scored directions
            weighted_choices = []
            for direction, score in direction_scores.items():
                weight = max(1, int(score // 15))  # Convert score to integer weight
                weighted_choices.extend([list(direction)] * weight)
            return random.choice(weighted_choices)
        
        return list(best_direction)

    def is_on_long_straight_path(self, ghost, current_pos, current_direction):
        """Check if ghost is on a long straight path where it should continue straight"""
        if current_direction == [0, 0]:  # Not moving
            return False
        
        current_row, current_col = current_pos
        
        # Check how far we can go straight in current direction
        straight_distance = 0
        check_col, check_row = current_col, current_row
        
        # Look ahead in current direction
        for step in range(1, 8):  # Check up to 8 steps ahead
            check_col += current_direction[0]
            check_row += current_direction[1]
            
            if not self.is_valid_position(check_col, check_row):
                break
                
            straight_distance += 1
            
            # Check if this position is an intersection (more than 2 directions)
            directions_at_pos = 0
            for dx, dy in [[0, -1], [0, 1], [-1, 0], [1, 0]]:
                if self.is_valid_position(check_col + dx, check_row + dy):
                    directions_at_pos += 1
            
            # If we hit an intersection, stop counting
            if directions_at_pos > 2:
                break
        
        # Consider it a long path if we can go straight for 4+ steps
        return straight_distance >= 4

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

    def should_prefer_turns(self, ghost, valid_directions):
        """Determine if ghost should prefer turning at intersections"""
        current_col = int(round(ghost['pos'][0]))
        current_row = int(round(ghost['pos'][1]))
        
        # Count available directions
        num_directions = len(valid_directions)
        
        # If at intersection (more than 2 directions), prefer turning
        if num_directions > 2:
            return True
            
        # If going straight would lead to dead end, prefer turning
        if ghost['direction'] in valid_directions:
            straight_col = current_col + ghost['direction'][0] * 2
            straight_row = current_row + ghost['direction'][1] * 2
            
            # Check if 2 steps ahead is a dead end
            straight_directions = [[0, -1], [0, 1], [-1, 0], [1, 0]]
            straight_valid = 0
            for dx, dy in straight_directions:
                if self.is_valid_position(straight_col + dx, straight_row + dy):
                    straight_valid += 1
            
            if straight_valid <= 2:  # Dead end or corridor ahead
                return True
        
        return False

    def get_turn_preference_direction(self, ghost, valid_directions):
        """Get direction that prefers turns over straight movement"""
        if not valid_directions:
            return random.choice([[0, -1], [0, 1], [-1, 0], [1, 0]])
        
        # Separate straight and turn directions
        straight_directions = []
        turn_directions = []
        
        for direction in valid_directions:
            if direction == ghost['direction']:
                straight_directions.append(direction)
            else:
                turn_directions.append(direction)
        
        # Prefer turns 70% of the time if available
        if turn_directions and random.random() < 0.7:
            return random.choice(turn_directions)
        elif straight_directions:
            return random.choice(straight_directions)
        else:
            return random.choice(valid_directions)

    def detect_stuck_ghost(self, ghost):
        """Detect if ghost is stuck in a loop or confined area"""
        if len(ghost['position_history']) < 6:
            return False
            
        history = ghost['position_history']
        
        # Check for small loops (2-4 positions)
        for loop_size in range(2, min(5, len(history)//2 + 1)):
            if len(history) >= loop_size * 2:
                recent_pattern = history[-loop_size:]
                previous_pattern = history[-loop_size*2:-loop_size]
                if recent_pattern == previous_pattern:
                    return True
        
        # Check if ghost hasn't moved much (confined area)
        if ghost['stuck_counter'] > 12:
            return True
            
        # Check if ghost is oscillating between few positions
        unique_positions = set(history[-10:])
        if len(unique_positions) <= 2 and len(history) >= 8:
            return True
            
        # Enhanced back-and-forth detection (main issue)
        if len(history) >= 6:
            # Check for A->B->A->B->A->B pattern (ping-pong movement)
            positions = history[-6:]
            if (positions[0] == positions[2] == positions[4] and 
                positions[1] == positions[3] == positions[5] and
                positions[0] != positions[1]):
                return True
        
        # Check for recent reversal pattern (going back and forth on same path)
        if len(history) >= 4:
            # If last 4 moves are just 2 positions alternating
            recent_4 = history[-4:]
            if len(set(recent_4)) == 2 and recent_4[0] == recent_4[2] and recent_4[1] == recent_4[3]:
                return True
        
        return False

    def get_anti_stuck_direction(self, ghost, valid_directions, current_pos):
        """Get direction to escape stuck situation using pathfinding"""
        if not valid_directions:
            return random.choice([[0, -1], [0, 1], [-1, 0], [1, 0]])
        
        # Try to find a path to a distant safe location
        current_row, current_col = current_pos
        
        # Choose a target far from current position and recent history
        best_target = None
        best_distance = 0
        
        # Try several potential targets
        for attempt in range(5):
            # Pick a random distant location
            target_row = random.randint(1, self.maze_gen.height - 2)
            target_col = random.randint(1, self.maze_gen.width - 2)
            
            # Check if it's a valid path and far enough
            if self.is_valid_position(target_col, target_row):
                distance = abs(target_row - current_row) + abs(target_col - current_col)
                if distance > best_distance and distance > 5:  # At least 5 blocks away
                    # Check if this target is not in recent history
                    target_pos = (target_row, target_col)
                    if target_pos not in ghost['position_history'][-15:]:  # Not visited recently
                        best_target = (target_row, target_col)
                        best_distance = distance
        
        if best_target:
            # Use Dijkstra to find path to target (ghosts don't avoid bombs)
            path, distance = self.dijkstra.shortest_path(current_pos, best_target)
            if path and len(path) > 1:
                next_pos = path[1]
                direction = [next_pos[1] - current_col, next_pos[0] - current_row]
                if direction in valid_directions:
                    return direction
        
        # Fallback: choose direction that leads to unexplored area
        best_direction = random.choice(valid_directions)
        max_distance = 0
        
        for direction in valid_directions:
            target_row = current_row + direction[1]
            target_col = current_col + direction[0]
            target_pos = (target_row, target_col)
            
            # Calculate distance to nearest recent position
            min_recent_distance = float('inf')
            for recent_pos in ghost['position_history'][-10:]:
                dist = abs(target_row - recent_pos[0]) + abs(target_col - recent_pos[1])
                min_recent_distance = min(min_recent_distance, dist)
            
            if min_recent_distance > max_distance:
                max_distance = min_recent_distance
                best_direction = direction
        
        return best_direction

    def get_random_direction(self, ghost, valid_directions):
        """Get random direction with enhanced randomness"""
        if not valid_directions:
            return random.choice([[0, -1], [0, 1], [-1, 0], [1, 0]])
        
        # 70% pure random, 30% weighted towards unexplored directions
        if random.random() < 0.7:
            return random.choice(valid_directions)
        else:
            # Weight towards directions leading to less visited areas
            current_row = int(round(ghost['pos'][1]))
            current_col = int(round(ghost['pos'][0]))
            
            best_direction = random.choice(valid_directions)
            max_score = 0
            
            for direction in valid_directions:
                target_row = current_row + direction[1]
                target_col = current_col + direction[0]
                target_pos = (target_row, target_col)
                
                # Score based on how recently this area was visited
                score = 10  # Base score
                if target_pos in ghost['position_history']:
                    # Reduce score based on recency
                    last_visit_index = len(ghost['position_history']) - ghost['position_history'][::-1].index(target_pos) - 1
                    recency_penalty = (len(ghost['position_history']) - last_visit_index) / len(ghost['position_history'])
                    score -= recency_penalty * 5
                
                if score > max_score:
                    max_score = score
                    best_direction = direction
            
            return best_direction

    def set_escape_target(self):
        """Set target to exit gate for emergency escape"""
        if hasattr(self, 'exit_gate'):
            self.auto_target = self.exit_gate
            self.calculate_auto_path()
            print(" Escape mode: Heading to exit gate!")
        else:
            print(" No exit gate found!")

    def find_auto_target(self):
        """GOAL-FIRST target finding - Ưu tiên goal tuyệt đối"""
        try:
            # Sử dụng logic goal-first mới
            self.find_goal_first()

            # Nếu tìm được goal, set làm auto_target
            if self.current_goal:
                self.auto_target = self.current_goal
                self.calculate_auto_path()
                print(f"Auto target set: {self.auto_target}")
            else:
                print("No auto target found")
                self.auto_target = None
                self.auto_path = []

        except Exception as e:
            print(f"Error in find_auto_target: {e}")
            self.auto_target = None
            self.auto_path = []

    def _emergency_ghost_avoidance(self, nearby_ghosts):
        """Xử lý việc quay đầu và rẽ vào ngã gần nhất khi gặp ghost - CẢI THIỆN"""
        current_time = pygame.time.get_ticks()

        # Khởi tạo biến nếu chưa có
        if not hasattr(self, 'last_emergency_turn'):
            self.last_emergency_turn = 0

        # Giảm cooldown để phản ứng nhanh hơn (100ms thay vì 200ms)
        if current_time - self.last_emergency_turn < 100:  # 100ms cooldown
            return False

        pacman_row, pacman_col = int(self.pacman_pos[1]), int(self.pacman_pos[0])
        
        # Dự đoán vị trí ma trong 2-3 bước tiếp theo
        predicted_ghost_positions = []
        for ghost_pos, distance in nearby_ghosts:
            ghost_row, ghost_col = ghost_pos
            
            # Tìm ghost object để lấy direction
            ghost_obj = None
            for g in self.ghosts:
                g_row, g_col = int(g['pos'][1]), int(g['pos'][0])
                if g_row == ghost_row and g_col == ghost_col:
                    ghost_obj = g
                    break
            
            if ghost_obj and ghost_obj['direction'] != [0, 0]:
                # Dự đoán 2-3 bước tiếp theo
                dx, dy = ghost_obj['direction']
                for steps in range(1, 4):  # Dự đoán 1-3 bước
                    pred_col = ghost_col + dx * steps
                    pred_row = ghost_row + dy * steps
                    if self.is_valid_position(pred_col, pred_row):
                        predicted_ghost_positions.append((pred_row, pred_col, distance + steps))
        
        # Kết hợp vị trí hiện tại và dự đoán
        all_dangerous_positions = [(pos[0], pos[1], dist) for pos, dist in nearby_ghosts]
        all_dangerous_positions.extend(predicted_ghost_positions)

        # Tìm ghost gần nhất (bao gồm cả dự đoán)
        nearest_ghost_pos, min_distance = min(nearby_ghosts, key=lambda x: x[1])
        ghost_row, ghost_col = nearest_ghost_pos

        # CRITICAL DANGER: Ghost cực gần (<= 2 ô)
        if min_distance <= 2:
            print(f"🚨 NGUY HIỂM CỰC! Ghost cách {min_distance} ô!")
            
            # Tìm hướng an toàn nhất bằng cách tính toán khoảng cách đến TẤT CẢ ghosts
            escape_options = []
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
            
            for dx, dy in directions:
                new_col, new_row = pacman_col + dx, pacman_row + dy
                
                if self.is_valid_position(new_col, new_row):
                    # Tính khoảng cách đến tất cả ghosts (bao gồm dự đoán)
                    min_dist_to_any_ghost = float('inf')
                    
                    for danger_row, danger_col, _ in all_dangerous_positions:
                        dist = abs(new_row - danger_row) + abs(new_col - danger_col)
                        min_dist_to_any_ghost = min(min_dist_to_any_ghost, dist)
                    
                    # Kiểm tra xem có dẫn đến dead end không
                    is_dead_end = self._is_dead_end(new_col, new_row)
                    
                    # Tính score: khoảng cách cao hơn = tốt hơn, dead end = tệ
                    safety_score = min_dist_to_any_ghost - (10 if is_dead_end else 0)
                    escape_options.append((dx, dy, safety_score, min_dist_to_any_ghost))
            
            if escape_options:
                # Sắp xếp theo safety score (cao nhất trước)
                escape_options.sort(key=lambda x: x[2], reverse=True)
                best_escape = escape_options[0]
                dx, dy, score, safety_dist = best_escape
                
                self.pacman_next_direction = [dx, dy]
                self.last_emergency_turn = current_time
                print(f"🛡️ Emergency escape: {self.pacman_next_direction} (safety: {safety_dist})")
                return True

        # HIGH DANGER: Ghost ở khoảng cách trung bình (3 ô) 
        elif min_distance <= 3:  # giảm từ 3-6 xuống chỉ 3
            print(f"⚠️ Ghost ở khoảng cách {min_distance} ô, tìm đường tránh...")
            
            # Tìm đường đi tránh ghosts với lookahead
            escape_path = self._find_smart_escape_path(pacman_col, pacman_row, all_dangerous_positions)
            
            if escape_path and len(escape_path) > 1:
                next_pos = escape_path[1]  # Bước tiếp theo
                dx = next_pos[1] - pacman_col  # next_pos is (row, col)
                dy = next_pos[0] - pacman_row
                
                self.pacman_next_direction = [dx, dy]
                self.last_emergency_turn = current_time
                print(f"🛤️ Smart escape path: {self.pacman_next_direction}")
                return True
            else:
                # Fallback: chọn hướng tăng khoảng cách nhiều nhất
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                best_direction = None
                max_distance_increase = 0
                
                for dx, dy in directions:
                    new_col, new_row = pacman_col + dx, pacman_row + dy
                    if self.is_valid_position(new_col, new_row):
                        # Tính khoảng cách đến ghost gần nhất sau khi di chuyển
                        distance_after_move = abs(new_row - ghost_row) + abs(new_col - ghost_col)
                        distance_increase = distance_after_move - min_distance
                        
                        if distance_increase > max_distance_increase:
                            max_distance_increase = distance_increase
                            best_direction = [dx, dy]
                
                if best_direction:
                    self.pacman_next_direction = best_direction
                    self.last_emergency_turn = current_time
                    print(f"🛤️ Fallback escape: {self.pacman_next_direction}")
                    return True

        return False  # Không thể xử lý

    def _is_dead_end(self, col, row):
        """Kiểm tra xem vị trí có phải là dead end không (chỉ có 1 lối ra)"""
        if not self.is_valid_position(col, row):
            return True
        
        valid_exits = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        
        for dx, dy in directions:
            next_col, next_row = col + dx, row + dy
            if self.is_valid_position(next_col, next_row):
                valid_exits += 1
        
        return valid_exits <= 1  # Dead end if only 1 or 0 exits

    def _find_smart_escape_path(self, start_col, start_row, dangerous_positions, max_depth=6):
        """Tìm đường thoát thông minh tránh ghosts với lookahead và line of sight"""
        import heapq
        from collections import deque
        
        start = (start_row, start_col)  # (row, col) format
        
        # Tạo danger map với penalty - chỉ cho ghosts có line of sight
        danger_map = {}
        for danger_row, danger_col, original_dist in dangerous_positions:
            # Kiểm tra line of sight trước khi tạo danger zone
            if not self._has_line_of_sight(start, (danger_row, danger_col)):
                continue  # Bỏ qua ghost bị tường cản
                
            # Tạo vùng nguy hiểm xung quanh ghost (chỉ những vị trí có line of sight)
            for dr in range(-3, 4):  # 7x7 area around ghost
                for dc in range(-3, 4):
                    pos = (danger_row + dr, danger_col + dc)
                    if self.is_valid_position(pos[1], pos[0]):  # col, row for is_valid_position
                        # Kiểm tra line of sight từ ghost đến vị trí này
                        if self._has_line_of_sight((danger_row, danger_col), pos):
                            # Penalty giảm dần theo khoảng cách
                            distance_from_danger = abs(dr) + abs(dc)
                            penalty = max(0, 10 - distance_from_danger)  # Max penalty = 10
                            danger_map[pos] = danger_map.get(pos, 0) + penalty
        
        # BFS với penalty để tìm đường an toàn
        heap = [(0, 0, start, [start])]  # (total_cost, steps, position, path)
        visited = set()
        
        while heap:
            total_cost, steps, (row, col), path = heapq.heappop(heap)
            
            if (row, col) in visited or steps >= max_depth:
                continue
            visited.add((row, col))
            
            # Nếu đã đi đủ xa và ở vị trí an toàn, return path
            if steps >= 3:  # Ít nhất 3 bước
                danger_level = danger_map.get((row, col), 0)
                if danger_level <= 2:  # Tương đối an toàn
                    return path
            
            # Thử tất cả hướng di chuyển
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_row, new_col = row + dy, col + dx
                new_pos = (new_row, new_col)
                
                if (new_pos not in visited and 
                    self.is_valid_position(new_col, new_row) and
                    not self._is_dead_end(new_col, new_row)):  # Tránh dead ends
                    
                    # Tính cost dựa trên danger level
                    danger_penalty = danger_map.get(new_pos, 0)
                    move_cost = 1 + danger_penalty
                    new_total_cost = total_cost + move_cost
                    new_path = path + [new_pos]
                    
                    heapq.heappush(heap, (new_total_cost, steps + 1, new_pos, new_path))
        
        return None  # Không tìm thấy đường thoát an toàn

    def _check_ghosts_nearby(self, avoidance_radius=3):  # giảm từ 6 xuống 3
        """Kiểm tra ghosts với line of sight - chỉ phát hiện ma khi không bị tường cản"""
        pacman_row, pacman_col = int(self.pacman_pos[1]), int(self.pacman_pos[0])
        
        nearby_ghosts = []
        
        for ghost in self.ghosts:
            # Bỏ qua ghost đang scared - không cần tránh
            if ghost.get('scared', False):
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            current_distance = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            # Kiểm tra ghost ở trong bán kính hiện tại
            if current_distance <= avoidance_radius:
                # QUAN TRỌNG: Kiểm tra line of sight - có tường cản không?
                if self._has_line_of_sight((pacman_row, pacman_col), (ghost_row, ghost_col)):
                    nearby_ghosts.append(((ghost_row, ghost_col), current_distance))
                else:
                    # Ma bị tường cản, không coi là threat
                    continue
            
            # THÊM: Dự đoán collision path - chỉ nếu có line of sight
            if current_distance <= avoidance_radius + 1:  # Giảm vùng kiểm tra từ +3 xuống +1
                # Kiểm tra line of sight trước khi dự đoán
                if not self._has_line_of_sight((pacman_row, pacman_col), (ghost_row, ghost_col)):
                    continue  # Bỏ qua ma bị tường cản
                    
                ghost_direction = ghost.get('direction', [0, 0])
                pacman_direction = self.pacman_direction
                
                # Dự đoán vị trí trong 2-3 bước tới
                future_collision_risk = False
                
                for steps in range(1, 4):  # Kiểm tra 1-3 bước tới
                    # Vị trí dự đoán của ghost
                    future_ghost_col = ghost_col + ghost_direction[0] * steps
                    future_ghost_row = ghost_row + ghost_direction[1] * steps
                    
                    # Vị trí dự đoán của pacman
                    future_pacman_col = pacman_col + pacman_direction[0] * steps  
                    future_pacman_row = pacman_row + pacman_direction[1] * steps
                    
                    # Kiểm tra khoảng cách trong tương lai
                    future_distance = abs(future_pacman_row - future_ghost_row) + abs(future_pacman_col - future_ghost_col)
                    
                    if future_distance <= 2:  # Collision risk
                        # Kiểm tra line of sight cho vị trí tương lai
                        if (self.is_valid_position(future_ghost_col, future_ghost_row) and 
                            self.is_valid_position(future_pacman_col, future_pacman_row) and
                            self._has_line_of_sight((future_pacman_row, future_pacman_col), (future_ghost_row, future_ghost_col))):
                            future_collision_risk = True
                            break
                
                # Nếu có nguy cơ collision, coi như ghost đang ở gần
                if future_collision_risk and current_distance <= avoidance_radius + 1:  # Giảm từ +2 xuống +1
                    effective_distance = max(1, current_distance - 1)  # Giảm penalty từ -2 xuống -1
                    if ((ghost_row, ghost_col), effective_distance) not in nearby_ghosts:
                        nearby_ghosts.append(((ghost_row, ghost_col), effective_distance))
                        print(f"⚠️ Predicted collision with ghost at ({ghost_row}, {ghost_col}) in {steps} steps!")

        return nearby_ghosts

    def _has_line_of_sight(self, pos1, pos2):
        """Kiểm tra xem có đường nhìn thẳng từ pos1 đến pos2 không bị tường cản"""
        row1, col1 = pos1
        row2, col2 = pos2
        
        # Nếu cùng vị trí
        if pos1 == pos2:
            return True
            
        # Sử dụng Bresenham's line algorithm để kiểm tra từng điểm trên đường thẳng
        dx = abs(col2 - col1)
        dy = abs(row2 - row1)
        
        # Xác định hướng di chuyển
        step_x = 1 if col1 < col2 else -1
        step_y = 1 if row1 < row2 else -1
        
        # Khởi tạo error
        err = dx - dy
        
        current_col, current_row = col1, row1
        
        while True:
            # Kiểm tra vị trí hiện tại có phải là tường không
            if self.is_wall(current_col, current_row):
                return False  # Bị tường cản
                
            # Đã đến đích
            if current_col == col2 and current_row == row2:
                return True
                
            # Tính toán bước tiếp theo
            e2 = 2 * err
            
            if e2 > -dy:
                err -= dy
                current_col += step_x
                
            if e2 < dx:
                err += dx
                current_row += step_y

    def _find_fallback_target(self, pacman_pos, ghost_positions):
        """Find a safe fallback target when primary targets are unsafe - CẢI THIỆN"""
        try:
            print(f"🔍 Tìm vị trí an toàn từ {pacman_pos}, tránh {len(ghost_positions)} ghosts...")
            
            # Sử dụng Dijkstra với ghost avoidance để tìm target an toàn
            if hasattr(self, 'dijkstra'):
                # Tìm tất cả các vị trí trong bán kính 15 ô
                all_positions = []
                for radius in range(8, 16):  # Bắt đầu từ 8 ô để đảm bảo an toàn
                    for dr in range(-radius, radius + 1):
                        for dc in range(-radius, radius + 1):
                            if abs(dr) + abs(dc) == radius:  # Chỉ check vị trí ở exact radius
                                new_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                                
                                # Check if position is valid
                                if (new_pos[0] >= 0 and new_pos[0] < self.maze_gen.height and
                                    new_pos[1] >= 0 and new_pos[1] < self.maze_gen.width and
                                    not self.maze_gen.is_wall(new_pos)):
                                    
                                    # Tính safety score dựa trên khoảng cách đến tất cả ghosts
                                    min_ghost_dist = min([abs(new_pos[0] - gr) + abs(new_pos[1] - gc) 
                                                        for gr, gc in ghost_positions]) if ghost_positions else 10
                                    
                                    # Chỉ coi là an toàn nếu cách ghost ít nhất 4 ô
                                    if min_ghost_dist >= 4:
                                        # Kiểm tra xem có phải dead end không
                                        is_dead_end = self._is_dead_end(new_pos[1], new_pos[0])  # col, row for _is_dead_end
                                        
                                        if not is_dead_end:
                                            # Thử tìm đường đi bằng ghost avoidance algorithm
                                            path, cost = self.dijkstra.shortest_path_with_ghost_avoidance(
                                                pacman_pos, new_pos, ghost_positions, avoidance_radius=4
                                            )
                                            
                                            if path and len(path) > 1:
                                                # Tính final score: khoảng cách an toàn + khả năng di chuyển
                                                safety_score = min_ghost_dist + (10 / len(path))  # Ưu tiên đường ngắn
                                                all_positions.append((new_pos, safety_score, path, cost))
                    
                    # Nếu tìm được đủ vị trí an toàn, stop
                    if len(all_positions) >= 5:
                        break
                
                # Chọn vị trí tốt nhất
                if all_positions:
                    # Sắp xếp theo safety score (cao nhất trước)
                    all_positions.sort(key=lambda x: x[1], reverse=True)
                    best_pos, best_score, best_path, best_cost = all_positions[0]
                    
                    self.auto_target = best_pos
                    self.auto_path = best_path
                    print(f"🎯 Fallback target: {best_pos} (score: {best_score:.2f}, path: {len(best_path)} steps)")
                    return
            
            # Fallback method nếu Dijkstra ghost avoidance không có
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # right, left, down, up
            search_radius = 12  # Tăng search radius
            
            # Find safe positions in expanding radius
            for radius in range(6, search_radius + 1):  # Bắt đầu từ 6 ô
                safe_positions = []
                
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        if abs(dr) + abs(dc) != radius:  # Chỉ check positions ở exact radius
                            continue
                        
                        new_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                        
                        # Check if position is valid
                        if (new_pos[0] >= 0 and new_pos[0] < self.maze_gen.height and
                            new_pos[1] >= 0 and new_pos[1] < self.maze_gen.width and
                            not self.is_wall(new_pos[1], new_pos[0])):  # col, row for is_wall
                            
                            # Check safety from ghosts
                            min_ghost_dist = min([abs(new_pos[0] - gr) + abs(new_pos[1] - gc) 
                                                for gr, gc in ghost_positions]) if ghost_positions else 10
                            
                            if min_ghost_dist >= 5:  # Tăng khoảng cách an toàn từ 3 lên 5
                                # Kiểm tra không phải dead end
                                if not self._is_dead_end(new_pos[1], new_pos[0]):
                                    # Thử tìm đường đi bằng normal pathfinding
                                    if hasattr(self, 'dijkstra'):
                                        path, distance = self.dijkstra.shortest_path(pacman_pos, new_pos)
                                        if path:
                                            safe_positions.append((new_pos, min_ghost_dist, distance))
                
                # Choose best safe position from this radius
                if safe_positions:
                    # Sort by safety first, then by path distance
                    safe_positions.sort(key=lambda x: (-x[1], x[2]))
                    best_pos = safe_positions[0][0]
                    
                    self.auto_target = best_pos
                    print(f"🎯 Fallback target (normal): {best_pos} (safety: {safe_positions[0][1]})")
                    self.calculate_auto_path()
                    return
            
            # Emergency: try to move away from nearest ghost
            if ghost_positions:
                nearest_ghost = min(ghost_positions, 
                                  key=lambda g: abs(pacman_pos[0] - g[0]) + abs(pacman_pos[1] - g[1]))
                
                # Move in opposite direction from nearest ghost
                escape_directions = []
                if nearest_ghost[0] > pacman_pos[0]:  # Ghost below, move up
                    escape_directions.append((-3, 0))  # Move 3 steps up
                elif nearest_ghost[0] < pacman_pos[0]:  # Ghost above, move down
                    escape_directions.append((3, 0))   # Move 3 steps down
                
                if nearest_ghost[1] > pacman_pos[1]:  # Ghost right, move left
                    escape_directions.append((0, -3))  # Move 3 steps left
                elif nearest_ghost[1] < pacman_pos[1]:  # Ghost left, move right
                    escape_directions.append((0, 3))   # Move 3 steps right
                
                for dr, dc in escape_directions:
                    escape_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                    if (escape_pos[0] >= 0 and escape_pos[0] < self.maze_gen.height and
                        escape_pos[1] >= 0 and escape_pos[1] < self.maze_gen.width and
                        not self.is_wall(escape_pos[1], escape_pos[0])):
                        
                        self.auto_target = escape_pos
                        print(f"🚨 Emergency escape to {escape_pos}")
                        self.calculate_auto_path()
                        return
            
            print("❌ Không tìm được vị trí an toàn nào!")
            self.auto_target = None
            self.auto_path = []
            
        except Exception as e:
            print(f"❌ Error in _find_fallback_target: {e}")
            self.auto_target = None
            self.auto_path = []
            
            # Last resort: stay in place but keep looking
            print(" No safe escape found, staying vigilant")
            self.auto_target = pacman_pos
            self.auto_path = [pacman_pos]
            
        except Exception as e:
            print(f" Error in fallback target search: {e}")
            self.auto_target = pacman_pos
            self.auto_path = [pacman_pos]

    def calculate_auto_path(self):
        """Đơn giản hóa tính toán đường đi tự động"""
        if not self.auto_target:
            return

        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)

        # Lấy vị trí ma để tránh - chỉ ma không scared
        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                          if not g.get('scared', False)]

        try:
            # Sử dụng thuật toán đơn giản: đường đi với tránh ma
            avoidance_radius = getattr(config, 'GHOST_AVOIDANCE_RADIUS', 4)
            path, distance = self.dijkstra.shortest_path_with_ghost_avoidance(
                pacman_pos, self.auto_target, ghost_positions, avoidance_radius=avoidance_radius
            )

            if path and distance < float('inf'):
                self.auto_path = path
                print(f"Path calculated: {len(path)-1} steps to {self.auto_target}")
                return

        except Exception as e:
            print(f"Path calculation failed: {e}")

        # Fallback: đường đi bình thường nếu không tìm được đường tránh ma
        try:
            bomb_grid = self.get_bomb_grid_positions()
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, self.auto_target, bomb_grid)
            if path and distance < float('inf'):
                self.auto_path = path
                print(f"📍 Fallback path: {len(path)-1} steps to {self.auto_target} (avoiding bombs)")
            else:
                self.auto_path = []
                print(" No path found")
        except Exception as e:
            print(f" Fallback path failed: {e}")
            self.auto_path = []

    def calculate_shortest_path_to_goal(self):
        """Tính toán đường đi ngắn nhất từ vị trí Pacman hiện tại đến goal, tránh bom"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        pacman_pos = (pacman_row, pacman_col)
        
        # Get bomb positions in grid coordinates
        bomb_grid = self.get_bomb_grid_positions()
        
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, self.current_goal, bomb_grid)
            if path and distance < float('inf'):
                self.shortest_path = path
                print(f"🔍 Shortest path calculated: {len(path)-1} steps to goal (avoiding {len(bomb_grid)} bombs)")
            else:
                self.shortest_path = []
                print(" No path to goal found (considering bomb avoidance)")
        except Exception as e:
            print(f" Shortest path calculation failed: {e}")
            self.shortest_path = []

    def draw_shortest_path(self):
        """Vẽ đường đi ngắn nhất từ Pacman đến goal"""
        if not self.show_shortest_path or not self.shortest_path:
            return
            
        # Vẽ đường đi bằng các chấm xanh lục
        for row, col in self.shortest_path:
            center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
            pygame.draw.circle(self.screen, (0, 255, 0), center, 4)  # Bright Green
            
        # Vẽ điểm bắt đầu (Pacman hiện tại) bằng màu vàng
        if self.shortest_path:
            start_row, start_col = self.shortest_path[0]
            start_center = ((start_col + 0.5) * self.cell_size, (start_row + 0.5) * self.cell_size)
            pygame.draw.circle(self.screen, self.YELLOW, start_center, 6)
            
        # Vẽ điểm kết thúc (goal) bằng màu xanh lá đậm
        if len(self.shortest_path) > 1:
            goal_row, goal_col = self.shortest_path[-1]
            goal_center = ((goal_col + 0.5) * self.cell_size, (goal_row + 0.5) * self.cell_size)
            pygame.draw.circle(self.screen, (0, 128, 0), goal_center, 6)

    def _evaluate_path_safety(self, path, ghost_positions, avoidance_radius):
        """Evaluate if a path is safe from ghosts"""
        if not path or not ghost_positions:
            return True
        
        danger_count = 0
        total_positions = len(path)
        
        for pos in path:
            row, col = pos
            min_distance = float('inf')
            
            for ghost_pos in ghost_positions:
                ghost_row, ghost_col = ghost_pos
                distance = abs(row - ghost_row) + abs(col - ghost_col)
                min_distance = min(min_distance, distance)
            
            if min_distance <= avoidance_radius:
                danger_count += 1
        
        # Path is safe if less than threshold fraction of positions are dangerous
        safety_threshold = getattr(config, 'SAFETY_DANGER_THRESHOLD', 0.2)
        return (danger_count / total_positions) < safety_threshold

    def _calculate_path_safety_penalty(self, path, ghost_positions, avoidance_radius):
        """Calculate safety penalty for a path (higher = more dangerous)"""
        if not path or not ghost_positions:
            return 0
        
        total_penalty = 0
        
        for pos in path:
            row, col = pos
            min_distance = float('inf')
            
            for ghost_pos in ghost_positions:
                ghost_row, ghost_col = ghost_pos
                distance = abs(row - ghost_row) + abs(col - ghost_col)
                min_distance = min(min_distance, distance)
            
            if min_distance <= avoidance_radius:
                # Exponential penalty for dangerous positions
                penalty = (avoidance_radius - min_distance + 1) ** 2
                total_penalty += penalty
        
        return total_penalty

    def _validate_path_safety(self, path, ghost_positions):
        """Enhanced validation for path safety using multiple criteria"""
        if not path or not ghost_positions:
            return True
        
        min_safe_distance = getattr(config, 'MIN_SAFE_DISTANCE', 3)
        danger_threshold = getattr(config, 'PATH_DANGER_THRESHOLD', 0.7)
        
        dangerous_positions = 0
        total_positions = len(path)
        
        for pos in path:
            # Calculate minimum distance to any ghost
            min_ghost_distance = min(
                abs(pos[0] - ghost_pos[0]) + abs(pos[1] - ghost_pos[1])
                for ghost_pos in ghost_positions
            )
            
            # Consider position dangerous if too close to any ghost
            if min_ghost_distance < min_safe_distance:
                dangerous_positions += 1
        
        # Path is safe if less than threshold percentage of positions are dangerous
        danger_ratio = dangerous_positions / total_positions if total_positions > 0 else 0
        is_safe = danger_ratio < danger_threshold
        
        if not is_safe:
            print(f" Path safety validation failed: {dangerous_positions}/{total_positions} dangerous positions ({danger_ratio:.2%})")
        
        return is_safe

    def _validate_and_smooth_path(self, path):
        """Validate path and smooth it to ensure Pacman can follow it"""
        if not path or len(path) < 2:
            return path
        
        validated_path = [path[0]]  # Always include start
        
        for i in range(1, len(path)):
            current_pos = validated_path[-1]
            next_pos = path[i]
            
            # Check if we can move directly from current to next
            if self._can_move_directly(current_pos, next_pos):
                validated_path.append(next_pos)
            else:
                # If not, try to find intermediate steps
                intermediate_path = self._find_intermediate_path(current_pos, next_pos)
                if intermediate_path:
                    validated_path.extend(intermediate_path[1:])  # Skip first position (already added)
                else:
                    # If can't find intermediate path, skip this position
                    continue
        
        return validated_path

    def _can_move_directly(self, pos1, pos2):
        """Check if Pacman can move directly from pos1 to pos2"""
        row1, col1 = pos1
        row2, col2 = pos2
        
        # Must be adjacent (Manhattan distance = 1)
        if abs(row1 - row2) + abs(col1 - col2) != 1:
            return False
        
        # Must not be a wall
        return not self.is_wall(col2, row2)

    def _find_intermediate_path(self, start_pos, end_pos):
        """Find a short path between two positions using BFS"""
        from collections import deque
        
        start_row, start_col = start_pos
        end_row, end_col = end_pos
        
        # If too far apart, don't bother
        if abs(start_row - end_row) + abs(start_col - end_col) > 3:
            return None
        
        queue = deque([(start_pos, [start_pos])])
        visited = set([start_pos])
        
        while queue:
            current_pos, path = queue.popleft()
            current_row, current_col = current_pos
            
            if current_pos == end_pos:
                return path
            
            # Try all 4 directions
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                next_row = current_row + dr
                next_col = current_col + dc
                next_pos = (next_row, next_col)
                
                if (next_pos not in visited and 
                    not self.is_wall(next_col, next_row) and
                    0 <= next_row < self.maze_gen.height and
                    0 <= next_col < self.maze_gen.width):
                    
                    visited.add(next_pos)
                    new_path = path + [next_pos]
                    queue.append((next_pos, new_path))
                    
                    # Limit search depth
                    if len(new_path) > 5:
                        continue
        
        return None

    def move_pacman_auto(self):
        """GOAL-FIRST auto movement với ADVANCED GHOST AVOIDANCE - cải thiện thuật toán né ma"""

        # Initialize auto mode variables
        if not hasattr(self, 'current_goal'):
            self.current_goal = None
        if not hasattr(self, 'goal_locked'):
            self.goal_locked = False
        if not hasattr(self, 'goal_cooldown'):
            self.goal_cooldown = 0
        if not hasattr(self, 'ghost_avoidance_active'):
            self.ghost_avoidance_active = False
        if not hasattr(self, 'last_ghost_check'):
            self.last_ghost_check = 0
        if not hasattr(self, 'last_emergency_turn'):
            self.last_emergency_turn = 0
        if not hasattr(self, 'turn_cooldown'):
            self.turn_cooldown = 0
        if not hasattr(self, 'continuous_avoidance_count'):
            self.continuous_avoidance_count = 0

        # Decrease cooldown
        if self.goal_cooldown > 0:
            self.goal_cooldown -= 1

        current_time = pygame.time.get_ticks()

        # SIÊU NHANH: Kiểm tra ghosts mỗi 30ms (33 lần/giây) để phản ứng cực nhanh
        if current_time - self.last_ghost_check > 30:
            self.last_ghost_check = current_time

            # Kiểm tra ghosts trong bán kính 3 ô (giảm từ 7)
            nearby_ghosts = self._check_ghosts_nearby(avoidance_radius=3)

            if nearby_ghosts:
                min_distance = min(d for _, d in nearby_ghosts)
                print(f"🚨 Phát hiện {len(nearby_ghosts)} ghost(s)! Khoảng cách gần nhất: {min_distance}")
                
                # PRIORITY 1: Emergency avoidance nếu ghost rất gần
                if min_distance <= 3:
                    self.continuous_avoidance_count += 1
                    
                    # Xử lý khẩn cấp: quay đầu hoặc rẽ ngã gần nhất
                    if self._emergency_ghost_avoidance(nearby_ghosts):
                        print(f"✅ Emergency avoidance successful! (Count: {self.continuous_avoidance_count})")
                        return  # Đã xử lý thành công, thoát ngay
                    else:
                        print("❌ Emergency avoidance failed, activating complex avoidance...")
                        
                # PRIORITY 2: Activate complex avoidance cho ghost ở khoảng cách trung bình
                if min_distance <= 3 or self.ghost_avoidance_active:  # giảm từ 6 xuống 3
                    if not self.ghost_avoidance_active:
                        self.ghost_avoidance_active = True
                        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                          if not g.get('scared', False)]

                        print("🛡️ Kích hoạt chế độ né tránh ghosts phức tạp!")
                        self._find_fallback_target(pacman_pos, ghost_positions)
                    
                    # Kiểm tra xem có cần update fallback target không
                    elif self.continuous_avoidance_count % 3 == 0:  # Mỗi 3 lần kiểm tra
                        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                          if not g.get('scared', False)]
                        print("🔄 Updating fallback target...")
                        self._find_fallback_target(pacman_pos, ghost_positions)
            else:
                # Không có ghost ở gần, reset counter và tắt chế độ avoidance
                if self.ghost_avoidance_active or self.continuous_avoidance_count > 0:
                    self.ghost_avoidance_active = False
                    self.continuous_avoidance_count = 0
                    self.auto_path = []  # Xóa đường đi avoidance cũ
                    print("🟢 Không còn ghost ở gần, tiếp tục đi đến goal")

        # Nếu đang trong chế độ ghost avoidance phức tạp, kiểm tra trạng thái
        if self.ghost_avoidance_active:
            nearby_ghosts = self._check_ghosts_nearby(avoidance_radius=3)
            if not nearby_ghosts:
                # Đã an toàn, quay lại goal chính
                self.ghost_avoidance_active = False
                self.goal_locked = False  # Cho phép tìm goal mới
                self.auto_path = []  # Xóa đường đi avoidance cũ
                self.continuous_avoidance_count = 0
                print("🛡️ Đã né tránh thành công, quay lại goal chính")

        # Kiểm tra xem đã đạt đến target an toàn chưa
        if self.ghost_avoidance_active and self.auto_target:
            pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
            if pacman_pos == self.auto_target:
                # Đã đạt đến vị trí an toàn
                self.ghost_avoidance_active = False
                self.goal_locked = False
                self.auto_path = []  # Xóa đường đi avoidance cũ
                self.continuous_avoidance_count = 0
                print("🎯 Đã đạt đến vị trí an toàn, tìm đường mới")

        # CRITICAL: Only find new goal if NO current goal OR goal reached/collected
        if not self.current_goal or not self.goal_locked:
            if self.goal_cooldown <= 0:
                self.find_goal_first()
                if self.current_goal:
                    self.goal_locked = True

        # GOAL-ONLY movement - không bị phân tâm bởi dots
        if self.current_goal and not self.ghost_avoidance_active:
            self.move_goal_focused()
        elif self.ghost_avoidance_active:
            # Nếu đang trong chế độ avoidance, ưu tiên auto_path
            if hasattr(self, 'auto_path') and self.auto_path and len(self.auto_path) > 1:
                pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
                current_pos = (pacman_row, pacman_col)
                
                try:
                    current_index = self.auto_path.index(current_pos)
                    if current_index + 1 < len(self.auto_path):
                        next_pos = self.auto_path[current_index + 1]
                        direction = [next_pos[1] - pacman_col, next_pos[0] - pacman_row]
                        self.pacman_next_direction = direction
                        print(f"🛡️ Following avoidance path: {direction}")
                        return
                except ValueError:
                    # Không tìm thấy vị trí hiện tại trong path, tính toán lại
                    print("⚠️ Current position not in avoidance path, recalculating...")
                    pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                    ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                      if not g.get('scared', False)]
                    self._find_fallback_target(pacman_pos, ghost_positions)

    def find_goal_first(self):
        """GOAL-ONLY selection - Chỉ đi đến đích, không ăn dots/pellets"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])

        # STRATEGY: Chỉ tập trung vào goal, không ăn dots/pellets
        # Ưu tiên: Exit gate ONLY

        # 1. EXIT GATE ONLY - Chỉ đi đến exit gate
        if hasattr(self, 'exit_gate'):
            self.current_goal = self.exit_gate
            print(f"GOAL-ONLY: Exit gate at {self.exit_gate}")
            return

        # 2. Nếu không có exit gate, tạo goal cố định ở góc đối diện
        if not hasattr(self, 'exit_gate'):
            # Tạo exit gate ở góc dưới phải
            center_row = self.maze_gen.height // 2
            center_col = self.maze_gen.width // 2

            # Tìm vị trí hợp lệ ở góc dưới phải
            for dr in range(-5, 6):
                for dc in range(-5, 6):
                    test_row = self.maze_gen.height - 1 + dr
                    test_col = self.maze_gen.width - 1 + dc

                    if (0 <= test_row < self.maze_gen.height and
                        0 <= test_col < self.maze_gen.width and
                        self.maze[test_row, test_col] == 0):  # Valid path
                        self.exit_gate = (test_row, test_col)
                        self.current_goal = self.exit_gate
                        print(f" GOAL-ONLY: Created exit gate at {self.exit_gate}")
                        return

        # 3. Fallback: goal ở center nếu không tìm được gì
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        if self.is_valid_position(center_col, center_row):
            self.current_goal = (center_row, center_col)
            print(f" GOAL-ONLY: Center goal at {self.current_goal}")
        else:
            self.current_goal = None
            print(" GOAL-ONLY: No valid goal found")

    def move_goal_focused(self):
        """GOAL-FOCUSED movement - Chỉ tập trung vào goal, không ăn dots ngẫu nhiên"""
        if not self.current_goal:
            return

        goal_row, goal_col = self.current_goal
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))

        # Check if goal reached
        distance_to_goal = abs(pacman_row - goal_row) + abs(pacman_col - goal_col)
        if distance_to_goal < 1:
            print(f" GOAL REACHED! Distance: {distance_to_goal}")
            self.goal_locked = False
            self.current_goal = None
            self.goal_cooldown = 10  # Short cooldown before next goal
            return

        # Tính toán đường đi ngắn nhất đến goal (tránh bom)
        self.calculate_shortest_path_to_goal()

        # Ưu tiên sử dụng shortest_path nếu có
        if hasattr(self, 'shortest_path') and self.shortest_path and len(self.shortest_path) > 1:
            # Tìm vị trí hiện tại trong shortest_path
            current_pos = (pacman_row, pacman_col)
            try:
                current_index = self.shortest_path.index(current_pos)
                if current_index + 1 < len(self.shortest_path):
                    next_pos = self.shortest_path[current_index + 1]
                    direction = [next_pos[1] - pacman_col, next_pos[0] - pacman_row]
                    self.pacman_next_direction = direction
                    print(f"🔍 Following shortest path: {direction}")
                    return
            except ValueError:
                # Không tìm thấy vị trí hiện tại trong path, tính toán lại
                print("⚠️ Current position not in shortest path, recalculating...")
                pass

        # Fallback: sử dụng auto_path nếu có (đã tính với ghost avoidance)
        if hasattr(self, 'auto_path') and self.auto_path and len(self.auto_path) > 1:
            # Tìm vị trí hiện tại trong auto_path
            current_pos = (pacman_row, pacman_col)
            try:
                current_index = self.auto_path.index(current_pos)
                if current_index + 1 < len(self.auto_path):
                    next_pos = self.auto_path[current_index + 1]
                    direction = [next_pos[1] - pacman_col, next_pos[0] - pacman_row]
                    self.pacman_next_direction = direction
                    return
            except ValueError:
                # Không tìm thấy vị trí hiện tại trong path, tính toán lại
                pass

        # Nếu không có path hoặc không tìm thấy vị trí hiện tại, sử dụng pathfinding thông thường
        direction = self.find_goal_path((pacman_col, pacman_row), (goal_col, goal_row))

        if direction:
            self.pacman_next_direction = direction
        else:
            # Emergency: move toward goal directly
            self.emergency_goal_move(pacman_col, pacman_row, goal_col, goal_row)

    def find_goal_path(self, start_pos, goal_pos):
        """GOAL-ONLY pathfinding - tối ưu cho việc đi đến goal"""
        import heapq

        start = (int(start_pos[0]), int(start_pos[1]))
        goal = goal_pos

        if start == goal:
            return None

        def heuristic(pos):
            """Manhattan distance - khuyến khích đi thẳng đến goal"""
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])

        # A* algorithm với goal priority
        heap = [(heuristic(start), 0, start, [])]
        visited = set()
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while heap:
            f_score, g_score, (x, y), path = heapq.heappop(heap)

            if (x, y) in visited:
                continue
            visited.add((x, y))

            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                if (nx, ny) == goal:
                    # GOAL FOUND - return first step
                    first_step = path[0] if path else (dx, dy)
                    return [first_step[0], first_step[1]]

                # Check if position has bomb
                bomb_grid = self.get_bomb_grid_positions()
                if (nx, ny) not in visited and self.is_valid_position(nx, ny) and (ny, nx) not in bomb_grid:
                    new_g_score = g_score + 1
                    new_f_score = new_g_score + heuristic((nx, ny))
                    new_path = path + [(dx, dy)]

                    heapq.heappush(heap, (new_f_score, new_g_score, (nx, ny), new_path))

        return None

    def emergency_goal_move(self, px, py, gx, gy):
        """Emergency movement trực tiếp đến goal"""
        dx = 1 if gx > px else (-1 if gx < px else 0)
        dy = 1 if gy > py else (-1 if gy < py else 0)

        # Get bomb positions
        bomb_grid = self.get_bomb_grid_positions()

        # Thử hướng chính trước
        if dx != 0 and self.is_valid_position(px + dx, py) and (py, px + dx) not in bomb_grid:
            self.pacman_next_direction = [dx, 0]
            return
        elif dy != 0 and self.is_valid_position(px, py + dy) and (py + dy, px) not in bomb_grid:
            self.pacman_next_direction = [0, dy]
            return

        # Thử hướng phụ
        if dy != 0 and self.is_valid_position(px + dy, py) and (py, px + dy) not in bomb_grid:
            self.pacman_next_direction = [dy, 0]
            return
        elif dx != 0 and self.is_valid_position(px, py + dx) and (py + dx, px) not in bomb_grid:
            self.pacman_next_direction = [0, dx]
            return

        # Last resort: bất kỳ hướng nào
        for test_dir in [[1,0], [-1,0], [0,1], [0,-1]]:
            if self.is_valid_position(px + test_dir[0], py + test_dir[1]) and (py + test_dir[1], px + test_dir[0]) not in bomb_grid:
                self.pacman_next_direction = test_dir
                return

    def find_simple_goal(self):
        """Find closest goal and stick to it - CHỈ TÌM EXIT GATE"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])

        #  DISABLED: Không tìm power pellets và dots nữa
        # # Find closest target
        # best_target = None
        # best_distance = float('inf')
        #
        # # Check power pellets first
        # for pellet in self.power_pellets:
        #     pellet_col = int((pellet[0] - self.cell_size // 2) / self.cell_size)
        #     pellet_row = int((pellet[1] - self.cell_size // 2) / self.cell_size)
        #     distance = abs(pacman_row - pellet_row) + abs(pacman_col - pellet_col)
        #
        #     if distance < best_distance:
        #         best_distance = distance
        #         best_target = (pellet_row, pellet_col)
        #
        # # Then check dots if no power pellets
        # if not best_target and self.dots:
        #     for dot in self.dots:
        #         dot_col = int((dot[0] - self.cell_size // 2) / self.cell_size)
        #         dot_row = int((dot[1] - self.cell_size // 2) / self.cell_size)
        #         distance = abs(pacman_row - dot_row) + abs(pacman_col - dot_col)
        #
        #     if distance < best_distance:
        #         best_distance = distance
        #         best_target = (dot_row, dot_col)

        #  CHỈ TÌM EXIT GATE
        if hasattr(self, 'exit_gate') and self.exit_gate:
            self.current_goal = self.exit_gate
            print(f" LOCKED Goal: {self.exit_gate} (EXIT GATE ONLY)")
        else:
            self.current_goal = None
            print(" No exit gate available")

    def find_path_to_goal(self, start_pos, goal_pos):
        """Tìm đường đi tối ưu đến goal với ghost avoidance thông minh"""
        from collections import deque
        
        start = (int(start_pos[0]), int(start_pos[1]))
        goal = goal_pos
        
        if start == goal:
            return None
        
        # Lấy vị trí ma và phân loại - chỉ những ma có line of sight
        dangerous_ghosts = []
        for ghost in self.ghosts:
            if not ghost.get('scared', False):  # Chỉ né ma không sợ
                ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
                ghost_pos = (ghost_row, ghost_col)
                
                # Chỉ coi là nguy hiểm nếu có line of sight và ở gần
                distance = abs(start[0] - ghost_col) + abs(start[1] - ghost_row)
                if distance <= 5 and self._has_line_of_sight((start[1], start[0]), ghost_pos):  # start[1], start[0] vì start là (col, row)
                    dangerous_ghosts.append(ghost_pos)
        
        # BFS với ghost avoidance cho ma nguy hiểm
        queue = deque([(start, [])])
        visited = {start}
        
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        
        while queue:
            (x, y), path = queue.popleft()
            
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                
                if (nx, ny) == goal:
                    # Tìm thấy goal, trả về bước đầu tiên
                    first_step = path[0] if path else (dx, dy)
                    return [first_step[0], first_step[1]]
                
                if (nx, ny) not in visited and self.is_valid_position(nx, ny):
                    # Kiểm tra an toàn từ ghosts có line of sight
                    is_safe = True
                    for ghost_pos in dangerous_ghosts:
                        # Kiểm tra line of sight từ next_pos đến ghost
                        next_pos = (ny, nx)  # Convert to (row, col) for safety check
                        if self._has_line_of_sight(next_pos, ghost_pos):
                            ghost_distance = abs(nx - ghost_pos[1]) + abs(ny - ghost_pos[0])  # ghost_pos is (row, col)
                            if ghost_distance <= 2:  # Quá gần ghost có thể nhìn thấy
                                is_safe = False
                                break
                    
                    if is_safe:
                        visited.add((nx, ny))
                        new_path = path + [(dx, dy)]
                        queue.append(((nx, ny), new_path))
        
        # Nếu không tìm thấy đường an toàn, thử đường trực tiếp (emergency)
        print(" No safe path found, trying direct path")
        
        # Emergency: đi trực tiếp bất chấp ma
        dx = 1 if goal[0] > start[0] else (-1 if goal[0] < start[0] else 0)
        dy = 1 if goal[1] > start[1] else (-1 if goal[1] < start[1] else 0)
        
        # Ưu tiên x trước
        if dx != 0 and self.is_valid_position(start[0] + dx, start[1]):
            return [dx, 0]
        elif dy != 0 and self.is_valid_position(start[0], start[1] + dy):
            return [0, dy]
        
        return None  # Không thể di chuyển

    def move_directly_toward_goal(self):
        """Move toward goal using BFS pathfinding"""
        if not self.current_goal:
            return
            
        goal_row, goal_col = self.current_goal
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        
        print(f"📍 Pacman at ({pacman_row}, {pacman_col}) → Goal at {self.current_goal}")
        
        # Check if goal reached
        if abs(pacman_row - goal_row) < 1 and abs(pacman_col - goal_col) < 1:
            print(f" Goal reached! Unlocking for next goal...")
            self.goal_locked = False
            self.current_goal = None
            self.goal_cooldown = 10  # Short cooldown before next goal
            return
            
        # Use BFS to find path
        direction = self.find_path_to_goal((pacman_col, pacman_row), (goal_col, goal_row))
        
        if direction:
            print(f" BFS Found path! Next move: {direction}")
            self.pacman_next_direction = direction
        else:
            print(f" No path found to goal {self.current_goal}")
            # If no path, try random valid move
            possible_dirs = [[1,0], [-1,0], [0,1], [0,-1]]
            for test_dir in possible_dirs:
                test_col = pacman_col + test_dir[0]
                test_row = pacman_row + test_dir[1]
                if self.is_valid_position(test_col, test_row):
                    self.pacman_next_direction = test_dir
                    print(f" Random move: {test_dir}")
                    break

    def find_optimal_goal(self):
        """Find the best goal - CHỈ TÌM EXIT GATE"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)

        #  DISABLED: Không kiểm tra dots/pellets nữa
        # # Check if current goal is still valid before switching
        # if self.current_goal:
        #     goal_row, goal_col = self.current_goal
        #     goal_screen_pos = (goal_col * self.cell_size + self.cell_size // 2,
        #                       goal_row * self.cell_size + self.cell_size // 2)
        #
        #     # If current goal still exists, keep it
        #     if (goal_screen_pos in self.dots or goal_screen_pos in self.power_pellets):
        #         print(f" Keeping current goal at {self.current_goal}")
        #         return

        #  DISABLED: Không tìm power pellets nữa
        # # Priority 1: Power pellets when ghosts are nearby or when found
        # if self.power_pellets:
        #     # Find closest power pellet
        #     best_pellet = None
        #     best_distance = float('inf')
        #
        #     for pellet in self.power_pellets:
        #         pellet_col = int((pellet[0] - self.cell_size // 2) / self.cell_size)
        #         pellet_row = int((pellet[1] - self.cell_size // 2) / self.cell_size)
        #         distance = abs(pacman_row - pellet_row) + abs(pacman_col - pellet_col)
        #
        #         if distance < best_distance:
        #             best_distance = distance
        #             best_pellet = (pellet_row, pellet_col)
        #
        #     if best_pellet:
        #         self.current_goal = best_pellet
        #         print(f" NEW Goal: Power pellet at {best_pellet}")
        #         return

        #  DISABLED: Không tìm dots nữa
        # # Priority 2: Nearest dots (find closest one and stick to it)
        # if self.dots:
        #     best_dot = None
        #     best_distance = float('inf')
        #
        #     for dot in self.dots:
        #         dot_col = int((dot[0] - self.cell_size // 2) / self.cell_size)
        #         dot_row = int((dot[1] - self.cell_size // 2) / self.cell_size)
        #         distance = abs(pacman_row - dot_row) + abs(pacman_col - dot_col)
        #
        #         if distance < best_distance:
        #             best_distance = distance
        #             best_dot = (dot_row, dot_col)
        #
        #     if best_dot:
        #         self.current_goal = best_dot
        #         print(f" NEW Goal: Dot at {best_dot}")
        #         return

        #  CHỈ TÌM EXIT GATE
        if hasattr(self, 'exit_gate') and self.exit_gate:
            self.current_goal = self.exit_gate
            print(f" GOAL: Exit gate at {self.exit_gate}")
        else:
            self.current_goal = None
            print(" No exit gate found!")

    def calculate_path_to_goal(self):
        """Calculate shortest path to current goal"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)
        
        path, distance = self.dijkstra.shortest_path(pacman_pos, self.current_goal)
        if path:
            self.path_to_goal = path
            print(f"📍 Path calculated: {len(path)} steps to goal {self.current_goal}")
        else:
            print(" No path to goal found")
            self.path_to_goal = []
            # If no path found, invalidate current goal
            self.current_goal = None

    def find_safe_detour(self):
        """Find safe route when ghost is near"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        
        # Get ghost positions
        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                          if not g.get('scared', False)]
        
        # Find safe directions (away from ghosts)
        safe_directions = []
        for dx, dy in [[1, 0], [-1, 0], [0, 1], [0, -1]]:
            new_col = pacman_col + dx
            new_row = pacman_row + dy
            
            if not self.is_wall(new_col, new_row):
                # Check if this direction is safe from ghosts
                min_ghost_distance = min([
                    abs(new_row - gr) + abs(new_col - gc)
                    for gr, gc in ghost_positions
                ]) if ghost_positions else 10
                
                if min_ghost_distance >= 2:  # Safe distance
                    # Calculate if this direction leads closer to goal
                    if self.current_goal:
                        goal_distance = abs(new_row - self.current_goal[0]) + abs(new_col - self.current_goal[1])
                        safe_directions.append((dx, dy, goal_distance))
        
        # Choose direction that's safe and closest to goal
        if safe_directions:
            safe_directions.sort(key=lambda x: x[2])  # Sort by distance to goal
            chosen_direction = safe_directions[0][:2]
            self.pacman_next_direction = [chosen_direction[0], chosen_direction[1]]
            
            # Recalculate path after detour
            self.path_to_goal = []
        else:
            print("No safe direction found!")

    def move_toward_goal(self):
        """Move toward current goal using calculated path"""
        if not self.path_to_goal or len(self.path_to_goal) <= 1:
            print("📍 No path available - staying put")
            return
        
        # Clean up path - remove current position if we're already there
        current_col, current_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        
        # Remove waypoints that we've already reached
        while (self.path_to_goal and 
               len(self.path_to_goal) > 1 and  # Keep at least one waypoint (the goal)
               abs(current_row - self.path_to_goal[0][0]) < 0.8 and 
               abs(current_col - self.path_to_goal[0][1]) < 0.8):
            self.path_to_goal.pop(0)
            print(f"Reached waypoint, remaining path: {len(self.path_to_goal)} steps")
        
        if not self.path_to_goal:
            print("Goal reached!")
            return
            
        # Get next target position from path
        next_row, next_col = self.path_to_goal[0]  # Always use first position in path
        
        print(f"Current: ({current_row}, {current_col}) → Target: ({next_row}, {next_col})")
        
        # Calculate direction to move
        dx = next_col - current_col  
        dy = next_row - current_row  
        
        # Simple direction logic - move one step at a time
        direction = [0, 0]
        if dy > 0:      # Need to go down
            direction = [0, 1]
        elif dy < 0:    # Need to go up  
            direction = [0, -1]
        elif dx > 0:    # Need to go right
            direction = [1, 0]
        elif dx < 0:    # Need to go left
            direction = [-1, 0]
        
        if direction != [0, 0]:
            self.pacman_next_direction = direction
            print(f"Moving {['left', 'right'][direction[0]] if direction[0] != 0 else ['up', 'down'][direction[1]]}")
        else:
            print(f"Already at target position")
            # If already at target, remove this waypoint
            if self.path_to_goal:
                self.path_to_goal.pop(0)

    def has_reached_current_goal(self):
        """Check if current goal has been reached - CHỈ KIỂM TRA ĐẾN GOAL"""
        if not self.current_goal:
            return True
        
        pacman_col, pacman_row = self.pacman_pos[0], self.pacman_pos[1]
        goal_row, goal_col = self.current_goal
        
        # Check if reached
        if abs(pacman_col - goal_col) < 1 and abs(pacman_row - goal_row) < 1:
            return True
        
        #  DISABLED: Không kiểm tra dots/pellets nữa
        # # Check if goal is still valid (dot/pellet still exists)
        # goal_screen_pos = (goal_col * self.cell_size + self.cell_size // 2,
        #                   goal_row * self.cell_size + self.cell_size // 2)
        #
        # # Check if it's still in dots or power_pellets
        # return (goal_screen_pos not in self.dots and 
        #         goal_screen_pos not in self.power_pellets)
        
        # Goal luôn valid vì chỉ đi đến exit gate
        return False

    def has_reached_target(self):
        """Check if Pacman has reached the current auto target"""
        if not self.auto_target:
            return True

        pacman_col, pacman_row = self.pacman_pos[0], self.pacman_pos[1]
        target_row, target_col = self.auto_target

        # Note: auto_target is in (row, col) format, pacman_pos is in [col, row] format
        return abs(pacman_col - target_col) < 1 and abs(pacman_row - target_row) < 1

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
        """Check collisions with ghosts ONLY - không ăn dots/pellets"""
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

                # Set power mode for 10 seconds
                self.power_mode_end_time = pygame.time.get_ticks() + 5000  # 10 seconds
                print("Power mode activated! Ghosts can be eaten for 10 seconds")

                # Make all ghosts frightened for 10 seconds
                for ghost in self.ghosts:
                    ghost['scared'] = True
                    ghost['scared_timer'] = 600  # 10 seconds at 60 FPS

        # Check bombs collision - lose life if hit
        for bomb in self.bombs[:]:
            distance = math.hypot(pacman_center[0] - bomb[0], pacman_center[1] - bomb[1])
            if distance < 12:  # Bomb collision distance
                print("Hit a bomb! Lost a life!")
                self.lives -= 1
                if self.lives <= 0:
                    self.game_state = "game_over"
                else:
                    self.reset_positions()
                break  # Only lose one life per collision check

        # CHỈ KIỂM TRA: Ghosts collision
        for ghost in self.ghosts:
            ghost_center = (ghost['pos'][0] * self.cell_size + self.cell_size // 2,
                          ghost['pos'][1] * self.cell_size + self.cell_size // 2)
            distance = math.hypot(pacman_center[0] - ghost_center[0],
                                pacman_center[1] - ghost_center[1])
            if distance < 15:
                if ghost.get('scared', False):
                    # Eat scared ghost for points
                    self.score += 200
                    print(f" Ate {ghost['name']} ghost! +200 points")
                    # Reset ghost position
                    ghost['pos'] = [float(self.start[1]), float(self.start[0])]
                    ghost['scared'] = False
                    ghost['scared_timer'] = 0
                else:
                    # Normal ghost collision - lose life but keep score
                    print(f"👻 Pacman touched a ghost! Lost a life. Lives remaining: {self.lives - 1}")
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_state = "game_over"
                        print("💀 Game Over! No lives remaining.")
                    else:
                        # Reset positions but keep score and game state
                        self.reset_positions_after_death()

        # Check exit gate collision (WIN CONDITION)
        if hasattr(self, 'exit_gate'):
            gate_row, gate_col = self.exit_gate
            gate_center = ((gate_col + 0.5) * self.cell_size, (gate_row + 0.5) * self.cell_size)
            gate_distance = math.hypot(pacman_center[0] - gate_center[0], 
                                     pacman_center[1] - gate_center[1])
            if gate_distance < 20:  # Slightly larger than ghost collision
                self.game_state = "level_complete"
                self.score += 1000  # Bonus for completing level

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
        
        # Place ghosts at valid center position and let them spread out
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)

        # If can't find valid ghost position, use Pacman's position as fallback
        if not ghost_start_pos:
            print("⚠️  Could not find valid ghost start position, using Pacman position")
            ghost_start_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))

        for i, ghost in enumerate(self.ghosts[:4]):  # Ensure only 4 ghosts
            # All ghosts start at the same valid center position
            ghost['pos'] = [float(ghost_start_pos[1]), float(ghost_start_pos[0])]  # [col, row] format

            # Reset ghost state
            ghost['direction'] = [0, 0]
            ghost['mode'] = 'random'  # Start in random mode to spread out
            ghost['target'] = None
            ghost['last_direction_change'] = 0
            ghost['position_history'] = []
            ghost['stuck_counter'] = 0
            ghost['last_position'] = None
            ghost['random_timer'] = 0
            ghost['spread_timer'] = 0

    def reset_positions_after_death(self):
        """Reset Pacman and ghosts positions after death - keeps score and game state intact"""
        print("🔄 Resetting positions after death...")

        # Set Pacman to maze start position (guaranteed black cell)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]

        # Reset auto mode variables but keep auto mode enabled if it was on
        if self.auto_mode:
            self.auto_path = []
            self.auto_target = None
            self.current_goal = None
            self.goal_locked = False
            self.goal_cooldown = 0
            self.ghost_avoidance_active = False

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

        # Place ghosts at valid center position and let them spread out
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)

        # If can't find valid ghost position, use Pacman's position as fallback
        if not ghost_start_pos:
            print("⚠️  Could not find valid ghost start position, using Pacman position")
            ghost_start_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))

        for i, ghost in enumerate(self.ghosts[:4]):  # Ensure only 4 ghosts
            # All ghosts start at the same valid center position
            ghost['pos'] = [float(ghost_start_pos[1]), float(ghost_start_pos[0])]  # [col, row] format

            # Reset ghost state
            ghost['direction'] = [0, 0]
            ghost['mode'] = 'random'  # Start in random mode to spread out
            ghost['target'] = None
            ghost['last_direction_change'] = 0
            ghost['position_history'] = []
            ghost['stuck_counter'] = 0
            ghost['last_position'] = None
            ghost['random_timer'] = 0
            ghost['spread_timer'] = 0
            # Keep scared state intact if ghost was scared
            if not ghost.get('scared', False):
                ghost['scared_timer'] = 0

        print(f"✅ Positions reset - Pacman at start, ghosts repositioned. Score: {self.score}, Lives: {self.lives}")

    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                print(f"Key pressed: {pygame.key.name(event.key)}")
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.game_state = "paused" if self.game_state == "playing" else "playing"
                elif event.key == pygame.K_a:
                    self.toggle_auto_mode()
                elif event.key == pygame.K_h:
                    self.show_shortest_path = not self.show_shortest_path
                    if self.show_shortest_path:
                        self.calculate_shortest_path_to_goal()
                        print("🔍 Shortest path visualization: ON")
                    else:
                        self.shortest_path = []
                        print("🔍 Shortest path visualization: OFF")
                elif event.key == pygame.K_e:
                    self.set_escape_target()
                elif event.key == pygame.K_r:
                    self.create_new_game()
                elif event.key == pygame.K_n and self.game_state == "level_complete":
                    self.next_level()
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
        print("🔄 RESTARTING GAME - Resetting all states...")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None

        # Remove user auto flag to ensure manual control after restart
        if hasattr(self, '_user_enabled_auto'):
            delattr(self, '_user_enabled_auto')

        # Reset Pacman properties
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = 2  
        self.pacman_animation = 1
        self.pacman_mouth_open = True

        # Reset shortest path visualization
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0

        # Reset ghost avoidance variables
        self.ghost_avoidance_active = False
        self.last_ghost_check = 0
        self.last_emergency_turn = 0
        self.turn_cooldown = 0
        self.current_goal = None
        self.goal_locked = False
        self.goal_cooldown = 0

        # Reset game timing variables
        self.last_update = pygame.time.get_ticks()
        self.animation_timer = 0
        self.auto_update_timer = 0

        print("📐 Generating new level...")
        self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Failed to generate valid maze, trying again...")
            # Try one more time
            self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Still failed to generate maze, using fallback")
            # Fallback: create a simple maze
            import numpy as np
            self.maze = np.zeros((self.maze_gen.height, self.maze_gen.width), dtype=int)
            self.start = (1, 1)
            self.goal = (self.maze_gen.height - 2, self.maze_gen.width - 2)

        print("Placing dots and pellets...")
        self.place_dots_and_pellets()

        print("Creating/resetting ghosts...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("Resetting positions...")
        self.reset_positions()

        print("✅ Game restarted successfully - Auto mode: OFF, Manual control enabled!")

    def next_level(self):
        """Advance to the next level"""
        self.level += 1
        self.game_state = "playing"
        
        # Reset shortest path visualization
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0
        
        # Reset ghost avoidance variables
        self.ghost_avoidance_active = False
        self.last_ghost_check = 0
        self.last_emergency_turn = 0
        self.turn_cooldown = 0
        self.current_goal = None
        self.goal_locked = False
        self.goal_cooldown = 0
        self.auto_path = []
        self.auto_target = None
        
        self.generate_level()
        self.place_dots_and_pellets()
        self.reset_positions()

    def create_new_game(self):
        """Create a new game with a randomly generated map"""
        print("Creating a new game with a random map...")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None

        # Remove user auto flag to ensure manual control after creating new game
        if hasattr(self, '_user_enabled_auto'):
            delattr(self, '_user_enabled_auto')

        # Reset shortest path visualization
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0

        # Reset ghost avoidance variables
        self.ghost_avoidance_active = False
        self.last_ghost_check = 0
        self.last_emergency_turn = 0
        self.turn_cooldown = 0
        self.current_goal = None
        self.goal_locked = False
        self.goal_cooldown = 0

        print("📐 Generating new random level...")
        self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Failed to generate valid maze, trying again...")
            # Try one more time
            self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Still failed to generate maze, using fallback")
            # Fallback: create a simple maze
            import numpy as np
            self.maze = np.zeros((self.maze_gen.height, self.maze_gen.width), dtype=int)
            self.start = (1, 1)
            self.goal = (self.maze_gen.height - 2, self.maze_gen.width - 2)

        print("Placing dots and pellets...")
        self.place_dots_and_pellets()

        print("👻 Creating/resetting ghosts...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("📍 Resetting positions...")
        self.reset_positions()

        print("New game created successfully!")

    def update(self):
        """Update game state"""
        current_time = pygame.time.get_ticks()

        # ENSURE AUTO MODE STAYS OFF UNLESS EXPLICITLY ENABLED BY USER
        if self.auto_mode and not hasattr(self, '_user_enabled_auto'):
            print("WARNING: Auto mode was unexpectedly enabled, resetting to manual")
            self.auto_mode = False
            self.auto_path = []
            self.auto_target = None

        if self.game_state == "playing":
            # Move Pacman based on mode
            if self.auto_mode:
                self.move_pacman_auto()  # Calculate AI direction
                self.move_pacman()       # Execute the movement
            else:
                self.move_pacman()
                
            self.move_ghosts()
            self.check_collisions()

            # Update ghost scared timers
            for ghost in self.ghosts:
                if ghost.get('scared', False):
                    ghost['scared_timer'] -= 1
                    if ghost['scared_timer'] <= 0:
                        ghost['scared'] = False
                        ghost['scared_timer'] = 0

            # Update shortest path visualization (recalculate every 30 frames)
            current_time = pygame.time.get_ticks()
            if self.show_shortest_path and current_time - self.last_path_calculation > 500:  # 500ms
                self.calculate_shortest_path_to_goal()
                self.last_path_calculation = current_time

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
        self.draw_bombs()
        self.draw_exit_gate()  # Draw exit gate
        self.draw_shortest_path()  # Draw shortest path to goal
        # self.draw_auto_path()  #  REMOVED: Xóa tính năng show path
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_ui()
        pygame.display.flip()

    def toggle_auto_mode(self):
        """Toggle between manual and automatic Pacman control"""
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            print("Auto mode ON - Pacman will play automatically!")
            self._user_enabled_auto = True  # Mark that user explicitly enabled auto
            self.find_auto_target()
        else:
            print("Manual mode ON - You control Pacman!")
            if hasattr(self, '_user_enabled_auto'):
                delattr(self, '_user_enabled_auto')  # Remove flag when disabling
            self.auto_path = []
            self.auto_target = None
            self.pacman_direction = [0, 0]
            self.pacman_next_direction = [0, 0]

    def run(self):
        """Main game loop"""
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(60)
        except KeyboardInterrupt:
            print("\nGame interrupted by user")
        except Exception as e:
            print(f" Error during game execution: {e}")
        finally:
            # Proper cleanup
            print("🧹 Cleaning up resources...")
            try:
                pygame.mixer.quit()  # Safe to call even if mixer not initialized
            except:
                pass
            pygame.quit()
            print("Game exited successfully")
            sys.exit(0)

    def get_bomb_grid_positions(self):
        """Convert bomb pixel positions to grid coordinates"""
        bomb_grid = set()
        for bomb in self.bombs:
            bomb_x, bomb_y = bomb
            grid_col = int(bomb_x / self.cell_size)
            grid_row = int(bomb_y / self.cell_size)
            bomb_grid.add((grid_row, grid_col))
        return bomb_grid

if __name__ == "__main__":
    game = PacmanGame()
    game.run()

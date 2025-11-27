import pygame
import sys
import random
import math
import signal
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm
from pacman_ai import PacmanAI
from ghost_avoidance_visualizer import GhostAvoidanceVisualizer
import config

class PacmanGame:
    def __init__(self, width=50, height=28, cell_size=30):
        self.maze_gen = MazeGenerator(width, height, complexity=1)  # Độ phức tạp mê cung
        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
        self.cell_size = cell_size
        # Add extra width for right panel (350px)
        self.screen_width = width * cell_size + 380
        self.screen_height = (height + 3) * cell_size  # Normal UI space

        pygame.init()
        pygame.mixer.init()  # Initialize audio mixer
        
        # Load and play opening sound
        # try:
        #     self.opening_sound = pygame.mixer.Sound('public/opening.wav')
        #     self.opening_sound.play()
        # except pygame.error as e:
        #     print(f"Warning: Could not load opening sound: {e}")
        #     self.opening_sound = None
        
        # # Load wakawaka sound for eating
        # try:
        #     self.wakawaka_sound = pygame.mixer.Sound('public/wakaWaka.wav')
        # except pygame.error as e:
        #     print(f"Warning: Could not load wakawaka sound: {e}")
        #     self.wakawaka_sound = None
        
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
        self.BLUE = (33, 150, 243)
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
        
        # Game tracking variables for statistics
        self.start_time = pygame.time.get_ticks()  # Track game start time
        self.last_death_cause = None  # Track what caused the last death
        self.initial_dots = []  # Will be set after dots are placed
        self.game_over_message = None  # Store random motivational message once

        # Pacman properties - will be set after maze generation
        self.pacman_pos = [14.0, 23.0]  # Temporary position, will be updated as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = config.PACMAN_LEGACY_SPEED  # Use config value
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

        # Bombs as obstacles - get from maze generator (already validated)
        self.bombs = []
        self.load_bombs_from_maze_generator()

        # Ghosts
        self.ghosts = []
        self.create_ghosts()

        # Initialize Pacman AI
        self.pacman_ai = PacmanAI(self)
        
        # Initialize Ghost Avoidance Visualizer
        try:
            self.visualizer = GhostAvoidanceVisualizer(self)
            print("✅ Ghost Avoidance Visualizer loaded successfully")
            print("   Press 'V' to toggle visualization")
            print("   Press 'B' to toggle debug info")
            print("   Press 'SHIFT+S' to save analysis report")
        except Exception as e:
            print(f"⚠️  Could not load visualizer: {e}")
            self.visualizer = None

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
        
        # Enhanced ghost avoidance
        self.escape_mode = False  # Đang trong chế độ thoát hiểm
        self.escape_steps = 0     # Số bước đã di chuyển thoát hiểm
        self.min_escape_distance = 6  # Tối thiểu 6 bước trước khi quay lại
        self.original_direction = None  # Hướng đi ban đầu trước khi quay đầu

        # Shortest path visualization
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0

        # Game timing - FPS independent movement
        self.target_fps = config.TARGET_FPS  # Use configurable FPS
        self.last_update = pygame.time.get_ticks()
        self.delta_time = 0  
        self.max_delta_time = config.MAX_DELTA_TIME  # Cap for large frame times
        self.animation_timer = 0
        self.auto_update_timer = 0
        
        # Performance monitoring
        self.fps_history = []
        self.show_fps_info = False  # Toggle with F key
        self.collision_checks_per_frame = 0  # Track collision performance

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
        min_distance = 5  # Minimum distance between power pellets
        max_pellets = 7  # Maximum number of power pellets
        attempts = 10
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
        
        # Save initial dots count for statistics
        self.initial_dots = self.dots.copy()

    def load_bombs_from_maze_generator(self):
        """Load bomb positions from maze generator - bombs are pre-validated during maze generation"""
        self.bombs = []
        
        if not hasattr(self.maze_gen, 'bomb_positions') or not self.maze_gen.bomb_positions:
            print("⚠️  No bomb positions from maze generator")
            return
        
        print(f"\n📦 Loading {len(self.maze_gen.bomb_positions)} bombs from MazeGenerator")
        
        for row, col in self.maze_gen.bomb_positions:
            # Verify position is valid
            if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
                print(f"❌ Bomb at Grid({row}, {col}) out of bounds - SKIPPED")
                continue
            
            maze_value = self.maze[row, col]
            if maze_value != 0:
                print(f"❌ Bomb at Grid({row}, {col}) not on path (maze={maze_value}) - SKIPPED")
                continue
            
            # Convert grid to pixel coordinates (center of cell)
            center_x = (col + 0.5) * self.cell_size
            center_y = (row + 0.5) * self.cell_size
            
            self.bombs.append((center_x, center_y))
            print(f"✅ Loaded bomb at Grid({row}, {col}) -> Pixel({center_x:.1f}, {center_y:.1f})")
        
        print(f"✅ Successfully loaded {len(self.bombs)} bombs\n")

    def place_bombs_OLD_DEPRECATED(self):
        """
        OLD METHOD - DEPRECATED
        This method is kept for reference but should NOT be used.
        Use load_bombs_from_maze_generator() instead.
        """
        self.bombs = []
        
        # Collect all valid positions (ONLY open paths) with ULTRA STRICT validation
        valid_positions = []
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                # ===== ULTRA STRICT VALIDATION =====
                # Check 1: Must be within bounds
                if not (0 <= y < self.maze_gen.height and 0 <= x < self.maze_gen.width):
                    continue
                
                # Check 2: MUST be exactly 0 (path) - reject EVERYTHING else
                maze_value = self.maze[y, x]
                if maze_value != 0:
                    continue  # Skip walls (1) and any other value
                
                # Check 3: Explicitly reject walls one more time
                if maze_value == 1:
                    continue
                    
                # Check 4: Skip start and goal positions
                if (y, x) == self.start or (y, x) == self.goal:
                    continue
                
                # Check 5: Ensure minimum distance from start and goal
                start_dist = math.sqrt((x - self.start[1])**2 + (y - self.start[0])**2)
                goal_dist = math.sqrt((x - self.goal[1])**2 + (y - self.goal[0])**2)
                
                # Must be at least 5 cells away from start/goal (increased from 4)
                if start_dist <= 5 or goal_dist <= 5:
                    continue
                
                # Check 6: Removed - too restrictive
                # The surrounding_walls check below is sufficient
                
                # Check 7: Ensure position is not adjacent to walls on all sides (avoid dead ends)
                surrounding_walls = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:  # Skip center cell
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                            if self.maze[ny, nx] == 1:  # Count walls
                                surrounding_walls += 1
                
                # Reject positions surrounded by too many walls (dead ends or corners)
                if surrounding_walls >= 6:  # If 6+ out of 8 neighbors are walls, skip
                    continue
                
                # FINAL CHECK: Verify this is definitely a path (0)
                if self.maze[y, x] == 0:
                    valid_positions.append((y, x))  # Store as (row, col) for consistency

        print(f"Tìm được {len(valid_positions)} vị trí hợp lệ để đặt bom (chỉ trên đường đi)")

        if not valid_positions:
            print("⚠️  Không thể đặt bom nào - không có vị trí hợp lệ!")
            return

        # Thuật toán đặt bom với kiểm tra pathfinding nghiêm ngặt
        bomb_positions = self.place_bombs_with_pathfinding_check(valid_positions, max_bombs=5)
        
        print(f"\n📍 Đặt thành công {len(bomb_positions)} quả bom (đảm bảo luôn có đường đi)\n")

        # Place bombs at selected positions - with FINAL ULTRA STRICT validation
        valid_bomb_count = 0
        for row, col in bomb_positions:  # bomb_positions stores (row, col)
            # ===== FINAL ULTRA STRICT VALIDATION =====
            # Check 1: Verify bounds
            if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
                print(f"❌ WARNING: Bom vượt biên giới tại Grid({row}, {col}) - BỎ QUA")
                continue
            
            # Check 2: Get maze value ONCE to avoid multiple array accesses
            maze_value = self.maze[row, col]
            
            # Check 3: MUST be exactly 0 (path) - reject EVERYTHING else
            if maze_value != 0:
                print(f"❌ WARNING: Cố gắng đặt bom trên TƯỜNG tại Grid({row}, {col}) - Giá trị: {maze_value} - BỎ QUA")
                continue
            
            # Check 4: Explicitly reject walls (redundant but safe)
            if maze_value == 1:
                print(f"❌ WARNING: Vị trí Grid({row}, {col}) là TƯỜNG (giá trị 1) - BỎ QUA")
                continue
            
            # Check 5: FINAL verification - must be path (0)
            if maze_value == 0:
                # Calculate pixel position from grid coordinates
                # col = x coordinate, row = y coordinate
                center_x = (col + 0.5) * self.cell_size
                center_y = (row + 0.5) * self.cell_size
                center = (center_x, center_y)
                
                self.bombs.append(center)
                valid_bomb_count += 1
                print(f"✅ Đặt bom thành công tại Grid({row}, {col}) -> Pixel({center_x:.1f}, {center_y:.1f}) - Maze[{row},{col}]={maze_value}")
            else:
                print(f"❌ WARNING: Không thể xác nhận Grid({row}, {col}) là đường đi - Giá trị: {maze_value} - BỎ QUA")
        
        print(f"✅ Đặt được {valid_bomb_count}/{len(bomb_positions)} quả bom hợp lệ trên đường đi")
        
        # Debug: Verify all bombs are on paths
        self.verify_bomb_placement()

    def verify_bomb_placement(self):
        """Debug function to verify all bombs are placed correctly on paths"""
        print("\n=== 🔍 KIỂM TRA CHI TIẾT VỊ TRÍ BOM ===")
        errors_found = 0
        
        for i, bomb in enumerate(self.bombs):
            # Convert bomb pixel coordinate to grid position
            # Use round() for accurate conversion from center position
            grid_col = round(bomb[0] / self.cell_size - 0.5)  # x -> col
            grid_row = round(bomb[1] / self.cell_size - 0.5)  # y -> row
            
            # Check bounds
            if not (0 <= grid_row < self.maze_gen.height and 0 <= grid_col < self.maze_gen.width):
                print(f"❌ BOM {i+1}: VƯỢT BIÊN GIỚI! Grid({grid_row}, {grid_col}) - Pixel{bomb}")
                errors_found += 1
                continue
            
            # Get maze value
            maze_value = self.maze[grid_row, grid_col]
            
            # Verify this is a path (0)
            if maze_value == 0:
                print(f"✅ BOM {i+1}: OK - Đặt trên đường đi Grid(row={grid_row}, col={grid_col}) - Pixel{bomb} - Maze[{grid_row},{grid_col}]={maze_value}")
            else:
                print(f"❌❌❌ BOM {i+1}: LỖI NGHIÊM TRỌNG! Đặt trên TƯỜNG Grid(row={grid_row}, col={grid_col}) - Pixel{bomb} - Maze[{grid_row},{grid_col}]={maze_value}")
                errors_found += 1
        
        print(f"\n📊 Tổng số bom: {len(self.bombs)}")
        print(f"{'✅ Tất cả bom đặt đúng!' if errors_found == 0 else f'❌ Phát hiện {errors_found} lỗi!'}")
        print("=" * 45 + "\n")

    def place_bombs_with_pathfinding_check(self, valid_positions, max_bombs=5):
        """Place bombs while ensuring path to goal ALWAYS remains available - ENHANCED"""
        selected_bombs = []
        remaining_positions = valid_positions.copy()
        random.shuffle(remaining_positions)
        
        # Kiểm tra đường đi ban đầu MULTIPLE TIMES để đảm bảo
        initial_path, initial_distance = self.dijkstra.shortest_path(self.start, self.goal)
        if not initial_path:
            print("❌ CRITICAL: Không có đường đi ban đầu từ start đến goal!")
            return []
        
        print(f"📍 Đường đi ban đầu: {initial_distance} bước")
        
        # Track failed positions to avoid retrying
        failed_positions = set()
        attempts = 0
        max_attempts = len(remaining_positions)
        
        while len(selected_bombs) < max_bombs and attempts < max_attempts:
            attempts += 1
            
            # Find next candidate that hasn't failed
            bomb_pos = None
            for pos in remaining_positions:
                if pos not in failed_positions:
                    bomb_pos = pos
                    remaining_positions.remove(pos)
                    break
            
            if bomb_pos is None:
                break  # No more candidates
                
            row, col = bomb_pos
            
            # ===== ULTRA STRICT PRE-VALIDATION =====
            # Verify bounds
            if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
                failed_positions.add(bomb_pos)
                continue
            
            # MUST be path (0)
            maze_value = self.maze[row, col]
            if maze_value != 0:
                failed_positions.add(bomb_pos)
                continue
            
            # Removed: is_at_least_distance_from_wall check - too restrictive
            # The surrounding_walls check in place_bombs() is sufficient
            
            # Check distance from goal (must be at least 5 cells away)
            goal_dist = math.sqrt((col - self.goal[1])**2 + (row - self.goal[0])**2)
            if goal_dist <= 5:
                failed_positions.add(bomb_pos)
                continue
            
            # Check distance from other bombs
            too_close = any(
                math.sqrt((col - sc)**2 + (row - sr)**2) < 5  # Increased from 4 to 5
                for sr, sc in selected_bombs
            )
            if too_close:
                failed_positions.add(bomb_pos)
                continue
            
            # Check not on critical path (main path between start and goal)
            if initial_path and (row, col) in initial_path[:max(3, len(initial_path)//3)]:
                # Skip if on first third of path - too critical
                failed_positions.add(bomb_pos)
                continue
            
            # ===== CRITICAL: Test MULTIPLE alternative paths =====
            temp_bombs = selected_bombs + [(row, col)]
            temp_bomb_grid = set(temp_bombs)
            
            # Test primary path
            path, distance = self.dijkstra.shortest_path_with_obstacles(
                self.start, self.goal, temp_bomb_grid
            )
            
            # ENHANCED CHECK: Path must exist, not be too long, AND have alternatives
            if not path:
                failed_positions.add(bomb_pos)
                continue
            
            if distance > initial_distance * 1.5:  # Stricter limit (was 2.0)
                failed_positions.add(bomb_pos)
                continue
            
            # ===== NEW: Verify alternative paths exist =====
            # Check that removing one bomb still leaves path
            alternative_exists = False
            if len(temp_bombs) > 1:
                # Try removing each bomb and see if path still works
                for test_idx in range(len(temp_bombs)):
                    test_bombs = temp_bombs[:test_idx] + temp_bombs[test_idx+1:]
                    test_path, _ = self.dijkstra.shortest_path_with_obstacles(
                        self.start, self.goal, set(test_bombs)
                    )
                    if test_path:
                        alternative_exists = True
                        break
            else:
                alternative_exists = True  # First bomb always ok
            
            if not alternative_exists and len(temp_bombs) > 1:
                failed_positions.add(bomb_pos)
                continue
            
            # ===== FINAL VERIFICATION =====
            if self.maze[row, col] == 0:
                selected_bombs.append((row, col))
                print(f"✅ Đặt bom #{len(selected_bombs)} tại Grid({row}, {col}) - Path: {distance} bước (limit: {int(initial_distance * 1.5)})")
                
                # Double-check path still exists after adding
                verify_path, _ = self.dijkstra.shortest_path_with_obstacles(
                    self.start, self.goal, set(selected_bombs)
                )
                if not verify_path:
                    print(f"❌ ROLLBACK: Bom tại Grid({row}, {col}) chặn đường!")
                    selected_bombs.remove((row, col))
                    failed_positions.add(bomb_pos)
            else:
                failed_positions.add(bomb_pos)
        
        # FINAL GLOBAL CHECK
        if selected_bombs:
            final_path, final_dist = self.dijkstra.shortest_path_with_obstacles(
                self.start, self.goal, set(selected_bombs)
            )
            if not final_path:
                print("❌ CRITICAL: Final check failed - clearing all bombs!")
                return []
            print(f"✅ Final verification: Path exists ({final_dist} bước)")
        
        return selected_bombs

    def select_bomb_positions_improved(self, positions, min_distance, max_bombs=5):
        """Improved algorithm to select bomb positions with better distribution"""
        if not positions:
            return []
        
        selected = []
        remaining_positions = positions.copy()
        random.shuffle(remaining_positions)  # Randomize order
        
        original_min_distance = min_distance
        
        # Thuật toán greedy cải tiến với fallback
        for attempt in range(max_bombs * 20):  # Nhiều attempt hơn
            if len(selected) >= max_bombs or not remaining_positions:
                break
                
            # Tìm vị trí tốt nhất trong remaining positions
            best_pos = None
            best_score = -1
            
            for pos in remaining_positions:
                # Tính score dựa trên khoảng cách đến các bom đã chọn
                min_dist_to_selected = float('inf')
                for selected_pos in selected:
                    dist = math.sqrt((pos[0] - selected_pos[0])**2 + (pos[1] - selected_pos[1])**2)
                    min_dist_to_selected = min(min_dist_to_selected, dist)
                
                # Score cao hơn cho vị trí xa các bom đã chọn
                if len(selected) == 0 or min_dist_to_selected >= min_distance:
                    score = min_dist_to_selected if len(selected) > 0 else 100
                    if score > best_score:
                        best_score = score
                        best_pos = pos
            
            if best_pos:
                selected.append(best_pos)
                # Loại bỏ các vị trí quá gần vị trí vừa chọn
                remaining_positions = [pos for pos in remaining_positions 
                                     if math.sqrt((pos[0] - best_pos[0])**2 + (pos[1] - best_pos[1])**2) >= min_distance]
            else:
                # Nếu không tìm được vị trí thỏa mãn, giảm min_distance và thử lại
                min_distance = max(2, min_distance - 1)
                # print(f"Giảm khoảng cách xuống {min_distance} để tìm thêm vị trí...")
                if min_distance < 2:
                    # Nếu vẫn không được, chọn ngẫu nhiên từ remaining
                    if remaining_positions and len(selected) < max_bombs:
                        selected.append(random.choice(remaining_positions))
                    break
        
        # print(f"Chọn được {len(selected)} vị trí bom (min_distance cuối: {min_distance})")
        return selected

    def count_adjacent_walls(self, y, x):
        """Count number of walls adjacent to position (y,x)"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        wall_count = 0
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                if self.maze[ny, nx] == 1:  # Wall
                    wall_count += 1
            else:
                # Đếm biên mê cung như tường
                wall_count += 1
        return wall_count

    def is_not_adjacent_to_wall(self, y, x):
        """Check if position (y,x) is not adjacent to any wall"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                if self.maze[ny, nx] == 1:  # Wall
                    return False
        return True

    def is_at_least_distance_from_wall(self, y, x, min_distance=1):
        """Check if position (y,x) is at least min_distance away from any wall"""
        for check_y in range(max(0, y - min_distance), min(self.maze_gen.height, y + min_distance + 1)):
            for check_x in range(max(0, x - min_distance), min(self.maze_gen.width, x + min_distance + 1)):
                if self.maze[check_y, check_x] == 1:  # Tìm thấy tường trong phạm vi
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
                'speed': config.GHOST_SPEED,  # Use config value
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
                'scared_timer': 0,  # Timer for scared state duration
                'eaten': False,  # Whether ghost has been eaten (shows only eyes)
                'eaten_timer': 0  # Timer for eaten state duration
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

    def find_far_spawn_position(self, pacman_row, pacman_col, min_distance=15, max_attempts=50):
        """Find a random valid spawn position far from Pacman"""
        import random
        
        valid_positions = []
        
        # Collect all valid positions that are far enough from Pacman
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                # Must be a valid path
                if self.maze[row, col] != 0:
                    continue
                
                # Calculate distance from Pacman
                distance = math.sqrt((col - pacman_col)**2 + (row - pacman_row)**2)
                
                # Must be at least min_distance away
                if distance >= min_distance:
                    valid_positions.append((row, col))
        
        # If we found valid far positions, choose one randomly
        if valid_positions:
            return random.choice(valid_positions)
        
        # Fallback 1: Try with reduced distance
        for reduced_dist in [min_distance * 0.75, min_distance * 0.5, min_distance * 0.25]:
            valid_positions = []
            for row in range(self.maze_gen.height):
                for col in range(self.maze_gen.width):
                    if self.maze[row, col] != 0:
                        continue
                    distance = math.sqrt((col - pacman_col)**2 + (row - pacman_row)**2)
                    if distance >= reduced_dist:
                        valid_positions.append((row, col))
            if valid_positions:
                return random.choice(valid_positions)
        
        # Fallback 2: Return any valid position
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                if self.maze[row, col] == 0:
                    return (row, col)
        
        # Final fallback: center of maze
        return (self.maze_gen.height // 2, self.maze_gen.width // 2)

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
        for i, bomb in enumerate(self.bombs):
            bomb_x, bomb_y = bomb
            
            # Bomb body colors - make bombs more distinctive  
            ORANGE = (255, 165, 0)  # Bright orange instead of gray
            DARK_ORANGE = (200, 100, 0)
            WHITE = (255, 255, 255)
            RED = (255, 0, 0)
            
            # Draw bomb body with gradient effect
            bomb_radius = 10  # Make slightly larger
            
            # Create gradient effect by drawing multiple circles of decreasing size
            for i in range(bomb_radius, 0, -1):
                # Calculate color gradient from orange to dark orange
                intensity = 255 - (i * 15)  # Different gradient calculation
                intensity = max(100, min(255, intensity))  # Clamp between 100 and 255
                color = (intensity, intensity//2, 0)  # Orange gradient
                
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
            mouth_angle = 270
        elif self.pacman_direction == [0, 1]:  # Down
            mouth_angle = 90

        mouth_open_angle = 45 if self.pacman_mouth_open else 1
        pacman_radius = self.cell_size // 2 - 2
        
        if self.pacman_direction != [0, 0] and mouth_open_angle > 0:
            pygame.draw.circle(self.screen, self.YELLOW, center, pacman_radius)
            
            start_angle = math.radians(mouth_angle - mouth_open_angle)
            end_angle = math.radians(mouth_angle + mouth_open_angle)
            
            mouth_radius = pacman_radius + 5
            
            pygame.draw.polygon(self.screen, self.BLACK, [
                center,
                (center[0] + math.cos(start_angle) * mouth_radius,
                 center[1] + math.sin(start_angle) * mouth_radius),
                (center[0] + math.cos(end_angle) * mouth_radius,
                 center[1] + math.sin(end_angle) * mouth_radius)
            ])
        else:
            pygame.draw.circle(self.screen, self.YELLOW, center, pacman_radius)

    def draw_ghosts(self):
        """Draw ghosts using images from public folder"""
        for ghost in self.ghosts:
            col, row = ghost['pos']
            center = (col * self.cell_size + self.cell_size // 2,
                     row * self.cell_size + self.cell_size // 2)

            # Determine direction for image selection
            direction = ghost['direction']
            facing_right = direction[0] > 0 or (direction[0] == 0 and direction[1] == 0)  # Default to right if stationary
            
            # If ghost is eaten, show only eyes
            if ghost.get('eaten', False):
                # Use eyes image
                image_key = 'eyes_right' if facing_right else 'eyes_left'
                eyes_image = self.ghost_images.get(image_key)
                
                if eyes_image:
                    # Scale image to fit cell size
                    scaled_image = pygame.transform.scale(eyes_image, (self.cell_size, self.cell_size))
                    # Position image centered on ghost position
                    image_rect = scaled_image.get_rect(center=center)
                    self.screen.blit(scaled_image, image_rect)
                else:
                    # Fallback: draw simple eyes
                    self.draw_eyes_fallback(center)
                continue  # Skip to next ghost
            
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

    def draw_eyes_fallback(self, center):
        """Draw simple eyes when ghost image is not available"""
        # Just draw two white eyes with black pupils on transparent background
        eye_size = 6
        pupil_size = 3
        eye_y = center[1]
        left_eye = (center[0] - 8, eye_y)
        right_eye = (center[0] + 8, eye_y)

        # Draw white eyes
        pygame.draw.circle(self.screen, self.WHITE, left_eye, eye_size)
        pygame.draw.circle(self.screen, self.WHITE, right_eye, eye_size)
        
        # Draw black pupils
        pygame.draw.circle(self.screen, self.BLACK, left_eye, pupil_size)
        pygame.draw.circle(self.screen, self.BLACK, right_eye, pupil_size)

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

        # FPS and performance info (top-right corner)
        if self.show_fps_info:
            self.draw_fps_info()

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
            
            vis_status = " | V:Visual" if self.visualizer and self.visualizer.enabled else ""
            
            inst_text = self.font.render(f"{mode_text} | {ghost_info}{path_info} | V: Visual | B: Debug | A: Auto | H: Hint | R: Restart", True, self.YELLOW)
            self.screen.blit(inst_text, (10, ui_y + 30))

        elif self.game_state == "paused":
            pause_text = self.large_font.render("PAUSED", True, self.YELLOW)
            self.screen.blit(pause_text, (self.screen_width // 2 - 60, self.screen_height // 2))

    def draw_fps_info(self):
        """Draw FPS and performance information on right side (top position)"""
        if not self.fps_history:
            return
            
        # Calculate FPS statistics
        current_fps = self.fps_history[-1] if self.fps_history else 0
        avg_fps = sum(self.fps_history) / len(self.fps_history)
        min_fps = min(self.fps_history)
        max_fps = max(self.fps_history)
        
        # Draw performance info background on right side (top position)
        maze_width = self.maze_gen.width * self.cell_size
        info_width = 240
        info_height = 120
        info_x = maze_width + 5
        info_y = 10
        
        # Semi-transparent background
        bg_surface = pygame.Surface((info_width, info_height))
        bg_surface.set_alpha(180)
        bg_surface.fill((0, 0, 0))
        self.screen.blit(bg_surface, (info_x, info_y))
        
        # Border
        pygame.draw.rect(self.screen, self.WHITE, (info_x, info_y, info_width, info_height), 2)
        
        # FPS information
        small_font = pygame.font.SysFont("arial", 14, bold=True)
        y_offset = info_y + 10
        
        # Current FPS (larger, colored)
        fps_color = self.WHITE
        if current_fps < 30:
            fps_color = self.RED
        elif current_fps < 50:
            fps_color = self.ORANGE
        else:
            fps_color = (0, 255, 0)  # Green
            
        current_text = small_font.render(f"FPS: {current_fps:.1f}", True, fps_color)
        self.screen.blit(current_text, (info_x + 10, y_offset))
        
        # Target FPS
        target_text = small_font.render(f"Target: {self.target_fps}", True, self.WHITE)
        self.screen.blit(target_text, (info_x + 110, y_offset))
        
        # Average FPS
        y_offset += 16
        avg_text = small_font.render(f"Avg: {avg_fps:.1f}", True, self.WHITE)
        self.screen.blit(avg_text, (info_x + 10, y_offset))
        
        # Min/Max FPS
        y_offset += 16
        min_text = small_font.render(f"Min: {min_fps:.1f}", True, self.WHITE)
        self.screen.blit(min_text, (info_x + 10, y_offset))
        
        max_text = small_font.render(f"Max: {max_fps:.1f}", True, self.WHITE)
        self.screen.blit(max_text, (info_x + 110, y_offset))
        
        # Delta time
        y_offset += 16
        delta_text = small_font.render(f"Delta: {self.delta_time*1000:.1f}ms", True, self.WHITE)
        self.screen.blit(delta_text, (info_x + 10, y_offset))
        
        # Movement speeds
        y_offset += 16
        dynamic_status = "ON" if config.ENABLE_DYNAMIC_SPEED else "OFF"
        speed_text = small_font.render(f"Speed: P{config.PACMAN_SPEED} G{config.GHOST_SPEED}", True, self.YELLOW)
        self.screen.blit(speed_text, (info_x + 10, y_offset))
        
        # Dynamic speed status
        y_offset += 12
        dynamic_color = (0, 255, 0) if config.ENABLE_DYNAMIC_SPEED else self.RED
        dynamic_text = small_font.render(f"Dynamic: {dynamic_status}", True, dynamic_color)
        self.screen.blit(dynamic_text, (info_x + 10, y_offset))
        
        # Collision performance
        y_offset += 12
        collision_color = (0, 255, 0) if self.collision_checks_per_frame < 50 else self.ORANGE if self.collision_checks_per_frame < 200 else self.RED
        collision_text = small_font.render(f"Checks: {self.collision_checks_per_frame}", True, collision_color)
        self.screen.blit(collision_text, (info_x + 10, y_offset))

    def draw_win_notification(self):
        """Draw a beautiful win notification box with score and congratulations"""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(150)  # Semi-transparent
        overlay.fill((0, 0, 0))  # Black overlay
        self.screen.blit(overlay, (0, 0))
        
        # Calculate notification box dimensions
        box_width = 400
        box_height = 300
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        # Draw main notification box with gradient border
        # Outer border (gold)
        outer_border = pygame.Rect(box_x - 5, box_y - 5, box_width + 10, box_height + 10)
        pygame.draw.rect(self.screen, (255, 215, 0), outer_border, border_radius=15)  # Gold border
        
        # Inner border (darker gold)
        inner_border = pygame.Rect(box_x - 2, box_y - 2, box_width + 4, box_height + 4)
        pygame.draw.rect(self.screen, (184, 134, 11), inner_border, border_radius=12)  # Dark gold
        
        # Main box (dark blue gradient)
        main_box = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, (25, 25, 112), main_box, border_radius=10)  # Midnight blue
        
        # Draw inner gradient effect
        for i in range(box_height // 3):
            alpha = int(50 * (1 - i / (box_height // 3)))
            if alpha > 0:
                gradient_surf = pygame.Surface((box_width, 1))
                gradient_surf.set_alpha(alpha)
                gradient_surf.fill((135, 206, 250))  # Light sky blue
                self.screen.blit(gradient_surf, (box_x, box_y + i))
        
        # Title: "CONGRATULATIONS!"
        title_font = pygame.font.SysFont("arial", 36, bold=True)
        title_text = title_font.render("CONGRATULATIONS!", True, (255, 215, 0))  # Gold
        title_rect = title_text.get_rect(center=(box_x + box_width // 2, box_y + 40))
        self.screen.blit(title_text, title_rect)
        
        # Score information
        score_font = pygame.font.SysFont("arial", 20, bold=True)
        
        # Current score
        score_text = score_font.render(f"Final Score: {self.score}", True, self.WHITE)
        score_rect = score_text.get_rect(center=(box_x + box_width // 2, box_y + 100))
        self.screen.blit(score_text, score_rect)
        
        # Level info
        level_text = score_font.render(f"Level {self.level} Completed", True, (0, 255, 127))  # Light blue
        level_rect = level_text.get_rect(center=(box_x + box_width // 2, box_y + 160))
        self.screen.blit(level_text, level_rect)
        
        # Divider line
        line_y = box_y + 190
        pygame.draw.line(self.screen, (255, 215, 0), (box_x + 50, line_y), (box_x + box_width - 50, line_y), 2)
        
        # Instructions
        instruction_font = pygame.font.SysFont("arial", 16, bold=True)
        next_text = instruction_font.render("Press N for Next Level", True, (144, 238, 144))  # Light green
        next_rect = next_text.get_rect(center=(box_x + box_width // 2, box_y + 220))
        self.screen.blit(next_text, next_rect)
        
        restart_text = instruction_font.render("Press R to Restart", True, (255, 182, 193))  # Light pink
        restart_rect = restart_text.get_rect(center=(box_x + box_width // 2, box_y + 245))
        self.screen.blit(restart_text, restart_rect)

    def draw_game_over_notification(self):
        """Draw a detailed game over notification box with statistics and motivational message"""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(150)  # Semi-transparent
        overlay.fill((0, 0, 0))  # Black overlay
        self.screen.blit(overlay, (0, 0))
        
        # Calculate notification box dimensions
        box_width = 450
        box_height = 350
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        # Draw main notification box with dramatic red gradient border
        # Outer border (dark red)
        outer_border = pygame.Rect(box_x - 5, box_y - 5, box_width + 10, box_height + 10)
        pygame.draw.rect(self.screen, (139, 0, 0), outer_border, border_radius=15)  # Dark red border
        
        # Inner border (crimson)
        inner_border = pygame.Rect(box_x - 2, box_y - 2, box_width + 4, box_height + 4)
        pygame.draw.rect(self.screen, (220, 20, 60), inner_border, border_radius=12)  # Crimson
        
        # Main box (dark navy gradient)
        main_box = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, (25, 25, 60), main_box, border_radius=10)  # Dark navy
        
        # Draw inner gradient effect (red to black)
        for i in range(box_height // 4):
            alpha = int(40 * (1 - i / (box_height // 4)))
            if alpha > 0:
                gradient_surf = pygame.Surface((box_width, 1))
                gradient_surf.set_alpha(alpha)
                gradient_surf.fill((139, 0, 0))  # Dark red
                self.screen.blit(gradient_surf, (box_x, box_y + i))
        
        # Title: "GAME OVER"
        title_font = pygame.font.SysFont("arial", 42, bold=True)
        title_text = title_font.render("GAME OVER", True, (255, 69, 0))  # Red-orange
        title_rect = title_text.get_rect(center=(box_x + box_width // 2, box_y + 45))
        self.screen.blit(title_text, title_rect)
        
        # Game statistics
        stats_font = pygame.font.SysFont("arial", 18, bold=True)
        
        # Final score
        score_text = stats_font.render(f"Final Score: {self.score}", True, (255, 215, 0))  # Gold
        score_rect = score_text.get_rect(center=(box_x + box_width // 2, box_y + 110))
        self.screen.blit(score_text, score_rect)
        
        # Determine cause of death
        death_cause = "Unknown cause"
        death_color = (255, 255, 255)
        if hasattr(self, 'last_death_cause') and self.last_death_cause:
            if "Ma " in self.last_death_cause:
                death_cause = f"👻 Bị {self.last_death_cause} Bắt"
                death_color = (255, 182, 193)  # Light pink
            elif self.last_death_cause == "Bom nổ":
                death_cause = "💣 Chết Vì Bom Nổ"
                death_color = (255, 140, 0)    # Dark orange
            else:
                death_cause = f"💀 {self.last_death_cause}"
                death_color = (255, 99, 71)   # Tomato red
        else:
            death_cause = "💀 Hết Mạng Sống"
            death_color = (255, 99, 71)   # Tomato red
        
        # Death cause
        cause_text = stats_font.render(f"Cause: {death_cause}", True, death_color)
        cause_rect = cause_text.get_rect(center=(box_x + box_width // 2, box_y + 140))
        self.screen.blit(cause_text, cause_rect)
        
        # Performance stats
        stats_small_font = pygame.font.SysFont("arial", 14, bold=True)
        
        # Dots collected
        dots_collected = len([pos for pos in self.initial_dots if pos not in self.dots])
        total_dots = len(self.initial_dots) if hasattr(self, 'initial_dots') else len(self.dots)
        dots_text = stats_small_font.render(f"Dots Collected: {dots_collected}/{total_dots}", True, (173, 216, 230))  # Light blue
        dots_rect = dots_text.get_rect(center=(box_x + box_width // 2, box_y + 170))
        self.screen.blit(dots_text, dots_rect)
        
        # Survival time (if available)
        if hasattr(self, 'start_time'):
            # Use death_time if available, otherwise current time
            end_time = self.death_time if hasattr(self, 'death_time') and self.death_time else pygame.time.get_ticks()
            survival_time = (end_time - self.start_time) // 1000
            minutes = survival_time // 60
            seconds = survival_time % 60
            time_text = stats_small_font.render(f"Survival Time: {minutes:02d}:{seconds:02d}", True, (144, 238, 144))  # Light green
            time_rect = time_text.get_rect(center=(box_x + box_width // 2, box_y + 195))
            self.screen.blit(time_text, time_rect)
        
        # Motivational message - use stored message to prevent flickering
        motivation_font = pygame.font.SysFont("arial", 16, bold=True)
        if hasattr(self, 'game_over_message') and self.game_over_message:
            motivation_msg = self.game_over_message
        else:
            # Fallback if message not set
            motivation_msg = "🌟 Every ending is a new beginning!"
        
        motivation_text = motivation_font.render(motivation_msg, True, (255, 223, 0))  # Gold
        motivation_rect = motivation_text.get_rect(center=(box_x + box_width // 2, box_y + 230))
        self.screen.blit(motivation_text, motivation_rect)
        
        # Instructions
        instruction_font = pygame.font.SysFont("arial", 16, bold=True)
        
        restart_text = instruction_font.render("Press R to Restart Game", True, (255, 182, 193))  # Light pink
        restart_rect = restart_text.get_rect(center=(box_x + box_width // 2, box_y + 270))
        self.screen.blit(restart_text, restart_rect)
        
        quit_text = instruction_font.render("Press ESC to Quit", True, (211, 211, 211))  # Light gray
        quit_rect = quit_text.get_rect(center=(box_x + box_width // 2, box_y + 295))
        self.screen.blit(quit_text, quit_rect)

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

            # ENHANCED CHECK: Target block must be valid (allowing movement through eyes)
            if self.is_valid_position_ignore_eyes(target_col, target_row):
                self.pacman_direction = self.pacman_next_direction[:]
                self.pacman_next_direction = [0, 0]

        # Move in current direction - BLOCK BY BLOCK
        if self.pacman_direction != [0, 0]:
            # Calculate target block position
            current_col = int(round(self.pacman_pos[0]))
            current_row = int(round(self.pacman_pos[1]))
            target_col = current_col + self.pacman_direction[0]
            target_row = current_row + self.pacman_direction[1]

            # Check if we can move to target block (allowing movement through eyes)
            if self.is_valid_position_ignore_eyes(target_col, target_row):
                # Speed calculation - configurable dynamic speed control
                base_speed = config.PACMAN_SPEED
                
                if config.ENABLE_DYNAMIC_SPEED:
                    # Calculate distance to nearest ghost
                    min_ghost_distance = float('inf')
                    for ghost in self.ghosts:
                        if not self.is_ghost_just_eyes(ghost):  # Only consider active ghosts
                            ghost_row = int(round(ghost['pos'][1]))
                            ghost_col = int(round(ghost['pos'][0]))
                            distance = abs(current_row - ghost_row) + abs(current_col - ghost_col)
                            min_ghost_distance = min(min_ghost_distance, distance)
                    
                    # Apply speed multiplier based on ghost proximity (improved values)
                    if min_ghost_distance <= 2:
                        speed_multiplier = config.DYNAMIC_SPEED_VERY_CLOSE  # Less severe slowdown
                    elif min_ghost_distance <= 4:
                        speed_multiplier = config.DYNAMIC_SPEED_CLOSE
                    elif min_ghost_distance <= 6:
                        speed_multiplier = config.DYNAMIC_SPEED_NEARBY
                    else:
                        speed_multiplier = 1.0  # Normal speed when safe
                    
                    speed = base_speed * speed_multiplier
                else:
                    # No dynamic speed - always use full speed
                    speed = base_speed
                
                step_size = speed * self.delta_time  # Distance to move this frame
                
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
            # Special handling for eaten ghosts (eyes only)
            if ghost.get('eaten', False):
                self.move_eaten_ghost_to_spawn(ghost)
                continue
                
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
                    
                    # Smooth animation towards target block - SLOWER than Pacman
                    # Time-based movement for consistency
                    ghost_speed = config.GHOST_SPEED  # Use config value
                    step_size = ghost_speed * self.delta_time  # Time-based like Pacman
                    
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

    def move_eaten_ghost_to_spawn(self, ghost):
        """Move eaten ghost (eyes only) back to spawn point using pathfinding"""
        # Get Pacman's current position
        pacman_row = int(round(self.pacman_pos[1]))
        pacman_col = int(round(self.pacman_pos[0]))
        
        # Find a random spawn position far from Pacman (minimum 15 cells away)
        spawn_pos = self.find_far_spawn_position(pacman_row, pacman_col, min_distance=15)
        target_pos = (spawn_pos[0], spawn_pos[1])  # (row, col)
        
        # Calculate actual distance for logging
        distance = math.sqrt((spawn_pos[1] - pacman_col)**2 + (spawn_pos[0] - pacman_row)**2)
        print(f"👻 {ghost.get('name', 'Ghost')} eyes: spawn target at Grid({spawn_pos[0]}, {spawn_pos[1]}) - {distance:.1f} cells from Pacman")
        
        current_col = int(round(ghost['pos'][0]))
        current_row = int(round(ghost['pos'][1]))
        current_pos = (current_row, current_col)
        
        # Ensure current position is valid - if not, move to nearest valid position
        if not self.is_valid_position(current_col, current_row):
            # Find nearest valid position
            for radius in range(1, 5):
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        test_row = current_row + dr
                        test_col = current_col + dc
                        if (self.is_valid_position(test_col, test_row)):
                            ghost['pos'][0] = float(test_col)
                            ghost['pos'][1] = float(test_row)
                            current_pos = (test_row, test_col)
                            # print(f"{ghost['name']} eyes moved to valid position {current_pos}")
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
        
        # Initialize path to spawn ONLY if path doesn't exist or is empty
        if not ghost.get('return_path') or len(ghost.get('return_path', [])) == 0:
            try:
                # Use Dijkstra pathfinding to find route back to spawn
                # print(f"{ghost['name']} eyes: trying pathfinding from {current_pos} to {target_pos}")
                path, distance = self.dijkstra.shortest_path(current_pos, target_pos)
                if path and len(path) > 1:
                    ghost['return_path'] = path
                    ghost['path_index'] = 0
                    # print(f"{ghost['name']} eyes finding path home: {len(path)} steps")
                else:
                    # Fallback: create simple direct path with multiple waypoints
                    waypoints = []
                    # Add current position
                    waypoints.append(current_pos)
                    # Add target position
                    waypoints.append(target_pos)
                    
                    ghost['return_path'] = waypoints
                    ghost['path_index'] = 0
                    # print(f"{ghost['name']} eyes using direct path to spawn (pathfinding failed)")
            except Exception as e:
                print(f"Path calculation failed for {ghost['name']} eyes: {e}")
                # Fallback: direct movement
                ghost['return_path'] = [current_pos, target_pos]
                ghost['path_index'] = 0
        
        # Follow the calculated path
        if 'return_path' in ghost and ghost['return_path']:
            path = ghost['return_path']
            path_index = ghost.get('path_index', 0)
            
            # Check if we need to advance to next waypoint
            current_waypoint = path[path_index] if path_index < len(path) else None
            if current_waypoint and abs(current_row - current_waypoint[0]) < 0.1 and abs(current_col - current_waypoint[1]) < 0.1:
                # Reached current waypoint, advance to next
                ghost['path_index'] = min(path_index + 1, len(path) - 1)
                path_index = ghost['path_index']
            
            # Get target position (next waypoint)
            if path_index < len(path):
                target_waypoint = path[path_index]
                target_row, target_col = target_waypoint[0], target_waypoint[1]
                
                # Move towards target waypoint - eyes move faster than normal ghosts
                eyes_speed = config.GHOST_EYES_SPEED  # Use config value
                step_size = eyes_speed * self.delta_time  # Time-based movement
                
                # Calculate direction to target waypoint
                old_pos = [ghost['pos'][0], ghost['pos'][1]]
                
                if abs(ghost['pos'][0] - target_col) > 0.05:
                    if target_col > ghost['pos'][0]:
                        ghost['pos'][0] = min(ghost['pos'][0] + step_size, target_col)
                    else:
                        ghost['pos'][0] = max(ghost['pos'][0] - step_size, target_col)
                
                if abs(ghost['pos'][1] - target_row) > 0.05:
                    if target_row > ghost['pos'][1]:
                        ghost['pos'][1] = min(ghost['pos'][1] + step_size, target_row)
                    else:
                        ghost['pos'][1] = max(ghost['pos'][1] - step_size, target_row)
                
                # Debug: Check if position actually changed (commented for cleaner output)
                # if old_pos != [ghost['pos'][0], ghost['pos'][1]]:
                #     print(f"{ghost['name']} moved from {old_pos} to [{ghost['pos'][0]:.1f}, {ghost['pos'][1]:.1f}] towards waypoint {path_index}/{len(path)} at ({target_row}, {target_col})")
                # else:
                #     print(f"{ghost['name']} STUCK at {old_pos}, target waypoint {path_index}/{len(path)} at ({target_row}, {target_col})")
                
                # Check if ghost reached final spawn point
                final_target = path[-1]
                distance_to_spawn = abs(ghost['pos'][0] - final_target[1]) + abs(ghost['pos'][1] - final_target[0])
                if distance_to_spawn < 0.5:
                    # Ghost has returned to spawn - restore to normal state
                    ghost['eaten'] = False
                    ghost['pos'] = [float(final_target[1]), float(final_target[0])]  # (col, row)
                    # Clean up pathfinding data
                    if 'return_path' in ghost:
                        del ghost['return_path']
                    if 'path_index' in ghost:
                        del ghost['path_index']
                    print(f"✅ {ghost.get('name', 'Ghost')} respawned at Grid({final_target[0]}, {final_target[1]})!")
            else:
                # Reached end of path
                final_target = path[-1]
                ghost['eaten'] = False
                ghost['pos'] = [float(final_target[1]), float(final_target[0])]  # (col, row)
                # Clean up pathfinding data
                if 'return_path' in ghost:
                    del ghost['return_path']
                if 'path_index' in ghost:
                    del ghost['path_index']
                print(f"✅ {ghost.get('name', 'Ghost')} respawned at Grid({final_target[0]}, {final_target[1]})!")

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
        for attempt in range(3):
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

    def find_auto_target(self):
        """GOAL-FIRST target finding - Ưu tiên goal tuyệt đối"""
        try:
            # Sử dụng logic goal-first mới
            self.find_goal_first()

            # Nếu tìm được goal, set làm auto_target
            if self.current_goal:
                self.auto_target = self.current_goal
                self.calculate_auto_path()
                # print(f"Auto target set: {self.auto_target}")
            else:
                # print("No auto target found")
                self.auto_target = None
                self.auto_path = []

        except Exception as e:
            print(f"Error in find_auto_target: {e}")
            self.auto_target = None
            self.auto_path = []

    def _check_ghost_on_path_to_goal(self):
        """
        Kiểm tra có ma nào trên đường đi tới goal không
        Trả về (có_ma, vị_trí_ma, khoảng_cách)
        """
        if not self.current_goal:
            return False, None, 0
            
        pacman_row, pacman_col = int(self.pacman_pos[1]), int(self.pacman_pos[0])
        current_pos = (pacman_row, pacman_col)
        
        # Nếu có auto_path, kiểm tra theo path
        if hasattr(self, 'auto_path') and self.auto_path and len(self.auto_path) > 0:
            # Kiểm tra 6-8 bước đầu tiên trên đường đi tới goal
            check_distance = min(8, len(self.auto_path))
            path_to_check = self.auto_path[:check_distance]
        else:
            # Nếu không có path, tạo đường thẳng tới goal để kiểm tra
            goal_row, goal_col = self.current_goal
            path_to_check = []
            
            # Tạo đường thẳng đơn giản tới goal
            steps = max(abs(goal_row - pacman_row), abs(goal_col - pacman_col))
            if steps > 0:
                for i in range(1, min(8, steps + 1)):
                    progress = i / steps
                    check_row = int(pacman_row + (goal_row - pacman_row) * progress)
                    check_col = int(pacman_col + (goal_col - pacman_col) * progress)
                    path_to_check.append((check_row, check_col))
        
        # Kiểm tra ma
        for ghost in self.ghosts:
            if ghost.get('scared', False):
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            ghost_pos = (ghost_row, ghost_col)
            
            # Kiểm tra khoảng cách trực tiếp tới Pacman trước
            distance_to_pacman = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            # Nếu ma rất gần Pacman (trong 4 ô)
            if distance_to_pacman <= 4:
                # Kiểm tra có line of sight không
                if self._has_line_of_sight(current_pos, ghost_pos):
                    return True, ghost_pos, distance_to_pacman
            
            # Kiểm tra ghost có nằm gần path không
            for i, path_pos in enumerate(path_to_check):
                path_distance = abs(path_pos[0] - ghost_row) + abs(path_pos[1] - ghost_col)
                
                # Nếu ghost rất gần path (trong 2 ô)
                if path_distance <= 2:
                    # Kiểm tra có line of sight với Pacman không
                    if self._has_line_of_sight(current_pos, ghost_pos):
                        return True, ghost_pos, distance_to_pacman
                        
        return False, None, 0

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

    def _is_dead_end(self, col, row):
        """Kiểm tra xem vị trí có phải là dead end không - cải thiện để tránh kẹt"""
        if not self.is_valid_position(col, row):
            return True
        
        valid_exits = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        
        # Đếm số lối ra hợp lệ
        for dx, dy in directions:
            next_col, next_row = col + dx, row + dy
            if self.is_valid_position(next_col, next_row):
                valid_exits += 1
        
        # Cải thiện: chỉ coi là dead end nếu thực sự chỉ có 1 lối ra
        # và lối ra đó không dẫn đến chỗ rộng rãi
        if valid_exits <= 1:
            return True
        elif valid_exits == 2:
            # Kiểm tra có phải corridor hẹp không (2 exits nhưng thẳng hàng)
            exits = []
            for dx, dy in directions:
                next_col, next_row = col + dx, row + dy
                if self.is_valid_position(next_col, next_row):
                    exits.append((dx, dy))
            
            # Nếu 2 exits đối diện nhau (corridor thẳng), không coi là dead end
            if len(exits) == 2:
                dx1, dy1 = exits[0]
                dx2, dy2 = exits[1]
                if (dx1 + dx2 == 0 and dy1 + dy2 == 0):  # Đối diện nhau
                    return False  # Không phải dead end, chỉ là corridor
            
            return True  # Góc cụt
        
        return False  # Đủ rộng rãi

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
            avoidance_radius = getattr(config, 'GHOST_AVOIDANCE_RADIUS', 5)
            path, distance = self.dijkstra.shortest_path_with_ghost_avoidance(
                pacman_pos, self.auto_target, ghost_positions, avoidance_radius=avoidance_radius
            )

            if path and distance < float('inf'):
                self.auto_path = path
                # print(f"Path calculated: {len(path)-1} steps to {self.auto_target}")
                return

        except Exception as e:
            print(f"Path calculation failed: {e}")

        # Fallback: đường đi bình thường nếu không tìm được đường tránh ma
        try:
            bomb_grid = self.get_bomb_grid_positions()
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, self.auto_target, bomb_grid)
            if path and distance < float('inf'):
                self.auto_path = path
                # print(f"Fallback path: {len(path)-1} steps to {self.auto_target} (avoiding bombs)")
            else:
                self.auto_path = []
                # print(" No path found")
        except Exception as e:
            # print(f" Fallback path failed: {e}")
            self.auto_path = []

    def calculate_shortest_path_to_goal(self):
        """Tính toán đường đi ngắn nhất từ vị trí Pacman hiện tại đến goal, tránh bom"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        pacman_pos = (pacman_row, pacman_col)
        
        # Get bomb positions in grid coordinates
        bomb_grid = self.get_bomb_grid_positions()
        
        # Kiểm tra tình trạng bom chặn đường trước khi tính toán
        if bomb_grid:
            is_blocked, blockage_level, alternatives = self.dijkstra.check_bomb_blockage_status(
                pacman_pos, self.current_goal, bomb_grid
            )
            
            # Hiển thị cảnh báo đặc biệt cho complete blockage
            if blockage_level == 'COMPLETE_BLOCKAGE':
                print("🆘 Pacman bị bom bao vây!")
        
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, self.current_goal, bomb_grid)
            if path and distance < float('inf'):
                self.shortest_path = path
                # print(f"Shortest path calculated: {len(path)-1} steps to goal (avoiding {len(bomb_grid)} bombs)")
            else:
                self.shortest_path = []
                if bomb_grid:
                    print("🚫 Bom chặn đường đến mục tiêu!")
                # print(" No path to goal found (considering bomb avoidance)")
        except Exception as e:
            # print(f" Shortest path calculation failed: {e}")
            self.shortest_path = []

    def calculate_hint_path_to_exit(self):
        """Tính toán đường gợi ý từ vị trí Pacman hiện tại đến exit gate (có thể dùng bất cứ lúc nào)"""
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        pacman_pos = (pacman_row, pacman_col)
        
        # Target là exit gate (goal chính của game)
        exit_goal = self.goal if hasattr(self, 'goal') else None
        if not exit_goal:
            print("No exit gate found!")
            self.shortest_path = []
            return
        
        # Get bomb positions in grid coordinates
        bomb_grid = self.get_bomb_grid_positions()
        
        # Kiểm tra bomb blockage cho đường đến exit gate
        if bomb_grid:
            is_blocked, blockage_level, alternatives = self.dijkstra.check_bomb_blockage_status(
                pacman_pos, exit_goal, bomb_grid
            )
            
            if blockage_level == 'COMPLETE_BLOCKAGE':
                print("🆘 Lối thoát bị bom chặn!")
        
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, exit_goal, bomb_grid)
            if path and distance < float('inf'):
                self.shortest_path = path
            else:
                self.shortest_path = []
                if bomb_grid:
                    print("🚫 Exit gate bị cô lập!")
        except Exception as e:
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
        """GOAL-FIRST auto movement với ADVANCED GHOST AVOIDANCE - sử dụng AI mới"""

        # CHECK FOR GHOST AVOIDANCE USING NEW AI SYSTEM
        pacman_row, pacman_col = int(self.pacman_pos[1]), int(self.pacman_pos[0])
        
        # Get nearby ghosts for AI analysis
        nearby_ghosts = []
        for ghost in self.ghosts:
            if ghost.get('scared', False) or ghost.get('eaten', False):
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            distance = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            # Consider ghosts within reasonable range for AI analysis
            if distance <= 8:  # Increased range for better AI analysis
                nearby_ghosts.append(((ghost_row, ghost_col), distance))
        
        # Use NEW AI system for ghost avoidance if there are nearby ghosts
        # Add AI throttling to prevent excessive direction changes
        if not hasattr(self, 'last_ai_call'):
            self.last_ai_call = 0
        if not hasattr(self, 'ai_decision_cooldown'):
            self.ai_decision_cooldown = 200  # 200ms cooldown between AI decisions
            
        current_time = pygame.time.get_ticks()
        ai_can_act = (current_time - self.last_ai_call) >= self.ai_decision_cooldown
        
        if nearby_ghosts and hasattr(self, 'pacman_ai') and ai_can_act:
            try:
                ai_handled = self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts)
                if ai_handled:
                    print(f"🤖 AI xử lý né ma: {len(nearby_ghosts)} ma gần đó")
                    self.last_ai_call = current_time  # Update AI call time
                    return  # AI has handled the situation
            except Exception as e:
                print(f"❌ AI error: {e}")
                # Fall back to simple emergency logic below
        
        # EMERGENCY FALLBACK - Simple emergency stop for critical proximity (≤ 1 cell)
        critical_ghosts = []
        for ghost_pos, distance in nearby_ghosts:
            if distance <= 1:  # Only immediate collision threat
                critical_ghosts.append({
                    'distance': distance,
                    'position': ghost_pos
                })
        
        if critical_ghosts:
            # Find immediate escape direction away from all critical ghosts
            escape_directions = [[1, 0], [-1, 0], [0, 1], [0, -1]]
            best_escape = None
            max_distance = 0
            
            for direction in escape_directions:
                next_col = pacman_col + direction[0]
                next_row = pacman_row + direction[1]
                
                if not self.is_valid_position(next_col, next_row):
                    continue
                
                # Calculate total distance from all critical ghosts
                total_distance = 0
                for cg in critical_ghosts:
                    gx, gy = cg['position']
                    dist = abs(next_row - gx) + abs(next_col - gy)
                    total_distance += dist
                
                if total_distance > max_distance:
                    max_distance = total_distance
                    best_escape = direction
            
            if best_escape:
                print(f"🚨 EMERGENCY: {len(critical_ghosts)} ma va chạm, thoát ngay!")
                self.pacman_next_direction = best_escape
                return
            else:
                print("🚨 EMERGENCY: Không tìm được lối thoát!")
                return

        # Khởi tạo biến cho hệ thống né ma cải tiến
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
        
        # Biến mới cho hệ thống né ma trên đường đi tới goal
        if not hasattr(self, 'path_avoidance_mode'):
            self.path_avoidance_mode = False
        if not hasattr(self, 'path_avoidance_start_time'):
            self.path_avoidance_start_time = 0
        if not hasattr(self, 'path_avoidance_direction'):
            self.path_avoidance_direction = None
        if not hasattr(self, 'original_goal_path'):
            self.original_goal_path = []
        if not hasattr(self, 'temporary_avoidance_target'):
            self.temporary_avoidance_target = None

        # Decrease cooldown
        if self.goal_cooldown > 0:
            self.goal_cooldown -= 1

        current_time = pygame.time.get_ticks()

        # KIỂM TRA MA TRÊN ĐƯỜNG ĐI TỚI GOAL - Tính năng mới
        if self.current_goal and not self.pacman_ai.path_avoidance_mode and not getattr(self.pacman_ai, 'escape_mode', False):
            has_ghost_on_path, ghost_pos, ghost_distance = self.pacman_ai.check_ghost_on_path_to_goal()
            
            if has_ghost_on_path and ghost_distance <= 6:  # Ma trong phạm vi 6 ô trên path
                print(f"Ma gần đường đi! Khoảng cách: {ghost_distance}")
                
                # Tìm ngã rẽ gần nhất để tránh
                avoidance_direction = self.pacman_ai.find_nearest_turn_from_path()
                
                if avoidance_direction:
                    # Bắt đầu chế độ né ma tạm thời
                    self.pacman_ai.start_path_avoidance(avoidance_direction)
                    self.pacman_next_direction = avoidance_direction
                    return
                else:
                    # Nếu không tìm được ngã rẽ, dùng emergency avoidance
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=4)
                    if nearby_ghosts and self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                        return

        # KIỂM TRA QUAY LẠI ĐƯỜNG ĐI GỐC
        if self.pacman_ai.path_avoidance_mode and self.pacman_ai.should_return_to_original_path():
            self.pacman_ai.path_avoidance_mode = False
            self.pacman_ai.path_avoidance_start_time = 0
            self.pacman_ai.path_avoidance_direction = None
            
            # Khôi phục đường đi gốc
            if hasattr(self.pacman_ai, 'original_goal_path') and self.pacman_ai.original_goal_path:
                self.auto_path = self.pacman_ai.original_goal_path.copy()
                print("Quay lại đường gốc")
            
            # Tính toán lại đường đi nếu cần
            if self.current_goal:
                self.calculate_path_to_goal()

        # XỬ LÝ TRONG CHẾ ĐỘ NÉ MA TREN ĐƯỜNG ĐI
        if self.pacman_ai.path_avoidance_mode:
            # Tiếp tục di chuyển theo hướng né ma
            if self.pacman_ai.path_avoidance_direction:
                pacman_row, pacman_col = int(self.pacman_pos[1]), int(self.pacman_pos[0])
                next_col = pacman_col + self.pacman_ai.path_avoidance_direction[0]
                next_row = pacman_row + self.pacman_ai.path_avoidance_direction[1]
                
                # Kiểm tra có thể tiếp tục đi theo hướng này không
                if self.is_valid_position(next_col, next_row):
                    self.pacman_next_direction = self.pacman_ai.path_avoidance_direction
                    return
                else:
                    # Gặp tường, tìm hướng khác
                    alternative_directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    for alt_dir in alternative_directions:
                        alt_col = pacman_col + alt_dir[0]
                        alt_row = pacman_row + alt_dir[1]
                        if self.is_valid_position(alt_col, alt_row):
                            self.pacman_ai.path_avoidance_direction = alt_dir
                            self.pacman_next_direction = alt_dir
                            return

        # Initialize nearby_ghosts và ghost checking
        nearby_ghosts = []
        
        # Throttle ghost checking to reduce computational load (check every 150ms instead of 60ms)  
        should_check_ghosts = (current_time - self.last_ghost_check) > 150
        if should_check_ghosts:
            self.last_ghost_check = current_time
            # Kiểm tra ghosts trong bán kính 4 ô theo yêu cầu
            nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=4)

        # ESCAPE MODE: Kiểm tra nếu đang trong chế độ thoát hiểm
        if getattr(self.pacman_ai, 'escape_mode', False):
            self.pacman_ai.escape_steps += 1
            
            # Giảm thời gian escape để Pacman không bị kẹt lâu
            max_escape_steps = getattr(self.pacman_ai, 'min_escape_distance', 3)  # Mặc định 3 bước
            
            # CHECK COMMIT TIME - Phải commit đủ lâu trước khi có thể thoát escape
            escape_commit_time = getattr(self.pacman_ai, 'escape_commit_time', 0)
            min_escape_duration = getattr(self.pacman_ai, 'min_escape_duration', 800)
            time_in_escape = current_time - escape_commit_time
            
            # Kiểm tra xem đã đi đủ xa chưa hoặc quá lâu VÀ đã commit đủ thời gian
            if self.pacman_ai.escape_steps >= max_escape_steps and time_in_escape >= min_escape_duration:
                # Kiểm tra xem có ghost nào ở gần không
                if should_check_ghosts:
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=4)
                if not nearby_ghosts or self.pacman_ai.escape_steps >= max_escape_steps * 2:  # Giảm multiplier để thoát nhanh hơn
                    # An toàn hoặc quá lâu, thoát escape mode
                    escape_success = not nearby_ghosts  # Success if no ghosts nearby
                    escape_duration = int(time_in_escape)
                    
                    # Determine threat level based on original trigger
                    threat_level = 'CRITICAL' if max_escape_steps >= 6 else ('HIGH' if max_escape_steps >= 4 else 'MODERATE')
                    
                    # LOG escape attempt to visualizer
                    if hasattr(self, 'visualizer') and self.visualizer:
                        self.visualizer.log_escape_attempt(escape_success, escape_duration, threat_level)
                    
                    self.pacman_ai.escape_mode = False
                    self.pacman_ai.escape_steps = 0
                    print(f"✅ Thoát escape mode sau {time_in_escape}ms ({self.pacman_ai.escape_steps} steps)")
                    
                    # Tìm đường thay thế đến goal (không spam log)
                    if not self.find_alternative_path_to_goal():
                        # Nếu không tìm được đường thay thế, tìm goal mới
                        self.find_simple_goal()
                        if self.current_goal:
                            self.calculate_path_to_goal()
                else:
                    # Vẫn có ghost gần nhưng không in quá nhiều log
                    pass
            else:
                # Kiểm tra ghost ít thường xuyên trong escape mode
                if should_check_ghosts:
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=4)  # Tăng từ 2 lên 4
            
            # Trong escape mode, tiếp tục di chuyển theo hướng hiện tại
            if nearby_ghosts:
                min_distance = min(d for _, d in nearby_ghosts)
                if min_distance <= 1:  # Chỉ khi CỰC gần mới emergency
                    # Add emergency throttling to prevent spam
                    if not hasattr(self, 'last_emergency_call'):
                        self.last_emergency_call = 0
                    if (current_time - self.last_emergency_call) >= 100:  # 100ms cooldown for emergency
                        if self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                            self.last_emergency_call = current_time
                            return

        # GHOST AVOIDANCE: Chỉ kiểm tra khi cần thiết
        if nearby_ghosts:
            min_distance = min(d for _, d in nearby_ghosts)
            # Chỉ in log khi thực sự rất nguy hiểm - comment để game mượt
            # if min_distance <= 2:
            #     print(f"GHOST ALERT! Distance: {min_distance}")
            
            # PRIORITY 1: Emergency avoidance khi ghost gần (trong 4 ô)
            if min_distance <= 4:  # Phạm vi phát hiện 4 ô theo yêu cầu
                # Xử lý khẩn cấp: ưu tiên ngã rẽ, tránh quay đầu liên tục
                if self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                    return  # Đã xử lý thành công, thoát ngay
                
                # PRIORITY 2: Complex avoidance chỉ khi ghost RẤT gần
                if min_distance <= 2 or self.ghost_avoidance_active:  # Giảm từ 3 xuống 2
                    if not self.ghost_avoidance_active:
                        self.ghost_avoidance_active = True
                        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                          if not g.get('scared', False)]

                        # Chỉ in log khi kích hoạt lần đầu
                        print("🚨 Tránh ma!")
                        self.pacman_ai.find_fallback_target(pacman_pos, ghost_positions)
                    
                    # Giảm tần suất update để tránh lag và spam
                    elif self.continuous_avoidance_count % 10 == 0:  # Từ 5 lên 10 lần để ít spam hơn
                        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                          if not g.get('scared', False)]
                        # Không print log nữa để tránh spam
                        self.pacman_ai.find_fallback_target(pacman_pos, ghost_positions)
            else:
                # Không có ghost ở gần, reset counter và tắt chế độ avoidance  
                if self.ghost_avoidance_active or self.continuous_avoidance_count > 0:
                    self.ghost_avoidance_active = False
                    self.continuous_avoidance_count = 0
                    self.auto_path = []  # Xóa đường đi avoidance cũ
                    print("An toàn - về mục tiêu")

        # Nếu đang trong chế độ ghost avoidance phức tạp, kiểm tra trạng thái
        if self.ghost_avoidance_active:
            nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=5)  # Chỉ tăng lên 5 cho safe zone check
            if not nearby_ghosts:
                # Đã an toàn (ma đi xa >6 ô), quay lại goal chính
                self.ghost_avoidance_active = False
                self.goal_locked = False  # Cho phép tìm goal mới
                self.auto_path = []  # Xóa đường đi avoidance cũ
                self.continuous_avoidance_count = 0
                print("Ma đi xa, tiếp tục")

        # Kiểm tra xem đã đạt đến target an toàn chưa
        if self.ghost_avoidance_active and self.auto_target:
            pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
            if pacman_pos == self.auto_target:
                # Đã đạt đến vị trí an toàn
                self.ghost_avoidance_active = False
                self.goal_locked = False
                self.auto_path = []  # Xóa đường đi avoidance cũ
                self.continuous_avoidance_count = 0
                print("An toàn, tìm đường mới")

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
            # Nếu đang trong chế độ avoidance, ưu tiên auto_path với improved following
            if hasattr(self, 'auto_path') and self.auto_path and len(self.auto_path) > 1:
                pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
                current_pos = (pacman_row, pacman_col)
                
                # Cải thiện path following - tìm điểm gần nhất trong path thay vì exact match
                best_index = -1
                min_distance = float('inf')
                
                for i, path_pos in enumerate(self.auto_path):
                    dist = abs(current_pos[0] - path_pos[0]) + abs(current_pos[1] - path_pos[1])
                    if dist < min_distance:
                        min_distance = dist
                        best_index = i
                
                # Nếu tìm được vị trí gần nhất trong path
                if best_index >= 0 and best_index + 1 < len(self.auto_path):
                    # Nếu quá xa path hiện tại, nhảy đến điểm gần nhất
                    if min_distance > 2:
                        next_pos = self.auto_path[best_index]
                    else:
                        next_pos = self.auto_path[best_index + 1]
                    
                    direction = [next_pos[1] - pacman_col, next_pos[0] - pacman_row]
                    
                    # Đảm bảo direction hợp lệ (chỉ di chuyển 1 ô mỗi lần)
                    if abs(direction[0]) <= 1 and abs(direction[1]) <= 1:
                        self.pacman_next_direction = direction
                        return
                
                # Fallback: nếu path không hợp lệ, tính toán lại
                print("Tính lại đường đi...")
                pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                  if not g.get('scared', False)]
                self.pacman_ai.find_fallback_target(pacman_pos, ghost_positions)

    def find_alternative_path_to_goal(self):
        """ENHANCED Tìm đường khác đến goal khi đường hiện tại không an toàn - multiple safety algorithms"""
        if not self.current_goal:
            return False
            
        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))  # (row, col)
        goal_pos = self.current_goal
        
        print(f"Tìm đường khác từ {pacman_pos} → {goal_pos}")
        
        # Lấy ghost positions và directions để predict movement
        ghost_positions = []
        ghost_data = []
        for g in self.ghosts:
            if not g.get('scared', False):
                ghost_pos = (int(g['pos'][1]), int(g['pos'][0]))
                ghost_positions.append(ghost_pos)
                ghost_data.append({
                    'pos': ghost_pos,
                    'direction': g.get('direction', [0, 0]),
                    'speed': 1  # Assume 1 block per step
                })
        
        # Try multiple pathfinding strategies, ordered by safety preference
        strategies = [
            ("max_safety", 8),    # Maximum avoidance radius
            ("moderate_safety", 6), # Moderate avoidance  
            ("min_safety", 4),    # Minimum viable avoidance
            ("emergency", 2)      # Emergency path
        ]
        
        for strategy_name, avoidance_radius in strategies:
            try:
                print(f"Thử chiến lược '{strategy_name}' với radius {avoidance_radius}")
                
                # Use enhanced ghost avoidance pathfinding
                path, distance = self.dijkstra.shortest_path_with_ghost_avoidance(
                    pacman_pos, goal_pos, ghost_positions, 
                    avoidance_radius=avoidance_radius
                )
                
                if path and len(path) > 1:
                    # ADDITIONAL SAFETY CHECK: Validate path doesn't go through predicted ghost positions
                    if self._validate_path_against_predicted_ghosts(path, ghost_data):
                        self.auto_path = path
                        self.auto_target = goal_pos
                        print(f"✅ {strategy_name}: {len(path)} bước")
                        return True
                    else:
                        print(f"❌ {strategy_name} bị ma chặn")
                        continue
                        
            except Exception as e:
                print(f"Lỗi với chiến lược {strategy_name}: {e}")
                continue
        
        print("❌ Không tìm được đường an toàn")
        return False
    
    def _validate_path_against_predicted_ghosts(self, path, ghost_data):
        """Validate that path doesn't intersect with predicted ghost movements"""
        if not path or len(path) <= 1:
            return False
            
        # Predict ghost positions for next few steps
        max_prediction_steps = min(10, len(path))
        
        for step in range(max_prediction_steps):
            if step >= len(path):
                break
                
            path_pos = path[step]
            
            # Check against each ghost's predicted position at this step
            for ghost in ghost_data:
                ghost_pos = ghost['pos']
                ghost_dir = ghost['direction']
                ghost_speed = ghost['speed']
                
                # Predict ghost position at this step
                predicted_ghost_row = ghost_pos[0] + (ghost_dir[1] * step * ghost_speed)
                predicted_ghost_col = ghost_pos[1] + (ghost_dir[0] * step * ghost_speed)
                predicted_ghost_pos = (predicted_ghost_row, predicted_ghost_col)
                
                # Check if path position conflicts with predicted ghost position
                if path_pos == predicted_ghost_pos:
                    print(f"⚠️  Path position {path_pos} conflicts with predicted ghost at step {step}")
                    return False
                
                # Check if too close (adjacent)
                distance = abs(path_pos[0] - predicted_ghost_pos[0]) + abs(path_pos[1] - predicted_ghost_pos[1])
                if distance <= 1:
                    print(f"⚠️  Path too close to predicted ghost at step {step}: distance {distance}")
                    return False
        
        return True

    def find_goal_first(self):
        """GOAL-ONLY selection - Chỉ đi đến đích, không ăn dots/pellets"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])

        # STRATEGY: Chỉ tập trung vào goal, không ăn dots/pellets
        # Ưu tiên: Exit gate ONLY

        # 1. EXIT GATE ONLY - Chỉ đi đến exit gate
        if hasattr(self, 'exit_gate'):
            self.current_goal = self.exit_gate
            # print(f"GOAL-ONLY: Exit gate at {self.exit_gate}")
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
                        # print(f" GOAL-ONLY: Created exit gate at {self.exit_gate}")
                        return

        # 3. Fallback: goal ở center nếu không tìm được gì
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        if self.is_valid_position(center_col, center_row):
            self.current_goal = (center_row, center_col)
            # print(f" GOAL-ONLY: Center goal at {self.current_goal}")
        else:
            self.current_goal = None
            # print(" GOAL-ONLY: No valid goal found")

    def move_goal_focused(self):
        """GOAL-FOCUSED movement - Chỉ tập trung vào goal, không ăn dots ngẫu nhiên"""
        if not self.current_goal:
            return

        goal_row, goal_col = self.current_goal
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))

        # Check if goal reached
        distance_to_goal = abs(pacman_row - goal_row) + abs(pacman_col - goal_col)
        if distance_to_goal < 1:
            print(f"Đến mục tiêu! Khoảng cách: {distance_to_goal}")
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
                    # print(f"Following shortest path: {direction}")
                    return
            except ValueError:
                # Không tìm thấy vị trí hiện tại trong path, tính toán lại
                # print("Current position not in shortest path, recalculating...")
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

        if hasattr(self, 'exit_gate') and self.exit_gate:
            self.current_goal = self.exit_gate
            print(f"Exit Gate: {self.exit_gate}")
        else:
            self.current_goal = None
            print("Không có exit gate")

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
        print("Thử đường trực tiếp")
        
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
        
        # Movement debug (silent)
        # print(f"Pacman at ({pacman_row}, {pacman_col}) → Goal at {self.current_goal}")
        
        # Check if goal reached
        if abs(pacman_row - goal_row) < 1 and abs(pacman_col - goal_col) < 1:
            print("Mục tiêu đạt được!")
            self.goal_locked = False
            self.current_goal = None
            self.goal_cooldown = 10  # Short cooldown before next goal
            return
            
        # Use BFS to find path
        direction = self.find_path_to_goal((pacman_col, pacman_row), (goal_col, goal_row))
        
        if direction:
            print(f"Tìm được đường! Di chuyển: {direction}")
            self.pacman_next_direction = direction
        else:
            print(f"Không tìm được đường đến {self.current_goal}")
            # If no path, try random valid move
            possible_dirs = [[1,0], [-1,0], [0,1], [0,-1]]
            for test_dir in possible_dirs:
                test_col = pacman_col + test_dir[0]
                test_row = pacman_row + test_dir[1]
                if self.is_valid_position(test_col, test_row):
                    self.pacman_next_direction = test_dir
                    print(f" Random move: {test_dir}")
                    break

    def calculate_path_to_goal(self):
        """Calculate shortest path to current goal"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)
        
        path, distance = self.dijkstra.shortest_path(pacman_pos, self.current_goal)
        if path:
            self.path_to_goal = path
            # print(f"Path calculated: {len(path)} steps to goal {self.current_goal}")  # Reduced verbosity
        else:
            # print(" No path to goal found")  # Reduced verbosity
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
            print("Không tìm được hướng an toàn!")

    def move_toward_goal(self):
        """Move toward current goal using calculated path"""
        if not self.path_to_goal or len(self.path_to_goal) <= 1:
            print("Không có đường - đứng im")
            return
        
        # Clean up path - remove current position if we're already there
        current_col, current_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        
        # Remove waypoints that we've already reached
        while (self.path_to_goal and 
               len(self.path_to_goal) > 1 and  # Keep at least one waypoint (the goal)
               abs(current_row - self.path_to_goal[0][0]) < 0.8 and 
               abs(current_col - self.path_to_goal[0][1]) < 0.8):
            self.path_to_goal.pop(0)
            # print(f"Reached waypoint, remaining path: {len(self.path_to_goal)} steps")  # Reduced verbosity
        
        if not self.path_to_goal:
            # print("Goal reached!")  # Reduced verbosity
            return
            
        # Get next target position from path
        next_row, next_col = self.path_to_goal[0]  # Always use first position in path
        
        # print(f"Current: ({current_row}, {current_col}) → Target: ({next_row}, {next_col})")  # Reduced verbosity
        
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
            # Movement debug (silent)
            # print(f"Moving {['left', 'right'][direction[0]] if direction[0] != 0 else ['up', 'down'][direction[1]]}")
        else:
            # print(f"Already at target position")  # Reduced verbosity
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

    def can_pacman_pass_through_ghost(self, ghost):
        """
        Kiểm tra Pacman có thể đi xuyên qua ghost không
        Trả về True nếu ghost đã bị ăn (chỉ còn eyes)
        """
        return ghost.get('eaten', False)

    def is_ghost_just_eyes(self, ghost):
        """
        Kiểm tra ghost có chỉ còn là eyes không (đã bị ăn)
        """
        return ghost.get('eaten', False)

    def is_valid_position_ignore_eyes(self, col, row):
        """
        Kiểm tra vị trí có hợp lệ không, bỏ qua ghost eyes (chỉ còn mắt)
        Ghost eyes không cản trở Pacman di chuyển
        """
        # Kiểm tra biên và tường như bình thường
        check_col, check_row = int(round(col)), int(round(row))
        
        if not (0 <= check_row < self.maze_gen.height and 0 <= check_col < self.maze_gen.width):
            return False
            
        # Must be open path (black cell, not blue wall)
        if self.maze[check_row, check_col] != 0:
            return False
        
        # Kiểm tra ghost - chỉ cản trở nếu ghost KHÔNG phải là eyes
        for ghost in self.ghosts:
            ghost_col = int(round(ghost['pos'][0]))
            ghost_row = int(round(ghost['pos'][1]))
            
            # Nếu ghost ở vị trí này
            if ghost_col == check_col and ghost_row == check_row:
                # Chỉ cản trở nếu ghost KHÔNG phải là eyes (chưa bị ăn)
                if not self.can_pacman_pass_through_ghost(ghost):
                    return False
        
        return True

    def check_collisions(self):
        """Optimized collision detection with spatial partitioning"""
        pacman_center = (self.pacman_pos[0] * self.cell_size + self.cell_size // 2,
                        self.pacman_pos[1] * self.cell_size + self.cell_size // 2)

        # OPTIMIZED: Only check dots within reasonable distance (2 cells = 60 pixels)
        max_check_distance = config.COLLISION_CHECK_DISTANCE if hasattr(config, 'COLLISION_CHECK_DISTANCE') else 60
        
        # Reset collision counter
        self.collision_checks_per_frame = 0
        
        # Check dots with early distance filtering
        for dot in self.dots[:]:
            # Quick distance check first (cheaper than hypot)
            dx = abs(pacman_center[0] - dot[0])
            dy = abs(pacman_center[1] - dot[1])
            
            # Skip if obviously too far (Manhattan distance check) - NO INCREMENT HERE
            if dx > max_check_distance or dy > max_check_distance:
                continue
            
            # Only count if we actually do the expensive calculation
            self.collision_checks_per_frame += 1
                
            # Only calculate exact distance for nearby dots
            distance = math.hypot(dx, dy)
            if distance < 10:
                self.dots.remove(dot)
                self.score += 10

        # Check power pellets with same optimization
        for pellet in self.power_pellets[:]:
            # Quick distance check first
            dx = abs(pacman_center[0] - pellet[0])
            dy = abs(pacman_center[1] - pellet[1])
            
            # Skip if obviously too far - NO INCREMENT HERE
            if dx > max_check_distance or dy > max_check_distance:
                continue
            
            # Only count if we actually do the expensive calculation
            self.collision_checks_per_frame += 1
                
            # Only calculate exact distance for nearby pellets
            distance = math.hypot(dx, dy)
            if distance < 10:
                self.power_pellets.remove(pellet)
                self.score += 50

                # Play wakawaka sound for power pellet
                if hasattr(self, 'wakawaka_sound') and self.wakawaka_sound:
                    self.wakawaka_sound.play()

                # Set power mode for 10 seconds
                self.power_mode_end_time = pygame.time.get_ticks() + 5000  # 10 seconds

                # Make all ghosts frightened for 10 seconds
                for ghost in self.ghosts:
                    ghost['scared'] = True
                    ghost['scared_timer'] = 600  # 10 seconds at 60 FPS

        # Check bombs collision - lose life if hit (less frequent, so keep as is)
        for bomb in self.bombs[:]:
            distance = math.hypot(pacman_center[0] - bomb[0], pacman_center[1] - bomb[1])
            if distance < 12:  # Bomb collision distance
                print("Trúng bom! Mất mạng!")
                self.lives -= 1
                self.last_death_cause = "Bom nổ"  # Track death cause
                if self.lives <= 0:
                    self.death_time = pygame.time.get_ticks()  # Save death time
                    self.game_state = "game_over"
                    # Set motivational message only once when game over
                    if not self.game_over_message:
                        motivational_messages = [
                            "🌟 Đừng bỏ cuộc, hãy thử lại!",
                            "💪 Thất bại là mẹ của thành công!",
                            "🎯 Lần sau sẽ tốt hơn!",
                            "🚀 Hãy học hỏi và phát triển!",
                            "✨ Every ending is a new beginning!",
                            "🔥 Persistence beats resistance!",
                            "🌈 The comeback is always stronger!",
                            "⭐ You're closer than you think!"
                        ]
                        self.game_over_message = random.choice(motivational_messages)
                else:
                    self.reset_positions()
                break  # Only lose one life per collision check

        # CHỈ KIỂM TRA: Ghosts collision - IMPROVED with larger detection radius
        for ghost in self.ghosts:
            # Skip if ghost is already eaten in this frame
            if ghost.get('eaten', False):
                continue
                
            ghost_center = (ghost['pos'][0] * self.cell_size + self.cell_size // 2,
                          ghost['pos'][1] * self.cell_size + self.cell_size // 2)
            distance = math.hypot(pacman_center[0] - ghost_center[0],
                                pacman_center[1] - ghost_center[1])
            if distance < 20:  # Increased from 15 to 20 for better detection
                # print(f"Ghost collision detected! Ghost: {ghost['name']}, Scared: {ghost.get('scared', False)}, Distance: {distance:.1f}")
                if ghost.get('scared', False):
                    # Eat scared ghost for points
                    self.score += 200
                    print(f"Ate {ghost['name']} ghost! +200 points")
                    
                    # Play wakawaka sound for eating ghost
                    if hasattr(self, 'wakawaka_sound') and self.wakawaka_sound:
                        self.wakawaka_sound.play()
                    
                    # Set ghost to eaten state (only eyes visible)
                    ghost['eaten'] = True
                    ghost['scared'] = False
                    ghost['scared_timer'] = 0
                    # Ghost will move back to spawn as eyes
                    # IMPORTANT: Break after eating one ghost to avoid multiple collisions in same frame
                    break
                else:
                    # Normal ghost collision - lose life but keep score
                    print(f"Pacman touched a normal ghost! Lost a life. Lives remaining: {self.lives - 1}")
                    self.lives -= 1
                    self.last_death_cause = f"Ma {ghost['name']}"  # Track death cause with ghost name
                    
                    # Log death to visualizer
                    if self.visualizer and hasattr(self, 'pacman_ai'):
                        try:
                            ghost_data = self.visualizer._collect_ghost_data()
                            decisions = self.visualizer._collect_decision_data(self.pacman_ai)
                            self.visualizer.log_death(ghost_data, decisions)
                        except Exception as e:
                            pass  # Silent fail
                    
                    if self.lives <= 0:
                        self.death_time = pygame.time.get_ticks()  # Save death time
                        self.game_state = "game_over"
                        print("Game Over! No lives remaining.")
                        # Set motivational message only once when game over
                        if not self.game_over_message:
                            motivational_messages = [
                                "🌟 Đừng bỏ cuộc, hãy thử lại!",
                                "💪 Thất bại là mẹ của thành công!",
                                "🎯 Lần sau sẽ tốt hơn!",
                                "🚀 Hãy học hỏi và phát triển!",
                                "✨ Every ending is a new beginning!",
                                "🔥 Persistence beats resistance!",
                                "🌈 The comeback is always stronger!",
                                "⭐ You're closer than you think!"
                            ]
                            self.game_over_message = random.choice(motivational_messages)
                    else:
                        # Reset positions but keep score and game state
                        self.reset_positions_after_death()
                    # IMPORTANT: Break after losing life to avoid multiple deaths in same frame
                    break

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
            print(" Could not find valid ghost start position, using Pacman position")
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
        print("Resetting positions after death...")

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
            print(" Could not find valid ghost start position, using Pacman position")
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

        print(f"Positions reset - Pacman at start, ghosts repositioned. Score: {self.score}, Lives: {self.lives}")

    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # print(f"Key pressed: {pygame.key.name(event.key)}")
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Visualizer controls
                elif event.key == pygame.K_v:
                    if self.visualizer:
                        self.visualizer.toggle_visualization()
                    else:
                        print("⚠️  Visualizer not available")
                
                elif event.key == pygame.K_b:
                    if self.visualizer:
                        self.visualizer.print_real_time_analysis()
                    else:
                        print("⚠️  Visualizer not available")
                
                elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if self.visualizer:
                        self.visualizer.save_analysis_report()
                    else:
                        print("⚠️  Visualizer not available")
                
                elif event.key == pygame.K_p:
                    self.game_state = "paused" if self.game_state == "playing" else "playing"
                elif event.key == pygame.K_a:
                    self.toggle_auto_mode()
                elif event.key == pygame.K_h:
                    self.show_shortest_path = not self.show_shortest_path
                    if self.show_shortest_path:
                        # Luôn hiển thị đường đi đến EXIT GATE (goal chính)
                        self.calculate_hint_path_to_exit()
                        # print("Hint path to EXIT: ON (Press H to toggle)")
                    else:
                        self.shortest_path = []
                        # print("Hint path visualization: OFF")
                elif event.key == pygame.K_f:
                    self.show_fps_info = not self.show_fps_info
                    print(f"FPS info: {'ON' if self.show_fps_info else 'OFF'}")
                elif event.key == pygame.K_d:
                    config.ENABLE_DYNAMIC_SPEED = not config.ENABLE_DYNAMIC_SPEED
                    status = "ON" if config.ENABLE_DYNAMIC_SPEED else "OFF"
                    print(f"Dynamic speed control: {status}")
                elif event.key == pygame.K_e:
                    self.pacman_ai.set_escape_target()
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
        print("RESTARTING GAME - Resetting all states...")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None

        # Reset game over message for next game
        self.game_over_message = None
        self.last_death_cause = None
        self.death_time = None  # Reset death time

        # Remove user auto flag to ensure manual control after restart
        if hasattr(self, '_user_enabled_auto'):
            delattr(self, '_user_enabled_auto')

        # Reset Pacman properties
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = config.PACMAN_LEGACY_SPEED  # Use config value
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

        print("Generating new level...")
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
        
        # Bombs are already generated in maze generation - no need to place again
        print("Loading bombs from maze generator...")
        self.load_bombs_from_maze_generator()

        print("Creating/resetting ghosts...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("Resetting positions...")
        self.reset_positions()

        print("Game restarted successfully - Auto mode: OFF, Manual control enabled!")

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

        print("Generating new random level...")
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
        
        # Bombs are already generated in maze generation - no need to place again
        print("Loading bombs from maze generator...")
        self.load_bombs_from_maze_generator()

        print("Creating/resetting ghosts...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("Resetting positions...")
        self.reset_positions()

        print("New game created successfully!")

    def update(self):
        """Update game state with FPS-independent movement"""
        current_time = pygame.time.get_ticks()
        raw_delta_time = (current_time - self.last_update) / 1000.0  # Convert to seconds
        
        # Cap delta time to prevent huge jumps when paused/lagging
        self.delta_time = min(raw_delta_time, self.max_delta_time)
        self.last_update = current_time
        
        # Track FPS for performance monitoring
        if raw_delta_time > 0:
            current_fps = 1.0 / raw_delta_time
            self.fps_history.append(current_fps)
            if len(self.fps_history) > 60:  # Keep last 60 frames
                self.fps_history.pop(0)
        
        # Update visualizer with current AI state
        if self.visualizer and hasattr(self, 'pacman_ai'):
            try:
                self.visualizer.update(self.pacman_ai)
            except Exception as e:
                pass  # Silent fail to not disrupt gameplay

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
            
            # Update ghost scared timers BEFORE collision check
            for ghost in self.ghosts:
                if ghost.get('scared', False):
                    ghost['scared_timer'] -= 1
                    if ghost['scared_timer'] <= 0:
                        ghost['scared'] = False
                        ghost['scared_timer'] = 0
                        # print(f"{ghost['name']} ghost is no longer scared!")
            
            # Check collisions AFTER timer updates
            self.check_collisions()

            # Update shortest path visualization (recalculate less frequently to reduce lag)
            current_time = pygame.time.get_ticks()
            # Update hint path periodically when showing it
            if self.show_shortest_path and current_time - self.last_path_calculation > 1000:  # 1000ms instead of 500ms
                self.calculate_hint_path_to_exit()  # Use hint path function
                self.last_path_calculation = current_time

            # Animate Pacman mouth - faster animation for snappier feel
            self.animation_timer += 1
            if self.animation_timer >= 8:  #Faster animation pacman mouth
                self.pacman_mouth_open = not self.pacman_mouth_open
                self.animation_timer = 0

    def draw_ghost_return_paths(self):
        """Draw the return paths for eaten ghosts (eyes only)"""
        for ghost in self.ghosts:
            if ghost.get('eaten', False) and hasattr(ghost, 'return_path') and ghost['return_path']:
                path = ghost['return_path']
                
                # Draw path with dotted white line
                for i, (row, col) in enumerate(path):
                    center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
                    
                    # Draw smaller dots for ghost return path
                    if i % 2 == 0:  # Draw every other dot for dotted effect
                        pygame.draw.circle(self.screen, (200, 200, 200), center, 2)  # Light gray
                
                # Highlight current target waypoint
                if hasattr(ghost, 'path_index') and ghost['path_index'] < len(path):
                    target_waypoint = path[ghost['path_index']]
                    target_row, target_col = target_waypoint
                    target_center = ((target_col + 0.5) * self.cell_size, (target_row + 0.5) * self.cell_size)
                    pygame.draw.circle(self.screen, (255, 255, 255), target_center, 4)  # White target

    def draw(self):
        """Draw everything"""
        self.screen.fill(self.BLACK)
        self.draw_maze()
        self.draw_dots_and_pellets()
        self.draw_bombs()
        self.draw_exit_gate()  # Draw exit gate
        self.draw_shortest_path()  # Draw shortest path to goal
        self.draw_ghost_return_paths()  # Draw return paths for eaten ghosts
        # self.draw_auto_path()  #  REMOVED: Xóa tính năng show path
        self.draw_pacman()
        self.draw_ghosts()
        self.draw_ui()
        
        # Draw FPS info if enabled
        if self.show_fps_info:
            self.draw_fps_info()
        
        # Render visualizer overlay (if enabled)
        if self.visualizer:
            try:
                self.visualizer.render(self.screen, self.cell_size)
            except Exception as e:
                pass  # Silent fail to not disrupt gameplay
        
        # Draw game state notifications LAST (on top of everything)
        if self.game_state == "game_over":
            self.draw_game_over_notification()
        elif self.game_state == "level_complete":
            self.draw_win_notification()
            
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
        """Main game loop with configurable FPS"""
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(self.target_fps)  # Use configurable FPS
        except KeyboardInterrupt:
            print("\nGame interrupted by user")
        except Exception as e:
            print(f" Error during game execution: {e}")
        finally:
            # Proper cleanup
            print("Cleaning up resources...")
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
            # Use round() for accurate conversion from center position
            grid_col = round(bomb_x / self.cell_size - 0.5)
            grid_row = round(bomb_y / self.cell_size - 0.5)
            bomb_grid.add((grid_row, grid_col))
        return bomb_grid

if __name__ == "__main__":
    game = PacmanGame()
    game.run()

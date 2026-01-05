import pygame
import sys
import random
import math
import signal
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm
from astar_algorithm import AStarAlgorithm
from pacman_ai import PacmanAI
from ghost_avoidance_visualizer import GhostAvoidanceVisualizer
import config

class PacmanGame:
    def __init__(self, width=50, height=28, cell_size=30):
        # Cấu hình mixer trước khi init để giảm rè/độ trễ âm thanh
        # NOTE: buffer quá nhỏ dễ gây rè/giật khi game nặng CPU, nên cho phép cấu hình qua config.
        audio_freq = getattr(config, 'AUDIO_FREQUENCY', 44100)
        audio_size = getattr(config, 'AUDIO_SIZE', -16)
        audio_channels = getattr(config, 'AUDIO_CHANNELS', 2)
        audio_buffer = getattr(config, 'AUDIO_BUFFER', 1024)
        pygame.mixer.pre_init(
            frequency=audio_freq,
            size=audio_size,
            channels=audio_channels,
            buffer=audio_buffer,
        )

        self.maze_gen = MazeGenerator(width, height, complexity=1)  # Độ phức tạp mê cung
        self.dijkstra = DijkstraAlgorithm(self.maze_gen)
        self.astar = AStarAlgorithm(self.maze_gen)
        self.cell_size = cell_size
        # Thêm chiều rộng cho panel bên phải (350px)
        self.screen_width = width * cell_size + 380
        self.screen_height = (height + 3) * cell_size  # Không gian UI chuẩn

        pygame.init()
        pygame.mixer.init()  # Khởi tạo bộ trộn âm thanh
        
        # Tải và phát nhạc mở màn
        opening_volume = getattr(config, 'OPENING_VOLUME', 0.5)
        try:
            self.opening_sound = pygame.mixer.Sound('public/opening.wav')
            self.opening_sound.set_volume(opening_volume)
            self.opening_sound.play()
        except pygame.error as e:
            print(f"Cảnh báo: Không tải được nhạc mở màn: {e}")
            self.opening_sound = None
        
        # Tải âm thanh waka-waka khi ăn
        waka_volume = getattr(config, 'WAKA_VOLUME', 0.5)
        try:
            self.wakawaka_sound = pygame.mixer.Sound('public/wakaWaka.wav')
            self.wakawaka_sound.set_volume(waka_volume)
        except pygame.error as e:
            print(f"Cảnh báo: Không tải được âm thanh waka-waka: {e}")
            self.wakawaka_sound = None

        # Dùng channel riêng + throttle để tránh overlap (nguyên nhân hay gây rè/giật)
        self.wakawaka_channel = None
        self._last_wakawaka_play_ms = 0
        self._wakawaka_min_interval_ms = getattr(config, 'WAKA_MIN_INTERVAL_MS', 90)
        try:
            if pygame.mixer.get_init():
                # Ensure there are enough channels; keep existing if already >= 8
                current_channels = pygame.mixer.get_num_channels() or 0
                if current_channels < 8:
                    pygame.mixer.set_num_channels(8)
                    current_channels = 8
                # Reserve the last channel for wakawaka
                self.wakawaka_channel = pygame.mixer.Channel(current_channels - 1)
        except Exception:
            self.wakawaka_channel = None

        # Helper: phát âm thanh ăn hạt an toàn, tránh crash nếu mixer lỗi
        def _safe_play_wakawaka():
            if not self.wakawaka_sound:
                return
            try:
                if not pygame.mixer.get_init():
                    return

                now_ms = pygame.time.get_ticks()
                if now_ms - self._last_wakawaka_play_ms < self._wakawaka_min_interval_ms:
                    return
                self._last_wakawaka_play_ms = now_ms

                if self.wakawaka_channel:
                    # Avoid stacking many plays on top of each other
                    if self.wakawaka_channel.get_busy():
                        return
                    self.wakawaka_channel.play(self.wakawaka_sound, fade_ms=10)
                else:
                    self.wakawaka_sound.play()
            except Exception as exc:
                print(f"Cảnh báo: Lỗi phát âm thanh waka-waka: {exc}")

        self.play_wakawaka = _safe_play_wakawaka
        
        # Thiết lập signal handler để thoát an toàn
        def signal_handler(signum, frame):
            print("\nNhận tín hiệu, đóng game an toàn...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Pacman AI - Trò chơi mê cung thông minh")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.large_font = pygame.font.SysFont("arial", 36, bold=True)

        # Bảng màu phong cách Pacman (Arcade cổ điển)
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.YELLOW = (255, 255, 0)
        self.BLUE = (33, 33, 222)  # Xanh arcade cổ điển
        self.LIGHT_BLUE = (33, 150, 243)  # Màu nhấn
        self.RED = (255, 0, 0)
        self.PINK = (255, 184, 255)
        self.CYAN = (0, 255, 255)
        self.ORANGE = (255, 184, 82)
        self.DARK_BLUE = (0, 0, 100)
        self.GREEN = (0, 255, 0)  # Xanh cho trạng thái bật
        self.WALL_COLOR = (33, 33, 222)  # Màu tường chính
        self.WALL_HIGHLIGHT = (82, 130, 255)  # Viền tường hiệu ứng 3D
        self.DOT_GLOW = (255, 255, 200)  # Phát sáng hạt

        # Load ghost images
        self.load_ghost_images()

        # Trạng thái game
        self.running = True
        self.game_state = "playing"  # playing, paused, game_over, level_complete
        self.score = 0
        self.high_score = 0  # Theo dõi điểm cao nhất
        self.lives = 3
        self.level = 1
        
        # Biến thống kê trạng thái trận
        self.start_time = pygame.time.get_ticks()  # Mốc thời gian bắt đầu
        self.last_death_cause = None  # Nguyên nhân lần chết gần nhất
        self.initial_dots = []  # Sẽ set sau khi đặt hạt
        self.game_over_message = None  # Lưu thông điệp động lực duy nhất

        # Thuộc tính Pacman - sẽ được cập nhật sau khi tạo mê cung
        self.pacman_pos = [14.0, 23.0]  # Vị trí tạm (float)
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.pacman_speed = config.PACMAN_LEGACY_SPEED  # Lấy từ config
        self.pacman_animation = 1
        self.pacman_mouth_open = True
        self.pacman_mouth_cycle = 0  # Chu kỳ mở miệng mượt
        
        # Hiệu ứng power pellet
        self.pellet_pulse_timer = 0
        self.pellet_pulse_size = 0

        # Generate maze
        self.generate_level()
        
        # Lấy vị trí bắt đầu Pacman từ điểm start trong mê cung (ô đen)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Đổi (row,col) sang [col,row] dạng float

        # Cổng thoát - góc đối diện vị trí start
        self.exit_gate = self.calculate_exit_gate_position()

        # Hạt nhỏ và power pellet
        self.dots = []
        self.power_pellets = []
        self.place_dots_and_pellets()

        # Bom làm chướng ngại - lấy từ maze generator (đã kiểm tra hợp lệ)
        self.bombs = []
        self.bombs_enabled = True  # Bật/tắt hiện bom và va chạm
        self.load_bombs_from_maze_generator()

        # Ma
        self.ghosts = []
        self.ghosts_enabled = True  # Bật/tắt hiện ma và va chạm
        self.create_ghosts()

        # Khởi tạo Pacman AI
        self.pacman_ai = PacmanAI(self)
        
        # Khởi tạo bộ hiển thị né ma
        try:
            self.visualizer = GhostAvoidanceVisualizer(self)
            print("Tải thành công bộ hiển thị né ma")
            print("   Nhấn 'V' để bật/tắt visualizer")
            print("   Nhấn 'B' để bật/tắt debug")
            print("   Nhấn 'SHIFT+S' để lưu báo cáo phân tích")
        except Exception as e:
            print(f"Không tải được visualizer: {e}")
            self.visualizer = None

        # Chế độ tự động cho Pacman AI - đảm bảo khởi động ở FALSE
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None
        self.auto_speed_index = config.AUTO_MODE_DEFAULT_SPEED_INDEX  # Mức tốc độ hiện tại trong auto mode

        # Biến di chuyển tập trung vào mục tiêu
        self.current_goal = None
        self.goal_locked = False
        self.goal_cooldown = 0
        self.ghost_avoidance_active = False
        self.last_ghost_check = 0
        self.last_emergency_turn = 0
        self.turn_cooldown = 0
        
        # Né ma nâng cao
        self.escape_mode = False  # Đang trong chế độ thoát hiểm
        self.escape_steps = 0     # Số bước đã di chuyển thoát hiểm
        self.min_escape_distance = 6  # Tối thiểu 6 bước trước khi quay lại
        self.original_direction = None  # Hướng đi ban đầu trước khi quay đầu

        # Hiển thị đường đi ngắn nhất
        self.show_shortest_path = False
        self.shortest_path = []
        self.last_path_calculation = 0

        # Thời gian game - di chuyển độc lập FPS
        self.target_fps = config.TARGET_FPS  # Lấy FPS cấu hình
        self.last_update = pygame.time.get_ticks()
        self.delta_time = 0  
        self.max_delta_time = config.MAX_DELTA_TIME  # Giới hạn khung hình lớn
        self.animation_timer = 0
        self.auto_update_timer = 0
        
        # Theo dõi hiệu năng
        self.fps_history = []
        self.show_fps_info = False  # Bật/tắt bằng phím F
        self.collision_checks_per_frame = 0  # Đếm kiểm tra va chạm mỗi khung

    def generate_level(self):
        """Tạo mê cung bố cục kiểu Pacman"""
        max_attempts = 10
        for attempt in range(max_attempts):
            # NOTE: generate_maze() already calls generate_bomb_positions() internally
            # So bombs are ALWAYS synchronized with the current maze attempt
            self.maze, self.start, self.goal = self.maze_gen.generate_maze()
            # Ensure start and goal are in good positions
            if self.validate_pacman_layout():
                print(f"Tạo mê cung hợp lệ ở lần thử {attempt + 1}")
                break
        else:
            print("Cảnh báo: Không tạo được mê cung phù hợp cho Pacman")

    def validate_pacman_layout(self):
        """Đảm bảo mê cung phù hợp để chơi Pacman"""
        # Check if start position is valid
        start_row, start_col = self.start
        if not (0 <= start_row < self.maze_gen.height and 0 <= start_col < self.maze_gen.width):
            return False
        if self.maze[start_row, start_col] == 1:
            return False
        return True

    def load_ghost_images(self):
        """Tải ảnh ma từ thư mục public"""
        self.ghost_images = {}
        
        # Tải ảnh ma cho từng màu (0-3)
        ghost_colors = ['0', '1', '2', '3']  # đỏ, hồng, cyan, cam
        
        for i, color in enumerate(ghost_colors):
            # Tải ảnh nhìn phải (0) và nhìn trái (1)
            try:
                self.ghost_images[f'ghost{i}_right'] = pygame.image.load(f'public/ghost{color}_0.png').convert_alpha()
                self.ghost_images[f'ghost{i}_left'] = pygame.image.load(f'public/ghost{color}_1.png').convert_alpha()
            except pygame.error as e:
                print(f"Cảnh báo: Không tải được ảnh ghost{color}: {e}")
                # Dùng hình chữ nhật màu làm dự phòng nếu không tải được ảnh
                self.ghost_images[f'ghost{i}_right'] = None
                self.ghost_images[f'ghost{i}_left'] = None
        
        # Tải ảnh ma sợ
        try:
            self.ghost_images['ghost_scared_right'] = pygame.image.load('public/ghostScared_0.png').convert_alpha()
            self.ghost_images['ghost_scared_left'] = pygame.image.load('public/ghostScared_1.png').convert_alpha()
        except pygame.error as e:
            print(f"Cảnh báo: Không tải được ảnh ma sợ: {e}")
            self.ghost_images['ghost_scared_right'] = None
            self.ghost_images['ghost_scared_left'] = None
        
        # Tải ảnh mắt (khi ma bị ăn)
        try:
            self.ghost_images['eyes_right'] = pygame.image.load('public/eyes0.png').convert_alpha()
            self.ghost_images['eyes_left'] = pygame.image.load('public/eyes1.png').convert_alpha()
        except pygame.error as e:
            print(f"Cảnh báo: Không tải được ảnh mắt ma: {e}")
            self.ghost_images['eyes_right'] = None
            self.ghost_images['eyes_left'] = None

    def calculate_exit_gate_position(self):
        """Tính vị trí cổng thoát ở góc đối diện điểm start của Pacman"""
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
        """Đặt hạt và power pellet lên mê cung"""
        self.dots = []
        self.power_pellets = []

        # Thu thập mọi vị trí hợp lệ (đường đi)
        valid_positions = []
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    # Skip start and goal positions
                    if not ((y, x) == self.start or (y, x) == self.goal):
                        valid_positions.append((x, y))

        # Chọn ngẫu nhiên vị trí đặt power pellet với ràng buộc khoảng cách tối thiểu
        power_pellet_positions = []
        min_distance = 5  # Khoảng cách tối thiểu giữa các power pellet
        max_pellets = 7  # Số power pellet tối đa
        attempts = 10
        max_attempts = 1000

        while len(power_pellet_positions) < max_pellets and attempts < max_attempts:
            attempts += 1
            # Pick a random position
            if not valid_positions:
                break

            candidate = random.choice(valid_positions)
            x, y = candidate

            # Kiểm tra vị trí này có đủ xa các power pellet đã chọn không
            is_valid = True
            for px, py in power_pellet_positions:
                distance = math.sqrt((x - px)**2 + (y - py)**2)
                if distance < min_distance:
                    is_valid = False
                    break

            if is_valid:
                power_pellet_positions.append(candidate)
                # Loại các vị trí lân cận khỏi valid_positions để tìm nhanh hơn
                valid_positions = [pos for pos in valid_positions
                                 if math.sqrt((pos[0] - x)**2 + (pos[1] - y)**2) >= min_distance]

        # Đặt hạt và power pellet
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                if self.maze[y, x] == 0:  # Open path
                    center = ((x + 0.5) * self.cell_size, (y + 0.5) * self.cell_size)

                    if (x, y) in power_pellet_positions:
                        self.power_pellets.append(center)
                    else:
                        # Đặt hạt thường khắp nơi trừ start và goal
                        if not ((y, x) == self.start or (y, x) == self.goal):
                            self.dots.append(center)
        
        # Lưu số lượng hạt ban đầu để thống kê
        self.initial_dots = self.dots.copy()

    def load_bombs_from_maze_generator(self):
        """Tải vị trí bom từ maze generator - đã được kiểm tra khi tạo mê cung"""
        self.bombs = []
        
        if not hasattr(self.maze_gen, 'bomb_positions') or not self.maze_gen.bomb_positions:
            print("Maze generator không trả về vị trí bom nào")
            return
        
        print(f"\n Đang tải {len(self.maze_gen.bomb_positions)} bom từ MazeGenerator")
        
        # QUAN TRỌNG: Xác nhận mê cung tồn tại và khớp kích thước
        if not hasattr(self, 'maze') or self.maze is None:
            print("ERROR: self.maze not initialized yet!")
            return
        
        if self.maze.shape != (self.maze_gen.height, self.maze_gen.width):
            print(f"LỖI: Kích thước mê cung không khớp! self.maze={self.maze.shape} vs maze_gen=({self.maze_gen.height}, {self.maze_gen.width})")
            return
        
        for row, col in self.maze_gen.bomb_positions:
            # Verify position is valid
            if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
                print(f"Bomb at Grid({row}, {col}) out of bounds - SKIPPED")
                continue
            
            maze_value = self.maze[row, col]
            if maze_value != 0:
                print(f"Bomb tại Grid({row}, {col}) KHÔNG nằm trên đường đi (maze[{row},{col}]={maze_value}) - BỎ QUA")
                # Trường hợp này không nên xảy ra nếu maze_generator đúng
                continue
            
            # Convert grid to pixel coordinates (center of cell)
            center_x = (col + 0.5) * self.cell_size
            center_y = (row + 0.5) * self.cell_size
            
            self.bombs.append((center_x, center_y))

    def place_bombs_OLD_DEPRECATED(self):
        """
        PHƯƠNG THỨC CŨ - ĐÃ NGỪNG DÙNG
        Giữ lại để tham khảo, KHÔNG nên sử dụng.
        Hãy dùng load_bombs_from_maze_generator() thay thế.
        """
        self.bombs = []
        
        # Thu thập mọi vị trí hợp lệ (CHỈ ô đi được) với kiểm tra SIÊU NGHIÊM NGẶT
        valid_positions = []
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                # ===== KIỂM TRA SIÊU NGHIÊM NGẶT =====
                # Bước 1: Phải trong biên
                if not (0 <= y < self.maze_gen.height and 0 <= x < self.maze_gen.width):
                    continue
                
                # Bước 2: BẮT BUỘC là 0 (đường đi) - loại bỏ mọi giá trị khác
                maze_value = self.maze[y, x]
                if maze_value != 0:
                    continue  # Skip walls (1) and any other value
                
                # Bước 3: Loại tường thêm một lần cho chắc
                if maze_value == 1:
                    continue
                    
                # Bước 4: Bỏ qua vị trí start và goal
                if (y, x) == self.start or (y, x) == self.goal:
                    continue
                
                # Bước 5: Đảm bảo cách xa start và goal tối thiểu
                start_dist = math.sqrt((x - self.start[1])**2 + (y - self.start[0])**2)
                goal_dist = math.sqrt((x - self.goal[1])**2 + (y - self.goal[0])**2)
                
                # Phải cách tối thiểu 5 ô so với start/goal (tăng từ 4)
                if start_dist <= 5 or goal_dist <= 5:
                    continue
                
                # Check 6: Removed - too restrictive
                # The surrounding_walls check below is sufficient
                
                # Bước 7: Đảm bảo vị trí không bị tường bao quanh (tránh ngõ cụt)
                surrounding_walls = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:  # Skip center cell
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                            if self.maze[ny, nx] == 1:  # Count walls
                                surrounding_walls += 1
                
                # Loại vị trí bị quá nhiều tường bao (ngõ cụt/góc chết)
                if surrounding_walls >= 6:  # Nếu có 6+/8 ô xung quanh là tường thì bỏ
                    continue
                
                # KIỂM TRA CUỐI: Chắc chắn đây là đường đi (0)
                if self.maze[y, x] == 0:
                    valid_positions.append((y, x))  # Lưu dạng (row, col)

        print(f"Tìm được {len(valid_positions)} vị trí hợp lệ để đặt bom (chỉ trên đường đi)")

        if not valid_positions:
            print("Không thể đặt bom nào - không có vị trí hợp lệ!")
            return

        # Thuật toán đặt bom với kiểm tra pathfinding nghiêm ngặt
        # Giảm số bom tối đa xuống 3 để tránh chặn đường
        bomb_positions = self.place_bombs_with_pathfinding_check(valid_positions, max_bombs=3)
        
        print(f"\n Đặt thành công {len(bomb_positions)} quả bom (đảm bảo luôn có đường đi)\n")

        # Place bombs at selected positions - with FINAL ULTRA STRICT validation
        valid_bomb_count = 0
        for row, col in bomb_positions:  # bomb_positions stores (row, col)
            # ===== FINAL ULTRA STRICT VALIDATION =====
            # Check 1: Verify bounds
            if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
                print(f"WARNING: Bom vượt biên giới tại Grid({row}, {col}) - BỎ QUA")
                continue
            
            # Check 2: Get maze value ONCE to avoid multiple array accesses
            maze_value = self.maze[row, col]
            
            # Check 3: MUST be exactly 0 (path) - reject EVERYTHING else
            if maze_value != 0:
                print(f"WARNING: Cố gắng đặt bom trên TƯỜNG tại Grid({row}, {col}) - Giá trị: {maze_value} - BỎ QUA")
                continue
            
            # Check 4: Explicitly reject walls (redundant but safe)
            if maze_value == 1:
                print(f"WARNING: Vị trí Grid({row}, {col}) là TƯỜNG (giá trị 1) - BỎ QUA")
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
                print(f"Đặt bom thành công tại Grid({row}, {col}) -> Pixel({center_x:.1f}, {center_y:.1f}) - Maze[{row},{col}]={maze_value}")
            else:
                print(f"WARNING: Không thể xác nhận Grid({row}, {col}) là đường đi - Giá trị: {maze_value} - BỎ QUA")
        
        print(f"Đặt được {valid_bomb_count}/{len(bomb_positions)} quả bom hợp lệ trên đường đi")
        
        # Debug: Verify all bombs are on paths
        self.verify_bomb_placement()

    def verify_bomb_placement(self):
        """Debug function to verify all bombs are placed correctly on paths"""
        print("\n===  KIỂM TRA CHI TIẾT VỊ TRÍ BOM ===")
        errors_found = 0
        
        for i, bomb in enumerate(self.bombs):
            # Convert bomb pixel coordinate to grid position
            # Use round() for accurate conversion from center position
            grid_col = round(bomb[0] / self.cell_size - 0.5)  # x -> col
            grid_row = round(bomb[1] / self.cell_size - 0.5)  # y -> row
            
            # Check bounds
            if not (0 <= grid_row < self.maze_gen.height and 0 <= grid_col < self.maze_gen.width):
                print(f"BOM {i+1}: VƯỢT BIÊN GIỚI! Grid({grid_row}, {grid_col}) - Pixel{bomb}")
                errors_found += 1
                continue
            
            # Get maze value
            maze_value = self.maze[grid_row, grid_col]
            
            # Verify this is a path (0)
            if maze_value == 0:
                print(f"BOM {i+1}: OK - Đặt trên đường đi Grid(row={grid_row}, col={grid_col}) - Pixel{bomb} - Maze[{grid_row},{grid_col}]={maze_value}")
            else:
                print(f"BOM {i+1}: LỖI NGHIÊM TRỌNG! Đặt trên TƯỜNG Grid(row={grid_row}, col={grid_col}) - Pixel{bomb} - Maze[{grid_row},{grid_col}]={maze_value}")
                errors_found += 1
        
        print(f"\n Tổng số bom: {len(self.bombs)}")
        print(f"{'Tất cả bom đặt đúng!' if errors_found == 0 else f'Phát hiện {errors_found} lỗi!'}")
        print("=" * 45 + "\n")

    def place_bombs_with_pathfinding_check(self, valid_positions, max_bombs=3):
        """Place bombs while ensuring path to goal ALWAYS remains available - ENHANCED"""
        selected_bombs = []
        remaining_positions = valid_positions.copy()
        random.shuffle(remaining_positions)
        
        # Kiểm tra đường đi ban đầu MULTIPLE TIMES để đảm bảo
        initial_path, initial_distance = self.dijkstra.shortest_path(self.start, self.goal)
        if not initial_path:
            print("CRITICAL: Không có đường đi ban đầu từ start đến goal!")
            return []
        
        print(f" Đường đi ban đầu: {initial_distance} bước")
        
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
            
            # Check distance from goal (must be at least 8 cells away - tăng từ 5)
            goal_dist = abs(col - self.goal[1]) + abs(row - self.goal[0])  # Manhattan distance
            if goal_dist <= 8:
                failed_positions.add(bomb_pos)
                continue
            
            # Check distance from start (must be at least 5 cells away)
            start_dist = abs(col - self.start[1]) + abs(row - self.start[0])
            if start_dist <= 5:
                failed_positions.add(bomb_pos)
                continue
            
            # Check distance from other bombs (tăng lên 6)
            too_close = any(
                abs(col - sc) + abs(row - sr) < 6  # Manhattan distance, tăng từ 5
                for sr, sc in selected_bombs
            )
            if too_close:
                failed_positions.add(bomb_pos)
                continue
            
            # Check not on critical path (TOÀN BỘ đường đi chính)
            if initial_path and (row, col) in initial_path:
                failed_positions.add(bomb_pos)
                continue
            
            # ===== CRITICAL: Test path vẫn tồn tại =====
            temp_bombs = selected_bombs + [(row, col)]
            temp_bomb_grid = set(temp_bombs)
            
            # Test primary path
            path, distance = self.dijkstra.shortest_path_with_obstacles(
                self.start, self.goal, temp_bomb_grid
            )
            
            # Path phải tồn tại và không quá dài (giới hạn chặt hơn: 1.3x)
            if not path:
                failed_positions.add(bomb_pos)
                continue
            
            if distance > initial_distance * 1.3:  # Giảm từ 1.5 xuống 1.3
                failed_positions.add(bomb_pos)
                continue
            
            # ===== FINAL VERIFICATION =====
            if self.maze[row, col] == 0:
                selected_bombs.append((row, col))
                print(f"Đặt bom #{len(selected_bombs)} tại Grid({row}, {col}) - Path: {distance} bước")
                
                # Double-check path still exists after adding
                verify_path, _ = self.dijkstra.shortest_path_with_obstacles(
                    self.start, self.goal, set(selected_bombs)
                )
                if not verify_path:
                    print(f"ROLLBACK: Bom tại Grid({row}, {col}) chặn đường!")
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
                print("CRITICAL: Final check failed - clearing all bombs!")
                return []
            print(f"Final verification: Path exists ({final_dist} bước)")
        
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
        """Đếm số tường kề vị trí (y,x)"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Lên, Xuống, Trái, Phải
        wall_count = 0
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                if self.maze[ny, nx] == 1:  # Tường
                    wall_count += 1
            else:
                # Đếm biên mê cung như tường
                wall_count += 1
        return wall_count

    def is_not_adjacent_to_wall(self, y, x):
        """Kiểm tra vị trí (y,x) không kề tường"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Lên, Xuống, Trái, Phải
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            if 0 <= ny < self.maze_gen.height and 0 <= nx < self.maze_gen.width:
                if self.maze[ny, nx] == 1:  # Tường
                    return False
        return True

    def is_at_least_distance_from_wall(self, y, x, min_distance=1):
        """Kiểm tra vị trí (y,x) cách tường tối thiểu min_distance"""
        for check_y in range(max(0, y - min_distance), min(self.maze_gen.height, y + min_distance + 1)):
            for check_x in range(max(0, x - min_distance), min(self.maze_gen.width, x + min_distance + 1)):
                if self.maze[check_y, check_x] == 1:  # Tìm thấy tường trong phạm vi
                    return False
        return True

    def select_positions_with_min_distance(self, positions, min_distance=10, max_bombs=5):
        """Chọn vị trí đảm bảo khoảng cách tối thiểu giữa các bom"""
        selected = []
        for pos in random.sample(positions, len(positions)):  # Shuffle to randomize
            if len(selected) >= max_bombs:
                break
            if all(math.sqrt((pos[0] - s[0])**2 + (pos[1] - s[1])**2) >= min_distance for s in selected):
                selected.append(pos)
        return selected

    def create_ghosts(self):
        """Tạo đúng 4 con ma với màu và hành vi khác nhau"""
        # Xóa danh sách hiện tại để tránh trùng
        self.ghosts = []
        
        ghost_colors = [self.RED, self.PINK, self.CYAN, self.ORANGE, self.YELLOW, self.BLUE]
        ghost_names = ["Blinky", "Pinky", "Inky", "Clyde"]

        # Tìm vị trí bắt đầu hợp lệ gần trung tâm
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        
        # Tìm vị trí hợp lệ xung quanh trung tâm
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)
        
        # Tạo đúng 4 con ma xuất phát từ vị trí trung tâm hợp lệ
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
        """Tìm vị trí xuất phát hợp lệ cho ma gần trung tâm"""
        # Kiểm tra trung tâm có hợp lệ không
        if (0 <= center_row < self.maze_gen.height and 
            0 <= center_col < self.maze_gen.width and
            self.maze[center_row, center_col] == 0):  # Valid path
            return (center_row, center_col)
        
        # Quét theo vòng tròn giãn dần quanh trung tâm
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
        """Draw the maze with classic arcade-style walls with 3D effect"""
        for y in range(self.maze_gen.height):
            for x in range(self.maze_gen.width):
                rect = pygame.Rect(x * self.cell_size, y * self.cell_size,
                                 self.cell_size, self.cell_size)
                if self.maze[y, x] == 1:  # Wall
                    # Check neighbors for rounded corner detection
                    has_top = y > 0 and self.maze[y-1, x] == 1
                    has_bottom = y < self.maze_gen.height-1 and self.maze[y+1, x] == 1
                    has_left = x > 0 and self.maze[y, x-1] == 1
                    has_right = x < self.maze_gen.width-1 and self.maze[y, x+1] == 1
                    
                    # Draw main wall with rounded corners
                    border_radius = 6 if not (has_top and has_bottom and has_left and has_right) else 0
                    pygame.draw.rect(self.screen, self.WALL_COLOR, rect, border_radius=border_radius)
                    
                    # Add 3D highlight effect (top-left lighter edge)
                    highlight_rect = pygame.Rect(x * self.cell_size, y * self.cell_size, 
                                                self.cell_size, self.cell_size)
                    pygame.draw.line(self.screen, self.WALL_HIGHLIGHT, 
                                   (highlight_rect.left, highlight_rect.top),
                                   (highlight_rect.right-1, highlight_rect.top), 2)
                    pygame.draw.line(self.screen, self.WALL_HIGHLIGHT,
                                   (highlight_rect.left, highlight_rect.top),
                                   (highlight_rect.left, highlight_rect.bottom-1), 2)
                    
                    # Outer glow/border for arcade feel
                    if not has_top or not has_bottom or not has_left or not has_right:
                        pygame.draw.rect(self.screen, self.LIGHT_BLUE, rect, 1, border_radius=border_radius)
                else:  # Path
                    pygame.draw.rect(self.screen, self.BLACK, rect)

    def draw_dots_and_pellets(self):
        """Draw dots and power pellets with glow effect"""
        # Regular dots with glow effect
        for dot in self.dots:
            # Outer glow
            pygame.draw.circle(self.screen, self.DOT_GLOW, dot, 4)
            # Main dot
            pygame.draw.circle(self.screen, self.WHITE, dot, 2)

        # Power pellets with pulsing animation
        pellet_size = 6 + int(math.sin(self.pellet_pulse_timer) * 2)  # Pulse between 4-8
        for pellet in self.power_pellets:
            # Outer glow (larger, pulsing)
            glow_size = pellet_size + 4
            glow_color = (255, 255, 200, 100)  # Semi-transparent yellow
            # Create surface for transparency
            glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
            self.screen.blit(glow_surf, (pellet[0]-glow_size, pellet[1]-glow_size))
            
            # Main pellet
            pygame.draw.circle(self.screen, self.WHITE, pellet, pellet_size)
            # Inner sparkle
            pygame.draw.circle(self.screen, self.YELLOW, pellet, pellet_size-2)

    def draw_bombs(self):
        """Draw bombs as realistic bomb obstacles"""
        if not self.bombs_enabled:
            return  # Don't draw bombs if disabled
        
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
        """Draw Pacman with smooth animation and glow effect"""
        col, row = self.pacman_pos
        center = (int(col * self.cell_size + self.cell_size // 2),
                 int(row * self.cell_size + self.cell_size // 2))

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

        # Smooth mouth animation using sine wave
        if self.pacman_direction != [0, 0]:
            mouth_open_angle = int(45 * abs(math.sin(self.pacman_mouth_cycle)))
            mouth_open_angle = max(5, mouth_open_angle)  # Min 5 degrees
        else:
            mouth_open_angle = 1
            
        pacman_radius = self.cell_size // 2 - 2
        
        # Draw glow effect
        glow_radius = pacman_radius + 3
        glow_surf = pygame.Surface((glow_radius*2+10, glow_radius*2+10), pygame.SRCALPHA)
        glow_color = (255, 255, 100, 80)
        pygame.draw.circle(glow_surf, glow_color, (glow_radius+5, glow_radius+5), glow_radius)
        self.screen.blit(glow_surf, (center[0]-glow_radius-5, center[1]-glow_radius-5))
        
        # Draw Pacman body
        if mouth_open_angle > 1:
            # Draw arc for Pacman with mouth open
            start_angle = math.radians(mouth_angle + mouth_open_angle)
            end_angle = math.radians(mouth_angle + 360 - mouth_open_angle)
            
            # Draw the Pacman arc (pie shape)
            points = [center]
            for angle in range(int(math.degrees(start_angle)), int(math.degrees(end_angle)) + 1, 3):
                x = center[0] + pacman_radius * math.cos(math.radians(angle))
                y = center[1] + pacman_radius * math.sin(math.radians(angle))
                points.append((int(x), int(y)))
            points.append(center)
            
            pygame.draw.polygon(self.screen, self.YELLOW, points)
            # Add darker outline for depth
            pygame.draw.polygon(self.screen, (200, 200, 0), points, 2)
        else:
            pygame.draw.circle(self.screen, self.YELLOW, center, pacman_radius)
            pygame.draw.circle(self.screen, (200, 200, 0), center, pacman_radius, 2)

    def draw_ghosts(self):
        """Draw ghosts using images from public folder"""
        # Skip drawing ghosts if they are disabled
        if not self.ghosts_enabled:
            return
            
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
                # Blink when scared is about to expire
                blink_threshold = getattr(config, 'SCARED_BLINK_THRESHOLD_FRAMES', 120)
                should_blink = ghost.get('scared_timer', 0) <= blink_threshold and (pygame.time.get_ticks() // 150) % 2 == 0
                if should_blink:
                    image_key = f'ghost{ghost_index}_right' if facing_right else f'ghost{ghost_index}_left'
                else:
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
        """Draw game UI with arcade style"""
        ui_y = self.maze_gen.height * self.cell_size + 15  # Tăng từ +10 lên +15 để dịch xuống

        # Create arcade-style font
        arcade_font = pygame.font.SysFont("courier", 24, bold=True)
        
        # Score with "1UP" label
        oneup_label = arcade_font.render("1UP", True, self.WHITE)
        self.screen.blit(oneup_label, (10, ui_y - 15))  # Giảm offset từ -20 xuống -15
        score_text = arcade_font.render(f"{self.score:06d}", True, self.WHITE)
        self.screen.blit(score_text, (10, ui_y + 8))  # Tăng từ +5 lên +8

        # High Score (center)
        highscore_label = arcade_font.render("HIGH SCORE", True, self.RED)
        highscore_x = self.maze_gen.width * self.cell_size // 2 - 80
        self.screen.blit(highscore_label, (highscore_x, ui_y - 15))  # Giảm offset từ -20 xuống -15
        highscore = max(self.score, getattr(self, 'high_score', 0))
        highscore_text = arcade_font.render(f"{highscore:06d}", True, self.WHITE)
        self.screen.blit(highscore_text, (highscore_x + 20, ui_y + 8))  # Tăng từ +5 lên +8

        # Lives with Pacman icons
        lives_x = self.maze_gen.width * self.cell_size - 150
        for i in range(self.lives):
            # Draw mini Pacman icons
            icon_center = (lives_x + i * 25, ui_y + 18)  # Tăng từ +15 lên +18
            pygame.draw.circle(self.screen, self.YELLOW, icon_center, 8)
            # Small mouth
            mouth_points = [
                icon_center,
                (icon_center[0] + 8, icon_center[1] - 4),
                (icon_center[0] + 8, icon_center[1] + 4)
            ]
            pygame.draw.polygon(self.screen, self.BLACK, mouth_points)
        
        # Level indicator
        level_text = arcade_font.render(f"LEVEL {self.level}", True, self.CYAN)
        self.screen.blit(level_text, (lives_x, ui_y - 15))  # Giảm offset từ -20 xuống -15

        # Draw right panel controls (always visible)
        self.draw_right_panel_controls()

        # FPS and performance info (top-right corner)
        if self.show_fps_info:
            self.draw_fps_info()

        elif self.game_state == "paused":
            pause_text = self.large_font.render("PAUSED", True, self.YELLOW)
            self.screen.blit(pause_text, (self.screen_width // 2 - 60, self.screen_height // 2))

    def draw_right_panel_controls(self):
        """Draw control instructions on right panel (fixed position at bottom)"""  
        maze_width = self.maze_gen.width * self.cell_size
        panel_x = maze_width + 10

        panel_width = 360

        # Font sizes (configurable)
        title_font_size = getattr(config, 'RIGHT_PANEL_TITLE_FONT_SIZE', 18)
        small_font_size = getattr(config, 'RIGHT_PANEL_SMALL_FONT_SIZE', 16)
        tiny_font_size = getattr(config, 'RIGHT_PANEL_TINY_FONT_SIZE', 14)
        line_height = getattr(config, 'RIGHT_PANEL_LINE_HEIGHT', 20)

        small_font = pygame.font.SysFont("arial", small_font_size, bold=True)
        tiny_font = pygame.font.SysFont("arial", tiny_font_size)

        # Title
        title_font = pygame.font.SysFont("arial", title_font_size, bold=True)

        # Estimate required panel height so bigger fonts don't get clipped.
        # Keep panel anchored to the bottom with a small margin.
        controls_count = 12
        estimated_panel_height = (
            25 +                 # title -> first line offset
            (line_height + 5) +  # mode line + extra spacing
            (controls_count * line_height) +
            10 + 20 +            # spacing + STATUS title spacing
            (4 * line_height) +  # Bombs, Ghosts, optional Path, optional Ghosts info
            10                   # bottom margin
        )

        # FIXED POSITION: anchored to bottom (dynamic offset based on content height)
        panel_y = max(10, self.screen_height - estimated_panel_height)
        title = title_font.render("CONTROLS", True, self.CYAN)
        self.screen.blit(title, (panel_x, panel_y))
        
        y = panel_y + 25
        
        # Game mode status with speed
        if self.auto_mode:
            speed_multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
            mode_text = f"AUTO [{speed_multiplier}x]"
            mode_color = self.YELLOW
        else:
            mode_text = "MANUAL"
            mode_color = self.WHITE
        mode = small_font.render(f"Mode: {mode_text}", True, mode_color)
        self.screen.blit(mode, (panel_x, y))
        y += line_height + 5
        
        # Controls list
        controls = [
            ("A", "Toggle Auto/Manual", self.YELLOW),
            ("+/-", "Speed Up/Down", self.CYAN),
            ("0", "Reset Speed", self.CYAN),
            ("H", "Show/Hide Path Hint", self.GREEN if self.show_shortest_path else self.WHITE),
            ("V", "Toggle Visualization", self.GREEN if (self.visualizer and self.visualizer.enabled) else self.WHITE),
            ("B", "Debug Info", self.WHITE),
            ("F", "Toggle FPS Info", self.GREEN if self.show_fps_info else self.WHITE),
            ("X", "Toggle Bombs", self.RED if self.bombs_enabled else self.WHITE),
            ("G", "Toggle Ghosts", self.PINK if self.ghosts_enabled else self.WHITE),
            ("R", "Restart Game", self.WHITE),
            ("P", "Pause", self.WHITE),
            ("ESC", "Quit", self.RED),
        ]
        
        for key, desc, color in controls:
            # Draw key in brackets
            key_text = tiny_font.render(f"[{key}]", True, self.YELLOW)
            self.screen.blit(key_text, (panel_x, y))
            
            # Draw description
            desc_text = tiny_font.render(desc, True, color)
            self.screen.blit(desc_text, (panel_x + 45, y))
            y += line_height
        
        # Status indicators
        y += 10
        status_title = small_font.render("STATUS", True, self.CYAN)
        self.screen.blit(status_title, (panel_x, y))
        y += 20
        
        # Bomb status
        bomb_status = "ON" if self.bombs_enabled else "OFF"
        bomb_color = self.RED if self.bombs_enabled else (100, 100, 100)
        bomb_text = tiny_font.render(f" Bombs: {bomb_status}", True, bomb_color)
        self.screen.blit(bomb_text, (panel_x, y))
        y += line_height
        
        # Ghost status
        ghost_status = "ON" if self.ghosts_enabled else "OFF"
        ghost_color = self.PINK if self.ghosts_enabled else (100, 100, 100)
        ghost_text = tiny_font.render(f" Ghosts: {ghost_status}", True, ghost_color)
        self.screen.blit(ghost_text, (panel_x, y))
        y += line_height
        
        # Path hint status
        if self.show_shortest_path:
            path_steps = len(self.shortest_path) - 1 if self.shortest_path else 0
            path_text = tiny_font.render(f" Path: {path_steps} steps", True, self.GREEN)
            self.screen.blit(path_text, (panel_x, y))
            y += line_height
        
        # Ghost info
        if len(self.ghosts) > 0:
            ghost_modes = [f"{g['name'][:1]}:{g['mode'][:3]}" for g in self.ghosts[:2]]
            ghost_text = tiny_font.render(f" Ghosts: {' '.join(ghost_modes)}", True, self.PINK)
            self.screen.blit(ghost_text, (panel_x, y))

    def draw_fps_info(self):
        """Vẽ thông tin FPS và hiệu năng bên phải (vị trí trên)"""
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
        title_text = title_font.render("CHÚC MỪNG!", True, (255, 215, 0))  # Gold
        title_rect = title_text.get_rect(center=(box_x + box_width // 2, box_y + 40))
        self.screen.blit(title_text, title_rect)
        
        # Score information
        score_font = pygame.font.SysFont("arial", 20, bold=True)
        
        # Current score
        score_text = score_font.render(f"Final Score: {self.score}", True, self.WHITE)
        score_rect = score_text.get_rect(center=(box_x + box_width // 2, box_y + 100))
        self.screen.blit(score_text, score_rect)
        
        # Level info
        level_text = score_font.render(f"Completed Level {self.level}", True, (0, 255, 127))  # Light blue
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
        """Vẽ hộp thông báo game over chi tiết kèm thống kê và thông điệp động lực"""
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
                death_cause = f"Caught by {self.last_death_cause}"
                death_color = (255, 182, 193)  # Light pink
            elif self.last_death_cause == "Bom nổ":
                death_cause = "Bomb Explosion"
                death_color = (255, 140, 0)    # Dark orange
            else:
                death_cause = f"{self.last_death_cause}"
                death_color = (255, 99, 71)   # Tomato red
        else:
            death_cause = "Out of Lives"
            death_color = (255, 99, 71)   # Tomato red
        
        # Death cause
        cause_text = stats_font.render(f"Cause: {death_cause}", True, death_color)
        cause_rect = cause_text.get_rect(center=(box_x + box_width // 2, box_y + 140))
        self.screen.blit(cause_text, cause_rect)
        
        # Performance stats
        stats_small_font = pygame.font.SysFont("arial", 14, bold=True)
        
        # Số hạt đã ăn
        dots_collected = len([pos for pos in self.initial_dots if pos not in self.dots])
        total_dots = len(self.initial_dots) if hasattr(self, 'initial_dots') else len(self.dots)
        dots_text = stats_small_font.render(f"Dots Collected: {dots_collected}/{total_dots}", True, (173, 216, 230))  # Light blue
        dots_rect = dots_text.get_rect(center=(box_x + box_width // 2, box_y + 170))
        self.screen.blit(dots_text, dots_rect)
        
        # Thời gian sống sót (nếu có)
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
            motivation_msg = " Mỗi kết thúc là một khởi đầu mới!"
        
        motivation_text = motivation_font.render(motivation_msg, True, (255, 223, 0))  # Gold
        motivation_rect = motivation_text.get_rect(center=(box_x + box_width // 2, box_y + 230))
        self.screen.blit(motivation_text, motivation_rect)
        
        # Instructions
        instruction_font = pygame.font.SysFont("arial", 16, bold=True)
        
        restart_text = instruction_font.render("Nhấn R để chơi lại", True, (255, 182, 193))  # Light pink
        restart_rect = restart_text.get_rect(center=(box_x + box_width // 2, box_y + 270))
        self.screen.blit(restart_text, restart_rect)
        
        quit_text = instruction_font.render("Nhấn ESC để thoát", True, (211, 211, 211))  # Light gray
        quit_rect = quit_text.get_rect(center=(box_x + box_width // 2, box_y + 295))
        self.screen.blit(quit_text, quit_rect)

    def move_pacman(self):
        """Di chuyển Pacman theo lưới - từng ô một"""
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
                # Tính tốc độ - có điều chỉnh tốc độ động
                base_speed = config.PACMAN_SPEED
                
                # Áp dụng hệ số tốc độ auto mode nếu đang bật
                if self.auto_mode:
                    auto_speed_multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                    base_speed = base_speed * auto_speed_multiplier
                
                if config.ENABLE_DYNAMIC_SPEED:
                    # Tính khoảng cách đến con ma gần nhất
                    min_ghost_distance = float('inf')
                    for ghost in self.ghosts:
                        if not self.is_ghost_just_eyes(ghost):  # Only consider active ghosts
                            ghost_row = int(round(ghost['pos'][1]))
                            ghost_col = int(round(ghost['pos'][0]))
                            distance = abs(current_row - ghost_row) + abs(current_col - ghost_col)
                            min_ghost_distance = min(min_ghost_distance, distance)
                    
                    # Áp dụng hệ số tốc độ dựa trên độ gần của ma
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
        # Skip moving ghosts if they are disabled
        if not self.ghosts_enabled:
            return
            
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
                    
                    # Áp dụng hệ số tốc độ auto mode nếu đang bật (giống Pacman)
                    if self.auto_mode:
                        auto_speed_multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                        ghost_speed = ghost_speed * auto_speed_multiplier
                    
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
                
                # Áp dụng hệ số tốc độ auto mode nếu đang bật (giống Pacman)
                if self.auto_mode:
                    auto_speed_multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                    eyes_speed = eyes_speed * auto_speed_multiplier
                
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
                    ghost['scared'] = False
                    ghost['scared_timer'] = 0
                    ghost['pos'] = [float(final_target[1]), float(final_target[0])]  # (col, row)
                    # Clean up pathfinding data
                    if 'return_path' in ghost:
                        del ghost['return_path']
                    if 'path_index' in ghost:
                        del ghost['path_index']
                    print(f"{ghost.get('name', 'Ghost')} respawned at Grid({final_target[0]}, {final_target[1]})!")
            else:
                # Reached end of path
                final_target = path[-1]
                ghost['eaten'] = False
                ghost['scared'] = False
                ghost['scared_timer'] = 0
                ghost['pos'] = [float(final_target[1]), float(final_target[0])]  # (col, row)
                # Clean up pathfinding data
                if 'return_path' in ghost:
                    del ghost['return_path']
                if 'path_index' in ghost:
                    del ghost['path_index']
                print(f"{ghost.get('name', 'Ghost')} respawned at Grid({final_target[0]}, {final_target[1]})!")

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
        """
        CRITICAL FIX: Tính toán đường đi tự động với ưu tiên:
        1. LUÔN LUÔN tránh bomb (bom là chướng ngại vật cố định)
        2. Cố gắng tránh ghost nếu có thể
        """
        if not self.auto_target:
            return

        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)

        # Lấy vị trí bom - LUÔN phải tránh (khi bom bật)
        bomb_grid = self.get_bomb_grid_positions() if self.bombs_enabled else set()
        
        # Lấy vị trí ma để tránh - chỉ ma không scared
        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                          if not g.get('scared', False) and not g.get('eaten', False)]

        try:
            # METHOD 1: Try path avoiding BOTH bombs AND ghosts
            if ghost_positions:
                avoidance_radius = getattr(config, 'GHOST_AVOIDANCE_RADIUS', 5)
                path, distance = self.dijkstra.shortest_path_with_ghost_and_bomb_avoidance(
                    pacman_pos, self.auto_target, ghost_positions, bomb_grid, avoidance_radius
                )
                
                if path and distance < float('inf'):
                    self.auto_path = path
                    # print(f"Path found: {len(path)-1} steps (avoiding bombs + ghosts)")
                    return

        except AttributeError:
            # Function doesn't exist yet, continue to fallback
            pass
        except Exception as e:
            print(f"Lỗi tìm đường (tránh ma): {e}")

        # PHƯƠNG ÁN 2 (dự phòng): Chỉ tránh bom (có thể không tránh được ma)
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(
                pacman_pos, self.auto_target, bomb_grid, enable_logging=False
            )
            if path and distance < float('inf'):
                self.auto_path = path
                # if ghost_positions:
                #     print(f"Path found: {len(path)-1} steps (avoiding bombs only, ghosts may be on path)")
                # else: print(f"Path found: {len(path)-1} steps (avoiding bombs)")
                return
            else:
                self.auto_path = []
                # print(f" No path to target (bombs blocking)")
        except Exception as e:
            print(f" Lỗi tính đường đi: {e}")
            self.auto_path = []

    def calculate_shortest_path_to_goal(self):
        """Tính toán đường đi ngắn nhất từ vị trí Pacman hiện tại đến goal, tránh bom"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        pacman_pos = (pacman_row, pacman_col)
        
        # Lấy vị trí bom theo toạ độ lưới
        bomb_grid = self.get_bomb_grid_positions()
        
        # Kiểm tra tình trạng bom chặn đường trước khi tính toán
        if bomb_grid:
            is_blocked, blockage_level, alternatives = self.dijkstra.check_bomb_blockage_status(
                pacman_pos, self.current_goal, bomb_grid
            )
            
            # Hiển thị cảnh báo đặc biệt cho complete blockage (rate limited)
            if blockage_level == 'COMPLETE_BLOCKAGE':
                if not hasattr(self, '_last_blockage_warning') or pygame.time.get_ticks() - self._last_blockage_warning > 2000:
                    print("Pacman bị bom bao vây!")
                    self._last_blockage_warning = pygame.time.get_ticks()
        
        # Ưu tiên A* cho đường đến goal (nhanh hơn) với bom là obstacles
        try:
            astar_path, astar_distance = self.astar.shortest_path(pacman_pos, self.current_goal, obstacles=bomb_grid)
            if astar_path and astar_distance < float('inf'):
                self.shortest_path = astar_path
                return
        except Exception:
            # Nếu A* gặp lỗi, fallback xuống Dijkstra
            pass

        # Fallback: Dijkstra (giữ nguyên logic cũ)
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, self.current_goal, bomb_grid)
            if path and distance < float('inf'):
                self.shortest_path = path
            else:
                self.shortest_path = []
                # Rate limit warning (only print every 2 seconds)
                if bomb_grid:
                    if not hasattr(self, '_last_bomb_path_warning') or pygame.time.get_ticks() - self._last_bomb_path_warning > 2000:
                        print(" Bom chặn đường đến mục tiêu!")
                        self._last_bomb_path_warning = pygame.time.get_ticks()
        except Exception:
            self.shortest_path = []

    def calculate_hint_path_to_exit(self):
        """Tính toán đường gợi ý từ vị trí Pacman hiện tại đến exit gate (có thể dùng bất cứ lúc nào)"""
        pacman_col, pacman_row = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
        pacman_pos = (pacman_row, pacman_col)
        
        # Target là exit gate (goal chính của game)
        exit_goal = self.goal if hasattr(self, 'goal') else None
        if not exit_goal:
            print("Không tìm thấy cổng thoát!")
            self.shortest_path = []
            return
        
        # Lấy vị trí bom theo toạ độ lưới
        bomb_grid = self.get_bomb_grid_positions()
        
        # Kiểm tra bomb blockage cho đường đến exit gate
        if bomb_grid:
            is_blocked, blockage_level, alternatives = self.dijkstra.check_bomb_blockage_status(
                pacman_pos, exit_goal, bomb_grid
            )
            
            if blockage_level == 'COMPLETE_BLOCKAGE':
                print("Lối thoát bị bom chặn!")
        
        try:
            path, distance = self.dijkstra.shortest_path_with_bomb_avoidance(pacman_pos, exit_goal, bomb_grid)
            if path and distance < float('inf'):
                self.shortest_path = path
            else:
                self.shortest_path = []
                if bomb_grid:
                    print(" Exit gate bị cô lập!")
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
        """Đánh giá đường đi có an toàn khỏi ma không"""
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
        
        # Đường đi an toàn nếu tỉ lệ ô nguy hiểm thấp hơn ngưỡng
        safety_threshold = getattr(config, 'SAFETY_DANGER_THRESHOLD', 0.2)
        return (danger_count / total_positions) < safety_threshold

    def _calculate_path_safety_penalty(self, path, ghost_positions, avoidance_radius):
        """Tính điểm phạt an toàn cho đường đi (cao hơn = nguy hiểm hơn)"""
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
        # Use AI's check_ghosts_nearby which already handles path-based distance
        nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=8)
        
        # Use NEW AI system for ghost avoidance if there are nearby ghosts
        # Add AI throttling to prevent excessive direction changes
        if not hasattr(self, 'last_ai_call'):
            self.last_ai_call = 0
        if not hasattr(self, 'ai_decision_cooldown'):
            self.ai_decision_cooldown = 50  # 50ms cooldown - nhanh hơn để phản ứng kịp ma
            
        current_time = pygame.time.get_ticks()
        
        # Kiểm tra xem có ghost RẤT gần không (≤3 ô) - bỏ qua cooldown
        has_close_ghost = any(dist <= 3 for _, dist in nearby_ghosts)
        ai_can_act = has_close_ghost or ((current_time - self.last_ai_call) >= self.ai_decision_cooldown)
        
        if nearby_ghosts and hasattr(self, 'pacman_ai') and ai_can_act:
            try:
                ai_handled = self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts)
                if ai_handled:
                    # Removed spam log - AI handles ghost avoidance silently
                    self.last_ai_call = current_time  # Update AI call time
                    return  # AI has handled the situation
            except Exception as e:
                print(f"AI error: {e}")
                # Fall back to simple emergency logic below
        
        # EMERGENCY FALLBACK - Simple emergency stop for critical proximity (≤ 1 cell)
        # IMPORTANT: Chỉ chạy khi AI KHÔNG đang trong escape mode (tránh conflict)
        if not (hasattr(self.pacman_ai, 'escape_mode') and self.pacman_ai.escape_mode):
            critical_ghosts = []
            for ghost_pos, distance in nearby_ghosts:
                if distance <= 1:  # Only immediate collision threat
                    critical_ghosts.append({
                        'distance': distance,
                        'position': ghost_pos
                    })
        else:
            critical_ghosts = []  # AI đang xử lý, không trigger EMERGENCY fallback
        
        if critical_ghosts:
            # Get current Pacman position
            pacman_col = int(round(self.pacman_pos[0]))
            pacman_row = int(round(self.pacman_pos[1]))
            
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
                print(f"⚠️ EMERGENCY: {len(critical_ghosts)} ma va chạm, thoát ngay!")
                self.pacman_next_direction = best_escape
                return
            else:
                # Không tìm được lối thoát,  thử di chuyển về phía goal
                print("⚠️ EMERGENCY: Không tìm được lối thoát! Di chuyển về goal.")
                pacman_col = int(round(self.pacman_pos[0]))
                pacman_row = int(round(self.pacman_pos[1]))
                if hasattr(self, 'exit_gate'):
                    goal_row, goal_col = self.exit_gate
                    self.emergency_goal_move(pacman_col, pacman_row, goal_col, goal_row)
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

        # =====================================================================
        # STATE MACHINE INTEGRATION - Quyết định thống nhất từ AI
        # =====================================================================
        # Cập nhật zone awareness và lấy quyết định di chuyển từ state machine
        movement_decision = self.pacman_ai.get_movement_decision()
        
        if movement_decision:
            direction, priority = movement_decision
            
            if priority == 'CRITICAL':
                # FLEEING - Ưu tiên cao nhất, thực hiện ngay
                self.pacman_next_direction = direction
                self.pacman_ai.escape_mode = True
                self.pacman_ai.escape_direction = direction
                self.pacman_ai.escape_steps = 0
                self.pacman_ai.escape_commit_time = current_time
                # Removed spam log
                return
            
            elif priority == 'HIGH':
                # EVADING - Ưu tiên cao, nhưng kiểm tra escape mode
                if not getattr(self.pacman_ai, 'escape_mode', False):
                    self.pacman_next_direction = direction
                    self.pacman_ai.escape_mode = True
                    self.pacman_ai.escape_direction = direction
                    self.pacman_ai.escape_steps = 0
                    self.pacman_ai.escape_commit_time = current_time
                    self.pacman_ai.min_escape_distance = 4
                    # Removed spam log
                    return
            
            elif priority == 'MEDIUM':
                # SAFE_RETURN cooldown - tiếp tục đi theo hướng an toàn
                self.pacman_next_direction = direction
                # KHÔNG set escape_mode vì đang trong SAFE_RETURN
                return
        
        # Nếu đang trong state SAFE_RETURN hoặc ALERT, vẫn cảnh giác
        current_state = getattr(self.pacman_ai, 'current_state', 'NORMAL')
        if current_state in ['SAFE_RETURN', 'ALERT']:
            # Vẫn check ghost liên tục và có thể trigger evade
            pass  # Để logic bên dưới xử lý
        # =====================================================================

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
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=6)
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
        
        # Throttle ghost checking to reduce computational load (check every 50ms for faster response)  
        should_check_ghosts = (current_time - self.last_ghost_check) > 50
        if should_check_ghosts:
            self.last_ghost_check = current_time
            # Kiểm tra ghosts trong bán kính 6 ô - tăng từ 4 lên 6 để phát hiện sớm hơn
            nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=6)

        # ESCAPE MODE: Kiểm tra nếu đang trong chế độ thoát hiểm
        if getattr(self.pacman_ai, 'escape_mode', False):
            # Track previous position để detect movement
            if not hasattr(self.pacman_ai, 'escape_last_pos'):
                self.pacman_ai.escape_last_pos = [self.pacman_pos[0], self.pacman_pos[1]]
            
            # Chỉ increment steps khi Pacman THỰC SỰ DI CHUYỂN (position thay đổi)
            current_pos = [int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))]
            last_pos = [int(round(self.pacman_ai.escape_last_pos[0])), int(round(self.pacman_ai.escape_last_pos[1]))]
            
            if current_pos != last_pos:
                self.pacman_ai.escape_steps += 1
                self.pacman_ai.escape_last_pos = [self.pacman_pos[0], self.pacman_pos[1]]
                # Debug: confirm movement
                # print(f"   Escape step {self.pacman_ai.escape_steps}: {last_pos} → {current_pos}")
            
            # Giảm thời gian escape để Pacman không bị kẹt lâu
            max_escape_steps = getattr(self.pacman_ai, 'min_escape_distance', 3)  # Mặc định 3 bước
            
            # CHECK COMMIT TIME - Phải commit đủ lâu trước khi có thể thoát escape
            escape_commit_time = getattr(self.pacman_ai, 'escape_commit_time', 0)
            min_escape_duration = getattr(self.pacman_ai, 'min_escape_duration', 400)
            time_in_escape = current_time - escape_commit_time
            
            # QUAN TRỌNG: Thoát khẩn cấp nếu bị kẹt (không di chuyển được sau 600ms)
            if time_in_escape > 600 and self.pacman_ai.escape_steps < 2:
                print(f"Escape mode bị kẹt! Chỉ đi được {self.pacman_ai.escape_steps} bước sau {time_in_escape}ms - Thoát ngay!")
                self.pacman_ai.escape_mode = False
                self.pacman_ai.escape_steps = 0
                self.goal_locked = False
                self.ghost_avoidance_active = False
                # Tìm hướng mới ngay
                nearby_ghosts_now = self.pacman_ai.check_ghosts_nearby(avoidance_radius=5)
                if nearby_ghosts_now:
                    self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts_now)
                return
            
            # Kiểm tra xem đã đi đủ xa chưa hoặc quá lâu VÀ đã commit đủ thời gian
            if self.pacman_ai.escape_steps >= max_escape_steps and time_in_escape >= min_escape_duration:
                # Kiểm tra xem có ghost nào ở gần không
                if should_check_ghosts:
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=6)
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
                    print(f"Thoat escape mode sau {time_in_escape}ms")
                    
                    # === SYNC VỚI STATE MACHINE ===
                    # Chuyển sang SAFE_RETURN thay vì NORMAL ngay
                    if hasattr(self.pacman_ai, '_transition_to_state'):
                        self.pacman_ai._transition_to_state(self.pacman_ai.STATE_SAFE_RETURN)
                    
                    # === QUAY LẠI GOAL NGAY ===
                    # Bỏ post-escape cooldown để quay lại goal nhanh hơn
                    # Tính toán đường đi mới đến goal ngay lập tức
                    self.goal_locked = False  # Mở khóa để tìm goal mới
                    self.find_goal_first()  # Tìm goal ngay
                    
                else:
                    # Vẫn có ghost gần nhưng không in quá nhiều log
                    pass
            else:
                # Kiểm tra ghost ít thường xuyên trong escape mode
                if should_check_ghosts:
                    nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=6)  # Tăng từ 4 lên 6
            
            # === EARLY CHECK: Hướng escape có an toàn không? ===
            # Kiểm tra xem đang chạy thẳng vào ma không
            escape_dir = getattr(self.pacman_ai, 'escape_direction', None)
            if escape_dir and nearby_ghosts:
                px, py = int(round(self.pacman_pos[1])), int(round(self.pacman_pos[0]))
                for ghost_pos, dist in nearby_ghosts:
                    gx, gy = ghost_pos
                    # Vector từ pacman đến ghost
                    dx, dy = gx - px, gy - py
                    # Nếu escape direction hướng về phía ghost -> đổi hướng!
                    if (escape_dir[0] * dx > 0) or (escape_dir[1] * dy > 0):
                        if dist <= 4:  # Ghost trong 4 ô và đang chạy về phía nó
                            print(f"ESCAPE DIRECTION TOWARDS GHOST! Dist: {dist} - Re-evaluating...")
                            # Cancel escape và tìm hướng mới
                            self.pacman_ai.escape_mode = False
                            self.pacman_ai.escape_steps = 0
                            if self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                                return  # Đã tìm được hướng mới
            
            # Trong escape mode, MAINTAIN escape direction để Pacman tiếp tục chạy
            # Đây là lý do tại sao escape mode có 0 steps - direction không được maintain!
            # KHÔNG return sớm, để logic dưới vẫn chạy (find_simple_goal, etc.)
            if nearby_ghosts:
                min_distance = min(d for _, d in nearby_ghosts)
                if min_distance <= 1:  # Chỉ khi CỰC gần mới re-evaluate
                    # Add emergency throttling to prevent spam
                    if not hasattr(self, 'last_emergency_call'):
                        self.last_emergency_call = 0
                    if (current_time - self.last_emergency_call) >= 100:  # 100ms cooldown for emergency
                        if self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                            self.last_emergency_call = current_time
                            # Continue to rest of logic (không return)
            # SKIP ghost avoidance logic dưới (đã xử lý trong escape mode)
            # Nhảy thẳng xuống find_simple_goal

        # NEW: IMMINENT COLLISION CHECK - Phát hiện va chạm sắp xảy ra
        # CHECK NGAY CẢ KHI ĐANG TRONG ESCAPE MODE để tránh đâm vào ma đang đến
        imminent_collision, collision_info = self.pacman_ai.check_imminent_collision(look_ahead_steps=6)  # Tăng từ 5 lên 6
        if imminent_collision:
            collision_step = collision_info.get('collision_step', 99)
            closing_speed = collision_info.get('closing_speed', False)
            
            # Nếu đang escape mode và va chạm sắp xảy ra -> đổi hướng escape ngay!
            if getattr(self.pacman_ai, 'escape_mode', False):
                print(f"COLLISION DURING ESCAPE in {collision_step} steps! Closing: {closing_speed} - Changing direction!")
                # Huỷ escape hiện tại và tìm hướng mới
                self.pacman_ai.escape_mode = False
                self.pacman_ai.escape_commit_duration = 0
                
            print(f"IMMINENT COLLISION DETECTED in {collision_step} steps! Closing speed: {closing_speed}")
            # Force emergency avoidance ngay lập tức
            ghost_pos = collision_info['ghost_future_pos']
            emergency_ghosts = [(ghost_pos, collision_step)]
            if self.pacman_ai.emergency_ghost_avoidance(emergency_ghosts):
                return  # Đã né thành công

        # GHOST AVOIDANCE: Chỉ kiểm tra khi cần thiết (SKIP nếu đang trong escape mode!)
        if nearby_ghosts and not getattr(self.pacman_ai, 'escape_mode', False):
            min_distance = min(d for _, d in nearby_ghosts)
            
            # NẾU MA ĐẾN GẦN TRONG LÚC COOLDOWN -> Cancel cooldown và né ngay!
            if min_distance <= 4 and getattr(self.pacman_ai, 'post_escape_cooldown', False):
                print(f"Ghost detected during cooldown! Distance: {min_distance} - Canceling cooldown!")
                self.pacman_ai.force_end_cooldown()
            
            # PRIORITY 1: Emergency avoidance khi ghost gần (trong 5 ô) - tăng từ 4 lên 5
            if min_distance <= 5:  # Tăng phạm vi phát hiện để phản ứng sớm hơn
                # Xử lý khẩn cấp: ưu tiên ngã rẽ, tránh quay đầu liên tục
                if self.pacman_ai.emergency_ghost_avoidance(nearby_ghosts):
                    return  # Đã xử lý thành công, thoát ngay
                
                # PRIORITY 2: Complex avoidance chỉ khi ghost RẤT gần
                if min_distance <= 3 or self.ghost_avoidance_active:  # Tăng từ 2 lên 3
                    if not self.ghost_avoidance_active:
                        self.ghost_avoidance_active = True
                        pacman_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))
                        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                                          if not g.get('scared', False)]

                        # Chỉ in log khi kích hoạt lần đầu
                        print(" Tránh ma!")
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
            nearby_ghosts = self.pacman_ai.check_ghosts_nearby(avoidance_radius=6)  # Tăng từ 5 lên 6
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

        # === POST-ESCAPE COOLDOWN CHECK (Enhanced với State Machine) ===
        # Nếu đang trong cooldown sau escape, KHÔNG tính đường mới
        # Thay vào đó, tiếp tục đi theo hướng an toàn VÀ check liên tục
        if getattr(self.pacman_ai, 'post_escape_cooldown', False):
            # Kiểm tra xem có thể thoát cooldown chưa
            if not self.pacman_ai.check_safe_zone_status():
                # Vẫn trong cooldown
                
                # === QUAN TRỌNG: Check state machine xem có cần né tiếp không ===
                current_state = getattr(self.pacman_ai, 'current_state', 'NORMAL')
                if current_state in ['FLEEING', 'EVADING']:
                    # State machine yêu cầu né -> để state machine xử lý
                    # (đã xử lý ở đầu function với get_movement_decision)
                    pass
                else:
                    # Tiếp tục đi theo hướng an toàn
                    safe_direction = self.pacman_ai.get_post_escape_direction()
                    if safe_direction:
                        self.pacman_next_direction = list(safe_direction)
            # else: Đã an toàn, cho phép tiếp tục logic bình thường
        
        # === SAFE_RETURN STATE CHECK ===
        # Khi trong SAFE_RETURN, vẫn cảnh giác và có thể né lại
        current_state = getattr(self.pacman_ai, 'current_state', 'NORMAL')
        if current_state == 'SAFE_RETURN':
            # Check xem có ghost đang tiến đến không
            zone_info = self.pacman_ai.update_ghost_zone_awareness()
            if zone_info.get('ghosts_in_zone'):
                approaching = [g for g in zone_info['ghosts_in_zone'] 
                              if g.get('approaching', False) and g.get('distance', 99) <= 5]
                if approaching:
                    # Có ghost đang tiến đến -> để state machine xử lý (đã ở đầu function)
                    print(f"[SAFE_RETURN] Ghost approaching! Will evade.")

        # CRITICAL: Only find new goal if NO current goal OR goal reached/collected
        # VÀ không trong post-escape cooldown VÀ state là NORMAL
        if not self.current_goal or not self.goal_locked:
            is_safe_state = current_state in ['NORMAL', 'ALERT']
            if self.goal_cooldown <= 0 and not getattr(self.pacman_ai, 'post_escape_cooldown', False) and is_safe_state:
                self.find_goal_first()
                if self.current_goal:
                    self.goal_locked = True

        # GOAL-ONLY movement - không bị phân tâm bởi dots
        # CHỈ khi không trong post-escape cooldown VÀ state cho phép
        is_safe_to_goal = (
            current_state in ['NORMAL', 'ALERT'] and 
            not getattr(self.pacman_ai, 'post_escape_cooldown', False) and
            not getattr(self.pacman_ai, 'escape_mode', False)
        )
        
        if self.current_goal and not self.ghost_avoidance_active and is_safe_to_goal:
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
        else:
            # FALLBACK CUỐI CÙNG: Nếu không có goal và không trong avoidance mode
            # Tìm goal mới hoặc di chuyển random để không đứng im
            if not self.current_goal:
                self.find_goal_first()
            
            # Nếu vẫn không có goal, di chuyển theo hướng hiện tại hoặc random
            if not self.current_goal:
                # Giữ hướng hiện tại nếu có thể
                if self.pacman_direction and self.pacman_direction != [0, 0]:
                    px, py = int(round(self.pacman_pos[0])), int(round(self.pacman_pos[1]))
                    next_x = px + self.pacman_direction[0]
                    next_y = py + self.pacman_direction[1]
                    if self.is_valid_position(next_x, next_y):
                        self.pacman_next_direction = self.pacman_direction[:]
                    else:
                        # Tìm hướng random hợp lệ
                        for test_dir in [[1,0], [-1,0], [0,1], [0,-1]]:
                            if self.is_valid_position(px + test_dir[0], py + test_dir[1]):
                                self.pacman_next_direction = test_dir
                                break

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
        
        # Thử nhiều chiến lược tìm đường, ưu tiên độ an toàn
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
                    # KIỂM TRA AN TOÀN BỔ SUNG: Đảm bảo đường không đi qua vị trí ma được dự đoán
                    if self._validate_path_against_predicted_ghosts(path, ghost_data):
                        self.auto_path = path
                        self.auto_target = goal_pos
                        print(f"{strategy_name}: {len(path)} bước")
                        return True
                    else:
                        print(f"{strategy_name} bị ma chặn")
                        continue
                        
            except Exception as e:
                print(f"Lỗi với chiến lược {strategy_name}: {e}")
                continue
        
        print("Không tìm được đường an toàn")
        return False
    
    def _validate_path_against_predicted_ghosts(self, path, ghost_data):
        """Xác nhận đường đi không cắt qua vị trí ma dự đoán"""
        if not path or len(path) <= 1:
            return False
            
        # Dự đoán vị trí ma trong vài bước tới
        max_prediction_steps = min(10, len(path))
        
        for step in range(max_prediction_steps):
            if step >= len(path):
                break
                
            path_pos = path[step]
            
            # So khớp với vị trí ma được dự đoán tại bước này
            for ghost in ghost_data:
                ghost_pos = ghost['pos']
                ghost_dir = ghost['direction']
                ghost_speed = ghost['speed']
                
                # Dự đoán vị trí ma ở bước này
                predicted_ghost_row = ghost_pos[0] + (ghost_dir[1] * step * ghost_speed)
                predicted_ghost_col = ghost_pos[1] + (ghost_dir[0] * step * ghost_speed)
                predicted_ghost_pos = (predicted_ghost_row, predicted_ghost_col)
                
                # Kiểm tra xung đột giữa đường đi và vị trí ma dự đoán
                if path_pos == predicted_ghost_pos:
                    print(f"Path position {path_pos} conflicts with predicted ghost at step {step}")
                    return False
                
                # Check if too close (adjacent)
                distance = abs(path_pos[0] - predicted_ghost_pos[0]) + abs(path_pos[1] - predicted_ghost_pos[1])
                if distance <= 1:
                    print(f"Path too close to predicted ghost at step {step}: distance {distance}")
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
            # print(" GOAL-ONLY: Không tìm thấy goal hợp lệ")

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
        """Dò đường chỉ cho mục tiêu (goal), tối ưu để đến đích"""
        import heapq

        start = (int(start_pos[0]), int(start_pos[1]))
        goal = goal_pos

        if start == goal:
            return None

        def heuristic(pos):
            """Khoảng cách Manhattan - khuyến khích đi thẳng tới goal"""
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])

        # A* algorithm với goal priority
        heap = [(heuristic(start), 0, start, [])]
        visited = set()
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
            # Lấy vị trí bom một lần trước vòng lặp (tối ưu)
        bomb_grid = self.get_bomb_grid_positions()

        while heap:
            f_score, g_score, (x, y), path = heapq.heappop(heap)

            if (x, y) in visited:
                continue
            visited.add((x, y))

            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                if (nx, ny) == goal:
                    # TÌM THẤY GOAL - trả về bước đầu tiên
                    first_step = path[0] if path else (dx, dy)
                    return [first_step[0], first_step[1]]

                # Kiểm tra vị trí hợp lệ và không có bom
                if (nx, ny) not in visited and self.is_valid_position(nx, ny) and (ny, nx) not in bomb_grid:
                    new_g_score = g_score + 1
                    new_f_score = new_g_score + heuristic((nx, ny))
                    new_path = path + [(dx, dy)]

                    heapq.heappush(heap, (new_f_score, new_g_score, (nx, ny), new_path))

        return None

    def emergency_goal_move(self, px, py, gx, gy):
        """Di chuyển khẩn cấp trực tiếp tới goal"""
        dx = 1 if gx > px else (-1 if gx < px else 0)
        dy = 1 if gy > py else (-1 if gy < py else 0)

        # Lấy vị trí bom
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

        # Phương án cuối: bất kỳ hướng hợp lệ nào
        for test_dir in [[1,0], [-1,0], [0,1], [0,-1]]:
            if self.is_valid_position(px + test_dir[0], py + test_dir[1]) and (py + test_dir[1], px + test_dir[0]) not in bomb_grid:
                self.pacman_next_direction = test_dir
                return

    def find_simple_goal(self):
        """Tìm goal gần nhất và bám theo (CHỈ exit gate)"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])

        if hasattr(self, 'exit_gate') and self.exit_gate:
            self.current_goal = self.exit_gate
            print(f"Cổng thoát: {self.exit_gate}")
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
        """Di chuyển tới goal bằng BFS"""
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
        """Tính đường ngắn nhất tới goal hiện tại"""
        if not self.current_goal:
            return
            
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        pacman_pos = (pacman_row, pacman_col)
        
        path, distance = self.dijkstra.shortest_path(pacman_pos, self.current_goal)
        if path:
            self.path_to_goal = path
            # print(f"Path calculated: {len(path)} steps to goal {self.current_goal}")  # Reduced verbosity
        else:
            # print(" Không tìm thấy đường tới goal")  # Giảm log
            self.path_to_goal = []
            # If no path found, invalidate current goal
            self.current_goal = None

    def find_safe_detour(self):
        """Tìm lối vòng an toàn khi có ma gần"""
        pacman_col, pacman_row = int(self.pacman_pos[0]), int(self.pacman_pos[1])
        
        # Get ghost positions
        ghost_positions = [(int(g['pos'][1]), int(g['pos'][0])) for g in self.ghosts 
                          if not g.get('scared', False)]
        
        # Tìm hướng an toàn (tránh xa ma)
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
        
        # Chọn hướng an toàn và gần goal nhất
        if safe_directions:
            safe_directions.sort(key=lambda x: x[2])  # Sort by distance to goal
            chosen_direction = safe_directions[0][:2]
            self.pacman_next_direction = [chosen_direction[0], chosen_direction[1]]
            
            # Recalculate path after detour
            self.path_to_goal = []
        else:
            print("Không tìm được hướng an toàn!")

    def move_toward_goal(self):
        """Đi tới goal hiện tại theo đường đã tính"""
        if not self.path_to_goal or len(self.path_to_goal) <= 1:
            print("Không có đường - đứng im")
            return
        
        # Dọn đường đi - bỏ waypoint hiện tại nếu đã đến
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
            
        # Lấy điểm đích tiếp theo trên đường
        next_row, next_col = self.path_to_goal[0]  # Always use first position in path
        
        # print(f"Current: ({current_row}, {current_col}) → Target: ({next_row}, {next_col})")  # Reduced verbosity
        
        # Calculate direction to move
        dx = next_col - current_col  
        dy = next_row - current_row  
        
        # Logic hướng đơn giản - đi từng bước
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
        """Kiểm tra Pacman đã tới auto target hiện tại chưa"""
        if not self.auto_target:
            return True

        pacman_col, pacman_row = self.pacman_pos[0], self.pacman_pos[1]
        target_row, target_col = self.auto_target

        # Lưu ý: auto_target dạng (row, col), pacman_pos dạng [col, row]
        return abs(pacman_col - target_col) < 1 and abs(pacman_row - target_row) < 1

    def is_wall(self, col, row):
        """Kiểm tra vị trí có phải tường (phiên bản nghiêm ngặt)"""
        # Đảm bảo toạ độ trong biên
        if not (0 <= row < self.maze_gen.height and 0 <= col < self.maze_gen.width):
            return True  # Out of bounds = wall
        
        # Kiểm tra có phải tường (ô xanh)
        return self.maze[row, col] == 1
    
    def is_valid_position(self, col, row):
        """Kiểm tra vị trí hợp lệ để di chuyển (chỉ ô đen)"""
        # Đổi float sang int để kiểm tra
        check_col, check_row = int(round(col)), int(round(row))
        
        # Phải trong biên
        if not (0 <= check_row < self.maze_gen.height and 0 <= check_col < self.maze_gen.width):
            return False
            
        # Phải là ô đường đi (ô đen, không phải tường xanh)
        return self.maze[check_row, check_col] == 0

    def can_pacman_pass_through_ghost(self, ghost):
        """
        Kiểm tra Pacman có thể đi xuyên qua ghost không
        Trả về True nếu ghost đã bị ăn (eyes) HOẶC đang sợ và còn nhiều thời gian sợ
        """
        if ghost.get('eaten', False):
            return True

        if ghost.get('scared', False):
            blink_threshold = getattr(config, 'SCARED_BLINK_THRESHOLD_FRAMES', 120)
            return ghost.get('scared_timer', 0) > blink_threshold

        return False

    def is_scared_expiring(self, ghost):
        """Trả về True nếu ghost đang sợ nhưng gần hết thời gian sợ (cần né lại)."""
        if not ghost.get('scared', False):
            return False
        blink_threshold = getattr(config, 'SCARED_BLINK_THRESHOLD_FRAMES', 120)
        return ghost.get('scared_timer', 0) <= blink_threshold

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
        """Phát hiện va chạm tối ưu với phân vùng lưới"""
        # Lấy vị trí Pacman trên lưới (làm tròn về ô gần nhất)
        pacman_grid_col = int(round(self.pacman_pos[0]))
        pacman_grid_row = int(round(self.pacman_pos[1]))
        
        # Đồng thời lấy toạ độ pixel để đo khoảng cách
        pacman_center = (self.pacman_pos[0] * self.cell_size + self.cell_size // 2,
                        self.pacman_pos[1] * self.cell_size + self.cell_size // 2)

        # TỐI ƯU: Chỉ kiểm tra hạt trong khoảng cách hợp lý (2 ô ≈ 60px)
        max_check_distance = config.COLLISION_CHECK_DISTANCE if hasattr(config, 'COLLISION_CHECK_DISTANCE') else 60
        
        # Đặt lại bộ đếm va chạm
        self.collision_checks_per_frame = 0
        
        # Kiểm tra hạt với phát hiện dựa trên lưới
        for dot in self.dots[:]:
            # Tính vị trí hạt trên lưới từ toạ độ pixel
            dot_grid_col = int(dot[0] / self.cell_size)
            dot_grid_row = int(dot[1] / self.cell_size)
            
            # Kiểm tra Pacman cùng ô hoặc lân cận
            grid_distance = abs(pacman_grid_col - dot_grid_col) + abs(pacman_grid_row - dot_grid_row)
            
            # If in same cell or adjacent cell, do precise check
            if grid_distance <= 1:
                # Ưu tiên kiểm tra khoảng cách nhanh (rẻ hơn hypot)
                dx = abs(pacman_center[0] - dot[0])
                dy = abs(pacman_center[1] - dot[1])
                
                # Chỉ tăng đếm khi thực hiện phép tính tốn kém
                self.collision_checks_per_frame += 1
                    
                # Tăng bán kính phát hiện từ 10 lên 15 để ăn hạt tốt hơn
                distance = math.hypot(dx, dy)
                if distance < 15:
                    self.dots.remove(dot)
                    self.score += 10

        # Kiểm tra power pellet với tối ưu tương tự
        for pellet in self.power_pellets[:]:
            # Tính vị trí pellet trên lưới từ toạ độ pixel
            pellet_grid_col = int(pellet[0] / self.cell_size)
            pellet_grid_row = int(pellet[1] / self.cell_size)
            
            # Kiểm tra Pacman cùng ô hoặc lân cận
            grid_distance = abs(pacman_grid_col - pellet_grid_col) + abs(pacman_grid_row - pellet_grid_row)
            
            # Nếu cùng/giáp ô thì kiểm tra kỹ
            if grid_distance <= 1:
                # Ưu tiên kiểm tra nhanh
                dx = abs(pacman_center[0] - pellet[0])
                dy = abs(pacman_center[1] - pellet[1])
                
                # Chỉ tăng đếm khi tính toán tốn kém
                self.collision_checks_per_frame += 1
                    
                # Tăng bán kính phát hiện từ 10 lên 15 để ăn pellet tốt hơn
                distance = math.hypot(dx, dy)
                if distance < 15:
                    self.power_pellets.remove(pellet)
                    self.score += 50

                    # Phát âm thanh wakawaka khi ăn power pellet
                    if hasattr(self, 'play_wakawaka'):
                        self.play_wakawaka()

                    # Kích hoạt power mode
                    self.power_mode_end_time = pygame.time.get_ticks() + 5000  # 5 seconds

                    # Làm toàn bộ ma sợ
                    for ghost in self.ghosts:
                        ghost['scared'] = True
                        ghost['scared_timer'] = 600  # 10 seconds at 60 FPS

        # Kiểm tra va chạm bom - dính bom mất mạng (chỉ khi bật bom)
        if self.bombs_enabled:
            for bomb in self.bombs[:]:
                distance = math.hypot(pacman_center[0] - bomb[0], pacman_center[1] - bomb[1])
                if distance < 12:  # Bomb collision distance
                    print("Trúng bom! Mất mạng!")
                    self.lives -= 1
                    self.last_death_cause = "Bom nổ"  # Track death cause
                    if self.lives <= 0:
                        self.death_time = pygame.time.get_ticks()  # Save death time
                        self.game_state = "game_over"
                        # Update high score
                        if self.score > self.high_score:
                            self.high_score = self.score
                        # Set motivational message only once when game over
                        if not self.game_over_message:
                            motivational_messages = [
                                " Đừng bỏ cuộc, hãy thử lại!",
                                " Thất bại là mẹ của thành công!",
                                " Lần sau sẽ tốt hơn!",
                                " Hãy học hỏi và phát triển!",
                                "✨ Mỗi kết thúc là một khởi đầu mới!",
                                " Kiên trì sẽ vượt mọi trở ngại!",
                                " Màn trở lại luôn mạnh mẽ hơn!",
                                "⭐ Bạn gần thành công hơn bạn nghĩ!"
                            ]
                            self.game_over_message = random.choice(motivational_messages)
                    else:
                        self.reset_positions()
                    break  # Only lose one life per collision check

        # CHỈ KIỂM TRA: Va chạm với ma - tăng bán kính phát hiện
        # Bỏ qua kiểm tra khi tắt ma
        if self.ghosts_enabled:
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
                        print(f"Ăn ma {ghost['name']}! +200 điểm")
                        
                        # Set ghost to eaten state (only eyes visible)
                        ghost['eaten'] = True
                        ghost['scared'] = False
                        ghost['scared_timer'] = 0
                        
                        # === RESET AVOIDANCE MODES ===
                        # Khi ăn ma, reset tất cả các mode tránh ma để Pacman tiếp tục đi
                        if hasattr(self, 'pacman_ai'):
                            if hasattr(self.pacman_ai, 'escape_mode'):
                                self.pacman_ai.escape_mode = False
                            if hasattr(self.pacman_ai, 'escape_steps'):
                                self.pacman_ai.escape_steps = 0
                            # Chuyển về state NORMAL để có thể tìm goal mới
                            if hasattr(self.pacman_ai, '_transition_to_state') and hasattr(self.pacman_ai, 'STATE_NORMAL'):
                                self.pacman_ai._transition_to_state(self.pacman_ai.STATE_NORMAL)
                        self.ghost_avoidance_active = False
                        self.goal_locked = False  # Cho phép tìm goal mới
                        self.goal_cooldown = 0  # Reset cooldown để tìm goal ngay
                        
                        # Tính toán đường đi mới ngay lập tức
                        self.find_goal_first()
                        if self.current_goal:
                            self.goal_locked = True
                            print(f"→ Tìm goal mới sau khi ăn ma: {self.current_goal}")
                        
                        # Ma sẽ quay về spawn dưới dạng mắt
                        # LƯU Ý: Break sau khi ăn một con để tránh nhiều va chạm trong cùng frame
                        break
                    else:
                        # Va chạm ma thường - mất mạng nhưng giữ điểm
                        print(f"Pacman chạm ma thường! Mất 1 mạng. Còn lại: {self.lives - 1}")
                        self.lives -= 1
                        self.last_death_cause = f"Ma {ghost['name']}"  # Track death cause with ghost name
                        
                        # Ghi log lần chết vào visualizer
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
                            print("Game Over! Hết mạng.")
                            # Update high score
                            if self.score > self.high_score:
                                self.high_score = self.score
                            # Set motivational message only once when game over
                            if not self.game_over_message:
                                motivational_messages = [
                                    " Đừng bỏ cuộc, hãy thử lại!",
                                    " Thất bại là mẹ của thành công!",
                                    " Lần sau sẽ tốt hơn!",
                                    " Hãy học hỏi và phát triển!",
                                    "✨ Mỗi kết thúc là một khởi đầu mới!",
                                    " Kiên trì sẽ vượt mọi trở ngại!",
                                    " Màn trở lại luôn mạnh mẽ hơn!",
                                    "⭐ Bạn gần thành công hơn bạn nghĩ!"
                                ]
                                self.game_over_message = random.choice(motivational_messages)
                        else:
                            # Reset positions but keep score and game state
                            self.reset_positions_after_death()
                        # LƯU Ý: Break sau khi mất mạng để tránh chết nhiều lần trong cùng frame
                        break

        # Kiểm tra va chạm cổng thoát (điều kiện thắng)
        if hasattr(self, 'exit_gate'):
            gate_row, gate_col = self.exit_gate
            gate_center = ((gate_col + 0.5) * self.cell_size, (gate_row + 0.5) * self.cell_size)
            gate_distance = math.hypot(pacman_center[0] - gate_center[0], 
                                     pacman_center[1] - gate_center[1])
            if gate_distance < 20:  # Slightly larger than ghost collision
                self.game_state = "level_complete"
                self.score += 1000  # Bonus for completing level

        # Kiểm tra điều kiện thắng
        if not self.dots and not self.power_pellets:
            self.level += 1
            self.generate_level()
            self.place_dots_and_pellets()
            self.reset_positions()

    def reset_positions(self):
        """Đặt lại vị trí Pacman và ma về điểm xuất phát - ma đặt ngẫu nhiên và cách xa Pacman"""
        # Đặt Pacman về vị trí start của mê cung (ô đen đảm bảo hợp lệ)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        self.auto_path = []
        self.auto_target = None
        
        # Kiểm tra vị trí Pacman có hợp lệ
        if not self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
            # Tìm vị trí hợp lệ đầu tiên
            for row in range(self.maze_gen.height):
                for col in range(self.maze_gen.width):
                    if self.is_valid_position(col, row):
                        self.pacman_pos = [float(col), float(row)]
                        break
                if self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
                    break

        # Tìm tất cả vị trí hợp lệ cho ma
        all_valid_positions = []
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                if self.is_valid_position(col, row):
                    all_valid_positions.append([float(col), float(row)])  # Lưu dưới dạng float
        
        # Lọc các vị trí đủ xa Pacman (tối thiểu 8 ô)
        min_distance_from_pacman = 8
        safe_positions = []
        
        for pos in all_valid_positions:
            distance = abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1])  # Manhattan distance
            if distance >= min_distance_from_pacman:
                safe_positions.append(pos)
        
        # Nếu không đủ vị trí an toàn, dùng toàn bộ vị trí hợp lệ nhưng sắp xếp theo khoảng cách
        if len(safe_positions) < 4:
            # Sort by distance from Pacman (farthest first)
            all_valid_positions.sort(key=lambda pos: abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1]), reverse=True)
            safe_positions = all_valid_positions
        
        # Xáo trộn ngẫu nhiên các vị trí an toàn
        random.shuffle(safe_positions)
        
        # Đặt ma tại vị trí trung tâm hợp lệ và để chúng tản ra
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)

        # If can't find valid ghost position, use Pacman's position as fallback
        if not ghost_start_pos:
            print(" Không tìm được vị trí bắt đầu hợp lệ cho ma, dùng vị trí Pacman")
            ghost_start_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))

        for i, ghost in enumerate(self.ghosts[:4]):  # Ensure only 4 ghosts
            # All ghosts start at the same valid center position
            ghost['pos'] = [float(ghost_start_pos[1]), float(ghost_start_pos[0])]  # [col, row] format

            # Đặt lại trạng thái của ma
            ghost['direction'] = [0, 0]
            ghost['mode'] = 'random'  # Bắt đầu ở mode ngẫu nhiên để tản ra
            ghost['target'] = None
            ghost['last_direction_change'] = 0
            ghost['position_history'] = []
            ghost['stuck_counter'] = 0
            ghost['last_position'] = None
            ghost['random_timer'] = 0
            ghost['spread_timer'] = 0

    def reset_positions_after_death(self):
        """Đặt lại vị trí Pacman và ma sau khi chết - giữ nguyên điểm và trạng thái"""
        print("Đang đặt lại vị trí sau khi chết...")

        # Set Pacman to maze start position (guaranteed black cell)
        start_row, start_col = self.start
        self.pacman_pos = [float(start_col), float(start_row)]  # Convert (row,col) to [col,row] as floats
        self.pacman_direction = [0, 0]
        self.pacman_next_direction = [0, 0]
        
        # Reset AI state để tránh lỗi và cho phép bật auto mode lại
        if hasattr(self, 'pacman_ai'):
            self.pacman_ai.reset()

        # Đặt lại biến auto mode nhưng vẫn giữ auto nếu đang bật
        if self.auto_mode:
            self.auto_path = []
            self.auto_target = None
            self.current_goal = None
            self.goal_locked = False
            self.goal_cooldown = 0
            self.ghost_avoidance_active = False

        # Kiểm tra vị trí Pacman có hợp lệ
        if not self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
            # Find first valid position
            for row in range(self.maze_gen.height):
                for col in range(self.maze_gen.width):
                    if self.is_valid_position(col, row):
                        self.pacman_pos = [float(col), float(row)]
                        break
                if self.is_valid_position(self.pacman_pos[0], self.pacman_pos[1]):
                    break

        # Tìm tất cả vị trí hợp lệ cho ma
        all_valid_positions = []
        for row in range(self.maze_gen.height):
            for col in range(self.maze_gen.width):
                if self.is_valid_position(col, row):
                    all_valid_positions.append([float(col), float(row)])  # Lưu dưới dạng float

        # Lọc các vị trí đủ xa Pacman (khoảng cách tối thiểu = 8 ô)
        min_distance_from_pacman = 8
        safe_positions = []

        for pos in all_valid_positions:
            distance = abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1])  # Manhattan distance
            if distance >= min_distance_from_pacman:
                safe_positions.append(pos)

        # Nếu không đủ vị trí an toàn, dùng toàn bộ vị trí hợp lệ nhưng sắp xếp theo khoảng cách
        if len(safe_positions) < 4:
            # Sort by distance from Pacman (farthest first)
            all_valid_positions.sort(key=lambda pos: abs(pos[0] - self.pacman_pos[0]) + abs(pos[1] - self.pacman_pos[1]), reverse=True)
            safe_positions = all_valid_positions

        # Xáo trộn ngẫu nhiên các vị trí an toàn
        random.shuffle(safe_positions)

        # Đặt ma tại vị trí trung tâm hợp lệ và để chúng tản ra
        center_row = self.maze_gen.height // 2
        center_col = self.maze_gen.width // 2
        ghost_start_pos = self.find_valid_ghost_start_position(center_row, center_col)

        # Nếu không tìm được vị trí hợp lệ cho ma, dùng vị trí của Pacman
        if not ghost_start_pos:
            print(" Không tìm được vị trí bắt đầu hợp lệ cho ma, dùng vị trí Pacman")
            ghost_start_pos = (int(self.pacman_pos[1]), int(self.pacman_pos[0]))

        for i, ghost in enumerate(self.ghosts[:4]):  # Ensure only 4 ghosts
            # All ghosts start at the same valid center position
            ghost['pos'] = [float(ghost_start_pos[1]), float(ghost_start_pos[0])]  # [col, row] format

            # Đặt lại trạng thái của ma
            ghost['direction'] = [0, 0]
            ghost['mode'] = 'random'  # Bắt đầu ở mode ngẫu nhiên để tản ra
            ghost['target'] = None
            ghost['last_direction_change'] = 0
            ghost['position_history'] = []
            ghost['stuck_counter'] = 0
            ghost['last_position'] = None
            ghost['random_timer'] = 0
            ghost['spread_timer'] = 0
            # Giữ nguyên trạng thái sợ nếu ma đang sợ
            if not ghost.get('scared', False):
                ghost['scared_timer'] = 0

        print(f"Đặt lại vị trí - Pacman về điểm start, ma được xếp lại. Điểm: {self.score}, Mạng: {self.lives}")

    def handle_events(self):
        """Xử lý input từ người chơi"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # print(f"Phím bấm: {pygame.key.name(event.key)}")
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Visualizer controls
                elif event.key == pygame.K_v:
                    if self.visualizer:
                        self.visualizer.toggle_visualization()
                    else:
                        print("Không có visualizer")
                
                elif event.key == pygame.K_b:
                    if self.visualizer:
                        self.visualizer.print_real_time_analysis()
                    else:
                        print("Không có visualizer")
                
                elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if self.visualizer:
                        self.visualizer.save_analysis_report()
                    else:
                        print("Không có visualizer")
                
                elif event.key == pygame.K_p:
                    self.game_state = "paused" if self.game_state == "playing" else "playing"
                elif event.key == pygame.K_a:
                    self.toggle_auto_mode()
                # Điều chỉnh tốc độ auto mode
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    # Tăng tốc độ
                    if self.auto_speed_index < len(config.AUTO_MODE_SPEED_LEVELS) - 1:
                        self.auto_speed_index += 1
                        multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                        print(f"⚡ Tốc độ auto: {multiplier}x")
                elif event.key == pygame.K_MINUS:
                    # Giảm tốc độ
                    if self.auto_speed_index > 0:
                        self.auto_speed_index -= 1
                        multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                        print(f"🐌 Tốc độ auto: {multiplier}x")
                elif event.key == pygame.K_0:
                    # Reset về tốc độ mặc định
                    self.auto_speed_index = config.AUTO_MODE_DEFAULT_SPEED_INDEX
                    multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                    print(f"🔄 Reset tốc độ auto: {multiplier}x")
                elif event.key == pygame.K_h:
                    self.show_shortest_path = not self.show_shortest_path
                    if self.show_shortest_path:
                        # Luôn hiển thị đường đi đến EXIT GATE (goal chính)
                        self.calculate_hint_path_to_exit()
                        # print("Đường gợi ý đến EXIT: BẬT (nhấn H để tắt)")
                    else:
                        self.shortest_path = []
                        # print("Hint path visualization: OFF")
                elif event.key == pygame.K_f:
                    self.show_fps_info = not self.show_fps_info
                    print(f"Thông tin FPS: {'BẬT' if self.show_fps_info else 'TẮT'}")
                elif event.key == pygame.K_x:
                    self.bombs_enabled = not self.bombs_enabled
                    status = "ON" if self.bombs_enabled else "OFF"
                    print(f" Bom: {status}")
                elif event.key == pygame.K_g:
                    self.ghosts_enabled = not self.ghosts_enabled
                    status = "ON" if self.ghosts_enabled else "OFF"
                    print(f" Ma: {status}")
                elif event.key == pygame.K_d:
                    config.ENABLE_DYNAMIC_SPEED = not config.ENABLE_DYNAMIC_SPEED
                    status = "ON" if config.ENABLE_DYNAMIC_SPEED else "OFF"
                    print(f"Điều chỉnh tốc độ động: {status}")
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
        """Khởi động lại toàn bộ game, giữ đúng 4 con ma"""
        print("ĐANG KHỞI ĐỘNG LẠI GAME - Đặt lại toàn bộ trạng thái...")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None
        
        # Reset AI state để có thể bật auto mode lại
        if hasattr(self, 'pacman_ai'):
            self.pacman_ai.reset()

        # Đặt lại thông báo game over cho lần sau
        self.game_over_message = None
        self.last_death_cause = None
        self.death_time = None  # Đặt lại thời gian chết

        # Xoá cờ auto để đảm bảo quay về điều khiển tay sau khi restart
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

        print("Đang tạo level mới...")
        self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Tạo mê cung thất bại, thử lại...")
            # Try one more time
            self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Vẫn thất bại khi tạo mê cung, dùng phương án dự phòng")
            # Fallback: create a simple maze
            import numpy as np
            self.maze = np.zeros((self.maze_gen.height, self.maze_gen.width), dtype=int)
            self.start = (1, 1)
            self.goal = (self.maze_gen.height - 2, self.maze_gen.width - 2)

        print("Đang đặt hạt và power pellet...")
        self.place_dots_and_pellets()
        
        # Bombs are already generated in maze generation - no need to place again
        print("Đang tải bom từ maze generator...")
        self.load_bombs_from_maze_generator()

        print("Đang tạo/đặt lại ma...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("Đang đặt lại vị trí...")
        self.reset_positions()

        print("Khởi động lại thành công - Auto: TẮT, điều khiển tay!")

    def next_level(self):
        """Sang level tiếp theo"""
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
        
        # Load bombs từ maze generator (QUAN TRỌNG: phải load trước reset_positions)
        self.load_bombs_from_maze_generator()
        
        self.reset_positions()

    def create_new_game(self):
        """Tạo ván mới với bản đồ ngẫu nhiên"""
        print("Đang tạo ván mới với bản đồ ngẫu nhiên...")

        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.auto_mode = False
        self.auto_path = []
        self.auto_target = None
        
        # Reset AI state để có thể bật auto mode lại
        if hasattr(self, 'pacman_ai'):
            self.pacman_ai.reset()

        # Xoá cờ auto để đảm bảo điều khiển tay sau khi tạo ván mới
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

        print("Đang tạo level ngẫu nhiên mới...")
        self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Tạo mê cung thất bại, thử lại...")
            # Try one more time
            self.generate_level()

        if not hasattr(self, 'start') or not hasattr(self, 'goal'):
            print("Vẫn thất bại khi tạo mê cung, dùng phương án dự phòng")
            # Fallback: create a simple maze
            import numpy as np
            self.maze = np.zeros((self.maze_gen.height, self.maze_gen.width), dtype=int)
            self.start = (1, 1)
            self.goal = (self.maze_gen.height - 2, self.maze_gen.width - 2)

        print("Đang đặt hạt và power pellet...")
        self.place_dots_and_pellets()
        
        # Bombs are already generated in maze generation - no need to place again
        print("Đang tải bom từ maze generator...")
        self.load_bombs_from_maze_generator()

        print("Đang tạo/đặt lại ma...")
        # Always recreate ghosts to ensure clean state
        self.ghosts = []
        self.create_ghosts()

        print("Đang đặt lại vị trí...")
        self.reset_positions()

        print("Tạo ván mới thành công!")

    def update(self):
        """Cập nhật trạng thái game với chuyển động độc lập FPS"""
        current_time = pygame.time.get_ticks()
        raw_delta_time = (current_time - self.last_update) / 1000.0  # Convert to seconds
        
        # Giới hạn delta time để tránh bước nhảy lớn khi pause/lag
        self.delta_time = min(raw_delta_time, self.max_delta_time)
        self.last_update = current_time
        
        # Theo dõi FPS để giám sát hiệu năng
        if raw_delta_time > 0:
            current_fps = 1.0 / raw_delta_time
            self.fps_history.append(current_fps)
            if len(self.fps_history) > 60:  # Keep last 60 frames
                self.fps_history.pop(0)
        
        # Cập nhật visualizer với trạng thái AI hiện tại
        if self.visualizer and hasattr(self, 'pacman_ai'):
            try:
                self.visualizer.update(self.pacman_ai)
            except Exception as e:
                pass  # Silent fail to not disrupt gameplay

        # ĐẢM BẢO AUTO CHỈ BẬT KHI NGƯỜI CHƠI CHỦ ĐỘNG
        if self.auto_mode and not hasattr(self, '_user_enabled_auto'):
            print("CẢNH BÁO: Auto bật ngoài ý muốn, chuyển về điều khiển tay")
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
                    # Áp dụng hệ số tốc độ auto mode - timer giảm nhanh hơn khi tăng tốc
                    timer_decrement = 1
                    if self.auto_mode:
                        auto_speed_multiplier = config.AUTO_MODE_SPEED_LEVELS[self.auto_speed_index]
                        timer_decrement = auto_speed_multiplier  # Giảm nhanh hơn khi tăng tốc
                    
                    ghost['scared_timer'] -= timer_decrement
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

            # Animate Pacman mouth - smooth sine wave animation
            self.animation_timer += 1
            if self.animation_timer >= 8:  #Faster animation pacman mouth
                self.pacman_mouth_open = not self.pacman_mouth_open
                self.animation_timer = 0
            
            # Smooth mouth cycle for better animation
            self.pacman_mouth_cycle += 0.15
            if self.pacman_mouth_cycle >= 2 * math.pi:
                self.pacman_mouth_cycle = 0
            
            # Power pellet pulse animation
            self.pellet_pulse_timer += 0.1
            if self.pellet_pulse_timer >= 2 * math.pi:
                self.pellet_pulse_timer = 0

    def draw_ghost_return_paths(self):
        """Vẽ đường quay về cho ma đã bị ăn (chỉ mắt)"""
        # Bỏ qua nếu tắt ma
        if not self.ghosts_enabled:
            return
            
        for ghost in self.ghosts:
            if ghost.get('eaten', False) and hasattr(ghost, 'return_path') and ghost['return_path']:
                path = ghost['return_path']
                
                # Vẽ đường bằng chấm trắng
                for i, (row, col) in enumerate(path):
                    center = ((col + 0.5) * self.cell_size, (row + 0.5) * self.cell_size)
                    
                    # Vẽ chấm nhỏ cho đường về của ma
                    if i % 2 == 0:  # Draw every other dot for dotted effect
                        pygame.draw.circle(self.screen, (200, 200, 200), center, 2)  # Light gray
                
                # Tô sáng waypoint mục tiêu hiện tại
                if hasattr(ghost, 'path_index') and ghost['path_index'] < len(path):
                    target_waypoint = path[ghost['path_index']]
                    target_row, target_col = target_waypoint
                    target_center = ((target_col + 0.5) * self.cell_size, (target_row + 0.5) * self.cell_size)
                    pygame.draw.circle(self.screen, (255, 255, 255), target_center, 4)  # White target

    def draw(self):
        """Vẽ toàn bộ khung hình"""
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
        
        # Vẽ thông tin FPS nếu bật
        if self.show_fps_info:
            self.draw_fps_info()
        
        # Vẽ overlay của visualizer nếu có
        if self.visualizer:
            try:
                self.visualizer.render(self.screen, self.cell_size)
            except Exception as e:
                pass  # Silent fail to not disrupt gameplay
        
        # Vẽ thông báo trạng thái ở lớp trên cùng
        if self.game_state == "game_over":
            self.draw_game_over_notification()
        elif self.game_state == "level_complete":
            self.draw_win_notification()
            
        pygame.display.flip()

    def toggle_auto_mode(self):
        """Chuyển giữa điều khiển tay và tự động"""
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            print("Bật auto - Pacman sẽ tự chơi!")
            self._user_enabled_auto = True  # Đánh dấu người chơi đã bật auto
            self.find_auto_target()
        else:
            print("Bật điều khiển tay - Bạn điều khiển Pacman!")
            if hasattr(self, '_user_enabled_auto'):
                delattr(self, '_user_enabled_auto')  # Xoá cờ khi tắt
            self.auto_path = []
            self.auto_target = None
            self.pacman_direction = [0, 0]
            self.pacman_next_direction = [0, 0]

    def run(self):
        """Vòng lặp chính với FPS cấu hình"""
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
                self.clock.tick(self.target_fps)  # Use configurable FPS
        except KeyboardInterrupt:
            print("\nGame bị dừng bởi người chơi")
        except Exception as e:
            print(f" Lỗi khi chạy game: {e}")
        finally:
            # Dọn dẹp
            print("Đang giải phóng tài nguyên...")
            try:
                pygame.mixer.quit()  # Gọi an toàn kể cả khi mixer chưa init
            except:
                pass
            pygame.quit()
            print("Thoát game thành công")
            sys.exit(0)

    def get_bomb_grid_positions(self):
        """Chuyển toạ độ pixel của bom sang ô lưới"""
        # Trả về tập rỗng nếu tắt bom
        if not self.bombs_enabled:
            return set()
        
        bomb_grid = set()
        for bomb in self.bombs:
            bomb_x, bomb_y = bomb
            # Use round() for accurate conversion from center position
            grid_col = round(bomb_x / self.cell_size - 0.5)
            grid_row = round(bomb_y / self.cell_size - 0.5)
            bomb_grid.add((grid_row, grid_col))
        
        # Debug output (rate limited)
        if not hasattr(self, '_last_bomb_grid_log'):
            self._last_bomb_grid_log = 0
        current_time = pygame.time.get_ticks()
        if current_time - self._last_bomb_grid_log > 5000:  # Every 5 seconds
            if bomb_grid:
                print(f" Bomb ({len(bomb_grid)}): {list(bomb_grid)[:3]}...")
            self._last_bomb_grid_log = current_time
        
        return bomb_grid

if __name__ == "__main__":
    game = PacmanGame()
    game.run()

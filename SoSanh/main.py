import math
import pygame
import time
from maze_generator import MazeGenerator
from algorithms import dijkstra, astar

# =============================
# Soft Neon Button (Đậm)
# =============================
class SoftButton:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = pygame.font.SysFont("segoeui", 22)

        self.bg = (28, 28, 44)
        self.hover_bg = (58, 48, 85)
        self.text_color = (235, 235, 255)
        self.border = (122, 92, 255)

    def draw(self, screen):
        mouse = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse)

        color = self.hover_bg if is_hover else self.bg
        pygame.draw.rect(screen, color, self.rect, border_radius=10)

        pygame.draw.rect(screen, self.border, self.rect, width=2, border_radius=10)

        if is_hover:
            glow = pygame.Surface((self.rect.width + 16, self.rect.height + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (122, 92, 255, 45), glow.get_rect(), border_radius=12)
            screen.blit(glow, (self.rect.x - 8, self.rect.y - 8))

        txt = self.font.render(self.text, True, self.text_color)
        screen.blit(txt, (
            self.rect.centerx - txt.get_width() // 2,
            self.rect.centery - txt.get_height() // 2,
        ))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)


# ======================================================
# Dropdown Select Mode Button
# ======================================================
class DropdownButton:
    def __init__(self, x, y, w, h):
        self.main_rect = pygame.Rect(x, y, w, h)
        self.font = pygame.font.SysFont("segoeui", 22)

        self.bg = (28, 28, 44)
        self.hover_bg = (58, 48, 85)
        self.border = (122, 92, 255)
        self.text_color = (235, 235, 255)

        self.options = ["Dijkstra", "A*", "Compare"]
        self.current = "Compare"
        self.open = False

        self.option_rects = [
            pygame.Rect(x, y + h + i * h, w, h)
            for i in range(len(self.options))
        ]

    def draw(self, screen):
        mouse = pygame.mouse.get_pos()
        is_hover = self.main_rect.collidepoint(mouse)

        color = self.hover_bg if is_hover else self.bg
        pygame.draw.rect(screen, color, self.main_rect, border_radius=10)
        pygame.draw.rect(screen, self.border, self.main_rect, 2, border_radius=10)

        txt = self.font.render("Mode: " + self.current, True, self.text_color)
        screen.blit(txt, (
            self.main_rect.centerx - txt.get_width() // 2,
            self.main_rect.centery - txt.get_height() // 2,
        ))

        if self.open:
            for i, opt_rect in enumerate(self.option_rects):
                pygame.draw.rect(screen, self.bg, opt_rect, border_radius=8)
                pygame.draw.rect(screen, self.border, opt_rect, 2, border_radius=8)

                txt2 = self.font.render(self.options[i], True, self.text_color)
                screen.blit(txt2, (
                    opt_rect.centerx - txt2.get_width() // 2,
                    opt_rect.centery - txt2.get_height() // 2,
                ))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.main_rect.collidepoint(event.pos):
                self.open = not self.open
                return None

            if self.open:
                for i, opt_rect in enumerate(self.option_rects):
                    if opt_rect.collidepoint(event.pos):
                        self.current = self.options[i]
                        self.open = False
                        return self.current
        return None


# =============================
# Config
# =============================
PADDING = 20
GAP = 40
FPS = 60
TOP_RESERVED = 180

# Fixed frame size for maze scaling
MAZE_FRAME_W = 600
MAZE_FRAME_H = 600

BG_COLOR = (0, 0, 10)
DIJ_RADAR_COLOR = (120, 220, 255)   # xanh ngọc sáng dịu
AST_RADAR_COLOR = (255, 170, 230)   # tím hồng pastel

DIJ_PATH_COLOR  = (255, 230, 120)   # vàng kem, nổi bật
AST_PATH_COLOR  = (120, 255, 170)   # xanh mint cho A*

HUD_COLOR = (220, 220, 240)

# Soft Maze Theme (dịu mắt)
PAC_WALL_COLOR        = (32, 36, 68)     # xanh tím VERY soft
PAC_WALL_BORDER       = (90, 105, 150)   # viền nhẹ, không chói
PAC_PATH_BG           = BG_COLOR         # giữ nền hiện tại
PAC_PELLET_COLOR      = (200, 200, 220)  # hạt xám sáng nhẹ
PAC_ROBOT_COLOR       = (255, 215, 120)  # vàng kem thay vì vàng neon



MOVE_DELAY = 0.05
SCAN_DELAY = 0.8
PAUSED = False

CELL_SIZE = 20  # auto override later


# =============================
# Drawing
# =============================

def draw_maze(surface, maze, start, goal, ox, oy):
    rows, cols = maze.shape
    sr, sc = start
    gr, gc = goal

    for r in range(rows):
        for c in range(cols):
            x = ox + c * CELL_SIZE
            y = oy + r * CELL_SIZE

            if maze[r, c] == 1:
                # Ô tường – vẽ kiểu Pacman
                pygame.draw.rect(surface, PAC_WALL_COLOR, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(surface, PAC_WALL_BORDER, (x, y, CELL_SIZE, CELL_SIZE), 1)
            else:
                # Ô đường – nền tối, có pellet
                # (background tổng thể đã là BG_COLOR nên không cần fill cả ô)
                # Vẽ hạt ở giữa ô, trừ start/goal
                if (r, c) != start and (r, c) != goal:
                    radius = max(2, CELL_SIZE //10)
                    pygame.draw.circle(
                        surface,
                        PAC_PELLET_COLOR,
                        (x + CELL_SIZE // 2, y + CELL_SIZE // 2),
                        radius
                    )

    # Start – ô màu vàng (giống điểm spawn Pacman)
    sx = ox + sc * CELL_SIZE
    sy = oy + sr * CELL_SIZE
    pygame.draw.rect(surface, (255, 230, 90), (sx, sy, CELL_SIZE, CELL_SIZE))
    pygame.draw.rect(surface, PAC_WALL_BORDER, (sx, sy, CELL_SIZE, CELL_SIZE), 2)

    # Goal – ô màu xanh lá (giống cổng/fruit)
    gx = ox + gc * CELL_SIZE
    gy = oy + gr * CELL_SIZE
    pygame.draw.rect(surface, (130, 255, 130), (gx, gy, CELL_SIZE, CELL_SIZE))
    pygame.draw.rect(surface, PAC_WALL_BORDER, (gx, gy, CELL_SIZE, CELL_SIZE), 2)



def draw_robot(surface, path, idx, ox, oy, color=None):
    if idx >= len(path):
        return

    r, c = path[idx]
    cx = ox + c * CELL_SIZE + CELL_SIZE // 2
    cy = oy + r * CELL_SIZE + CELL_SIZE // 2
    radius = CELL_SIZE // 2 - 2

    if color is None:
        color = PAC_ROBOT_COLOR

    # Vẽ Pacman: hình quạt tròn (sector)
    mouth_angle = math.pi / 4   # góc miệng
    start_angle = mouth_angle
    end_angle = 2 * math.pi - mouth_angle

    # Vẽ hình tròn đầy trước (fallback nếu muốn đơn giản)
    pygame.draw.circle(surface, color, (cx, cy), radius)

    # Vẽ “miệng” bằng cách phủ tam giác màu nền
    x1, y1 = cx, cy
    x2 = cx + int(radius * math.cos(start_angle))
    y2 = cy - int(radius * math.sin(start_angle))
    x3 = cx + int(radius * math.cos(end_angle))
    y3 = cy - int(radius * math.sin(end_angle))

    pygame.draw.polygon(surface, BG_COLOR, [(x1, y1), (x2, y2), (x3, y3)])


def draw_radar(surface, explored, ox, oy, base_color, upto):
    """
    Hiển thị rõ:
    - Tất cả ô đã quét: nền màu nhạt
    - Ô đang quét: viền đậm + chấm tròn sáng
    """
    n = min(upto, len(explored))
    if n <= 0:
        return

    # 1) Tô overlay nhạt cho TẤT CẢ ô đã quét
    for i in range(n):
        r, c = explored[i]
        x = ox + c * CELL_SIZE
        y = oy + r * CELL_SIZE

        # Ô overlay bán trong suốt
        cell_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        # alpha nhỏ cho dịu mắt (40–70 tùy anh)
        cell_surf.fill((*base_color, 55))
        surface.blit(cell_surf, (x, y))

    # 2) Ô đang quét hiện tại (node cuối cùng)
    last_r, last_c = explored[n - 1]
    lx = ox + last_c * CELL_SIZE
    ly = oy + last_r * CELL_SIZE

    # Viền đậm để biết ô hiện tại
    pygame.draw.rect(surface, base_color, (lx, ly, CELL_SIZE, CELL_SIZE), 3)

    # Chấm tròn sáng ở giữa
    cx = lx + CELL_SIZE // 2
    cy = ly + CELL_SIZE // 2
    radius = max(3, CELL_SIZE // 4)

    pulse_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(pulse_surf, (*base_color, 200), (radius, radius), radius)
    surface.blit(pulse_surf, (cx - radius, cy - radius))

def draw_path(surface, path, ox, oy, color):
    if not path:
        return

    # Vẽ đường đi bằng line + chấm tròn cho dễ nhìn
    points = []
    for r, c in path:
        x = ox + c * CELL_SIZE + CELL_SIZE // 2
        y = oy + r * CELL_SIZE + CELL_SIZE // 2
        points.append((x, y))

    # Vẽ line nối các điểm
    if len(points) >= 2:
        pygame.draw.lines(surface, color, False, points, 4)

    # Vẽ chấm nhỏ trên từng ô cho rõ hơn
    for x, y in points:
        pygame.draw.circle(surface, color, (x, y), 4)


def draw_label(surface, text, x, y):
    font = pygame.font.SysFont("segoeui", 26, bold=True)
    label = font.render(text, True, (230, 230, 255))
    surface.blit(label, (x, y))


    # =============================
# HUD (Stats Card)
# =============================
def draw_hud(surface, speed, paused, mode, dij_stats, ast_stats,
             left_ox, right_ox, maze_w):
    font_title = pygame.font.SysFont("segoeui", 22, bold=True)
    font_body = pygame.font.SysFont("segoeui", 18)

    # ===== Top status line =====
    top_text = (
        f"Speed: {speed:.2f}s/step   •   "
        f"State: {'PAUSED' if paused else 'RUNNING'}   •   "
        f"Mode: {mode}"
    )

    img = font_title.render(top_text, True, HUD_COLOR)
    surface.blit(img, (surface.get_width()//2 - img.get_width()//2, 70))

    # ===== Card size =====
    card_w = 270
    card_h = 95

    # Dijkstra card position
    dij_x = left_ox + maze_w//2 - card_w//2
    dij_y = TOP_RESERVED - 50

    # A* card position
    ast_x = right_ox + maze_w//2 - card_w//2
    ast_y = TOP_RESERVED - 50

    def draw_card(x, y, title, stats, color):
        rect = pygame.Rect(x, y, card_w, card_h)
        pygame.draw.rect(surface, (20, 20, 35), rect, border_radius=12)
        pygame.draw.rect(surface, color, rect, 2, border_radius=12)

        # Title
        title_txt = font_title.render(title, True, color)
        surface.blit(title_txt, (x + 12, y + 8))

        # Stats
        steps = stats["steps"]
        nodes = stats["scanned"]      # node đã quét
        time_ms = stats["time"] * 1000

        # Hàng 1: Steps + Nodes
        surface.blit(font_body.render(f"Steps: {steps}", True, HUD_COLOR),
                     (x + 12, y + 34))
        surface.blit(font_body.render(f"Nodes: {nodes}", True, HUD_COLOR),
                     (x + 140, y + 34))

        # Hàng 2: Time + FPS
        surface.blit(font_body.render(f"Time: {time_ms:.1f} ms", True, HUD_COLOR),
                     (x + 12, y + 58))

    if mode in ["Dijkstra", "Compare"]:
        draw_card(dij_x, dij_y, "Dijkstra", dij_stats, (130, 150, 255))

    if mode in ["A*", "Compare"]:
        draw_card(ast_x, ast_y, "A*", ast_stats, (255, 160, 255))


# =============================
# Stats nội suy (giữ nguyên)
# =============================
def get_progress_stats(path, explored, idx_step, idx_scan, total_time):
    if not path or not explored:
        return {"steps": 0, "scanned": 0, "time": 0}

    total_steps = len(path)
    total_scanned = len(explored)

    steps_now = min(idx_step + 1, total_steps)
    scanned_now = min(idx_scan, total_scanned)

    move_prog = idx_step / max(1, total_steps - 1)
    scan_prog = idx_scan / max(1, total_scanned)
    progress = max(move_prog, scan_prog)

    return {
        "steps": steps_now,
        "scanned": scanned_now,
        "time": total_time * progress,
    }


# =============================
# Generate Maze + time
# =============================
def generate_valid_maze(mg):
    while True:
        maze, start, goal = mg.generate_maze()

        t0 = time.perf_counter()
        dij_path, dij_cost, dij_scan = dijkstra(mg)
        dij_time = time.perf_counter() - t0

        t1 = time.perf_counter()
        ast_path, ast_cost, ast_scan = astar(mg)
        ast_time = time.perf_counter() - t1

        if dij_path and ast_path:
            return (
                maze, start, goal,
                dij_path, ast_path,
                dij_scan, ast_scan,
                dij_time, ast_time
            )


# =============================
# MAIN
# =============================
def main():
    global MOVE_DELAY, PAUSED, CELL_SIZE

    pygame.init()
    pygame.display.set_caption("Soft Neon Maze Visualizer (Updated UI)")
    clock = pygame.time.Clock()

    mg = MazeGenerator(31, 21)

    (
        maze, start, goal,
        dij_path, ast_path,
        dij_scan, ast_scan,
        dij_time, ast_time
    ) = generate_valid_maze(mg)

    dij_total_time = dij_time
    ast_total_time = ast_time

    # -------------------------------
    # AUTO SCALE CELL SIZE
    # -------------------------------
    rows, cols = maze.shape

    cell_w = MAZE_FRAME_W // cols
    cell_h = MAZE_FRAME_H // rows
    CELL_SIZE = min(cell_w, cell_h)

    maze_w = cols * CELL_SIZE
    maze_h = rows * CELL_SIZE

    screen_w = PADDING + MAZE_FRAME_W + GAP + MAZE_FRAME_W + PADDING
    screen_h = TOP_RESERVED + MAZE_FRAME_H + 50

    screen = pygame.display.set_mode((screen_w, screen_h))

    # -------------------------------
    # Center maze inside frame
    # -------------------------------
    left_ox = PADDING + (MAZE_FRAME_W - maze_w) // 2
    left_oy = TOP_RESERVED + (MAZE_FRAME_H - maze_h) // 2

    right_frame_x = PADDING + MAZE_FRAME_W + GAP
    right_ox = right_frame_x + (MAZE_FRAME_W - maze_w) // 2
    right_oy = left_oy


    # ===========================================
    # NEW UI BUTTONS — CÙNG 1 HÀNG
    # ===========================================
    btn_mode     = DropdownButton(20, 20, 160, 45)
    btn_replay   = SoftButton(200, 20, 130, 45, "Replay")
    btn_pause    = SoftButton(340, 20, 130, 45, "Pause")
    btn_reload   = SoftButton(480, 20, 130, 45, "Reload")

    # Speed group
    btn_speed_lbl   = SoftButton(650, 20, 110, 45, "Speed")
    btn_speed_plus  = SoftButton(760, 20, 45, 45, "+")
    btn_speed_minus = SoftButton(810, 20, 45, 45, "-")

    # Maze Size group
    btn_size_lbl    = SoftButton(880, 20, 150, 45, "Maze Size")
    btn_size_plus   = SoftButton(1040, 20, 45, 45, "+")
    btn_size_minus  = SoftButton(1090, 20, 45, 45, "-")


    dij_i = ast_i = 0
    dij_scan_i = ast_scan_i = 0
    dij_scan_t = ast_scan_t = 0
    robot_t = 0
    scan_done = False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000

        # ======= GLOBAL TIME SCALE =======
        time_scale = 1.0 / MOVE_DELAY

        dij_scan_t += dt * time_scale
        ast_scan_t += dt * time_scale
        robot_t    += dt * time_scale




        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            # =============================
            # MODE change
            # =============================
            mode_change = btn_mode.handle_event(event)
            if mode_change:
                dij_i = ast_i = 0
                dij_scan_i = ast_scan_i = 0
                dij_scan_t = ast_scan_t = 0
                scan_done = False

            # =============================
            # Replay
            # =============================
            if btn_replay.is_clicked(event):
                dij_i = ast_i = 0
                dij_scan_i = ast_scan_i = len(dij_scan)
                scan_done = True

            # Pause
            if btn_pause.is_clicked(event):
                PAUSED = not PAUSED

            # Reload
            if btn_reload.is_clicked(event):
                (
                    maze, start, goal,
                    dij_path, ast_path,
                    dij_scan, ast_scan,
                    dij_time, ast_time
                ) = generate_valid_maze(mg)

                dij_total_time = dij_time
                ast_total_time = ast_time

                dij_i = ast_i = 0
                dij_scan_i = ast_scan_i = 0
                dij_scan_t = ast_scan_t = 0
                scan_done = False

            # =============================
            # SPEED
            # =============================
            if btn_speed_plus.is_clicked(event):
                MOVE_DELAY = max(0.01, MOVE_DELAY - 0.05)

            if btn_speed_minus.is_clicked(event):
                MOVE_DELAY = min(0.5, MOVE_DELAY + 0.05)

            # =============================
            # MAZE SIZE CHANGE  + AUTO SCALE
            # =============================
            if btn_size_plus.is_clicked(event):
                mg = MazeGenerator(mg.width + 2, mg.height + 2)

                (
                    maze, start, goal,
                    dij_path, ast_path,
                    dij_scan, ast_scan,
                    dij_time, ast_time
                ) = generate_valid_maze(mg)

                # RECALCULATE SCALE
                rows, cols = maze.shape
                cell_w = MAZE_FRAME_W // cols
                cell_h = MAZE_FRAME_H // rows
                CELL_SIZE = min(cell_w, cell_h)

                maze_w = cols * CELL_SIZE
                maze_h = rows * CELL_SIZE

                left_ox = PADDING + (MAZE_FRAME_W - maze_w) // 2
                left_oy = TOP_RESERVED + (MAZE_FRAME_H - maze_h) // 2

                right_ox = right_frame_x + (MAZE_FRAME_W - maze_w) // 2
                right_oy = left_oy

                dij_total_time = dij_time
                ast_total_time = ast_time

                dij_i = ast_i = 0
                dij_scan_i = ast_scan_i = 0
                dij_scan_t = ast_scan_t = 0
                scan_done = False

            # Decrease maze size
            if btn_size_minus.is_clicked(event):
                if mg.width > 9 and mg.height > 9:
                    mg = MazeGenerator(mg.width - 2, mg.height - 2)

                    (
                        maze, start, goal,
                        dij_path, ast_path,
                        dij_scan, ast_scan,
                        dij_time, ast_time
                    ) = generate_valid_maze(mg)

                    # AUTO SCALE AGAIN
                    rows, cols = maze.shape
                    cell_w = MAZE_FRAME_W // cols
                    cell_h = MAZE_FRAME_H // rows
                    CELL_SIZE = min(cell_w, cell_h)

                    maze_w = cols * CELL_SIZE
                    maze_h = rows * CELL_SIZE

                    left_ox = PADDING + (MAZE_FRAME_W - maze_w) // 2
                    left_oy = TOP_RESERVED + (MAZE_FRAME_H - maze_h) // 2

                    right_ox = right_frame_x + (MAZE_FRAME_W - maze_w) // 2
                    right_oy = left_oy

                    dij_total_time = dij_time
                    ast_total_time = ast_time

                    dij_i = ast_i = 0
                    dij_scan_i = ast_scan_i = 0
                    dij_scan_t = ast_scan_t = 0
                    scan_done = False


        # ===============================
        # SCAN + MOVE UPDATE
        # ===============================
        if not PAUSED and not scan_done:
            if dij_scan_t >= SCAN_DELAY:
                dij_scan_i += 1
                dij_scan_t = 0

            if ast_scan_t >= SCAN_DELAY:
                ast_scan_i += 1
                ast_scan_t = 0

            if dij_scan_i >= len(dij_scan) and ast_scan_i >= len(ast_scan):
                scan_done = True

        # ======= ROBOT MOVEMENT WITH GLOBAL SPEED =======
        if scan_done and not PAUSED:
            if robot_t >= 0.05:  # tốc độ cơ bản của robot (có thể chỉnh)
                if dij_i < len(dij_path) - 1:
                    dij_i += 1
                if ast_i < len(ast_path) - 1:
                    ast_i += 1
                robot_t = 0


        # ===============================
        # DRAW
        # ===============================
        screen.fill(BG_COLOR)

        # Draw top buttons
        for b in [
            btn_mode, btn_replay, btn_pause, btn_reload,
            btn_speed_lbl, btn_speed_plus, btn_speed_minus,
            btn_size_lbl, btn_size_plus, btn_size_minus
        ]:
            b.draw(screen)

        mode = btn_mode.current

        dij_stats_cur = get_progress_stats(dij_path, dij_scan, dij_i, dij_scan_i, dij_total_time)
        ast_stats_cur = get_progress_stats(ast_path, ast_scan, ast_i, ast_scan_i, ast_total_time)

        draw_hud(screen, MOVE_DELAY, PAUSED, mode,
                 dij_stats_cur, ast_stats_cur,
                 left_ox, right_ox, maze_w)


        # Frame separator
        pygame.draw.rect(screen, (70, 70, 100),
                         (PADDING + MAZE_FRAME_W, left_oy, GAP, MAZE_FRAME_H))

        # Left maze
        if mode in ["Dijkstra", "Compare"]:
            draw_maze(screen, maze, start, goal, left_ox, left_oy)
            draw_radar(screen, dij_scan, left_ox, left_oy, DIJ_RADAR_COLOR, dij_scan_i)
            if scan_done:
                draw_path(screen, dij_path, left_ox, left_oy, DIJ_PATH_COLOR)
                draw_robot(screen, dij_path, dij_i, left_ox, left_oy, DIJ_PATH_COLOR)


        if mode in ["A*", "Compare"]:
            draw_maze(screen, maze, start, goal, right_ox, right_oy)
            draw_radar(screen, ast_scan, right_ox, right_oy, AST_RADAR_COLOR, ast_scan_i)
            if scan_done:
                draw_path(screen, ast_path, right_ox, right_oy, AST_PATH_COLOR)
                draw_robot(screen, ast_path, ast_i, right_ox, right_oy, AST_PATH_COLOR)
    

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()


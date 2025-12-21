# 🤖 PACMAN AI - TÀI LIỆU CÁC THUẬT TOÁN

## 📋 Mục lục
1. [BFS (Breadth-First Search)](#1-bfs-breadth-first-search)
2. [Thuật toán Dijkstra](#2-thuật-toán-dijkstra)
3. [Thuật toán A*](#3-thuật-toán-a)
4. [Line of Sight (Bresenham)](#4-line-of-sight-bresenham)
5. [Threat Score Calculation](#5-threat-score-calculation)
6. [Safety Score Algorithm](#6-safety-score-algorithm)
7. [Predictive Collision Detection](#7-predictive-collision-detection)
8. [Anti-Loop Mechanism](#8-anti-loop-mechanism)

---

## 1. BFS (Breadth-First Search)

### 📖 Mô tả
BFS là thuật toán tìm kiếm theo chiều rộng, được sử dụng để phân tích không gian di chuyển của Pacman và tìm lối thoát an toàn.

### Mục đích
- **Flood Fill**: Tính toán tất cả các vị trí Pacman có thể đến được
- **Movement Freedom**: Đánh giá mức độ tự do di chuyển (bị kẹt hay không)
- **Escape Analysis**: Tìm tất cả các lối thoát khả dụng

### 💻 Cách sử dụng

```python
# Kiểm tra tự do di chuyển
freedom_analysis = pacman_ai.check_movement_freedom(debug=True)

# Kết quả:
# {
#     'total_reachable': 150,        # Tổng số ô có thể đến
#     'safe_positions': 120,         # Số ô an toàn
#     'moderate_danger': 20,         # Số ô nguy hiểm vừa
#     'danger_positions': 10,        # Số ô nguy hiểm
#     'freedom_percentage': 80.0,    # % tự do di chuyển
#     'threat_level': 'LOW',         # Mức đe dọa
#     'is_trapped': False            # Có bị kẹt không
# }
```

### 🔍 Tìm lối thoát khẩn cấp
```python
# Tìm lối thoát tốt nhất sử dụng BFS
escape_route = pacman_ai.find_bfs_escape_route(debug=True)

# Kết quả:
# {
#     'destination': (15, 20),       # Vị trí đích
#     'distance': 8,                 # Khoảng cách
#     'safety_score': 85.5,          # Điểm an toàn
#     'min_ghost_distance': 6,       # Khoảng cách gần nhất đến ma
#     'min_bomb_distance': 4,        # Khoảng cách gần nhất đến bom
#     'is_junction': True,           # Có phải ngã rẽ không
#     'escape_directions': ['up', 'right']  # Hướng thoát
# }
```

### ⚙️ Áp dụng chiến lược thoát hiểm
```python
# Tự động áp dụng BFS escape khi bị kẹt
success = pacman_ai.apply_bfs_escape_strategy()
# Returns: True nếu đã tìm thấy và áp dụng lối thoát
```

### 📊 Thống kê BFS
```python
stats = pacman_ai.get_bfs_statistics()
# {
#     'total_searches': 150,
#     'average_search_time': 0.003,
#     'cache_hits': 450,
#     'cache_misses': 150
# }
```

---

## 2. Thuật toán Dijkstra

### 📖 Mô tả
Dijkstra là thuật toán tìm đường đi ngắn nhất từ một điểm đến tất cả các điểm khác, được tối ưu hóa với ghost avoidance và bomb detection.

### Mục đích
- Tìm đường đi ngắn nhất đến mục tiêu
- Phát hiện bom chặn đường
- Tính toán chi phí đường đi với ghost avoidance

### 💻 Cách sử dụng

```python
# Kiểm tra mức độ đe dọa của bom
bomb_threat = pacman_ai.check_bomb_threat_level(target_position=(15, 20))

# Kết quả:
# {
#     'threat_level': 'COMPLETE_BLOCKAGE',  # Mức đe dọa
#     'is_blocked': True,                    # Có bị chặn không
#     'alternatives': 0,                     # Số lựa chọn khác
#     'warning': 'TẤT CẢ ĐƯỜNG ĐI BỊ CHẶN!',
#     'bomb_count': 5,                       # Số lượng bom
#     'pacman_pos': (10, 15),               # Vị trí Pacman
#     'target_pos': (15, 20)                # Vị trí mục tiêu
# }
```

### 🎚️ Các mức độ đe dọa

| Threat Level | Mô tả | Hành động |
|-------------|-------|----------|
| `SAFE` | Không có bom cản trở | Đi theo đường bình thường |
| `SAFE_DETOUR` | Có đường tránh an toàn | Đi đường vòng |
| `DANGEROUS_PATH_ONLY` | Chỉ có đường nguy hiểm | Cân nhắc kỹ trước khi đi |
| `COMPLETE_BLOCKAGE` | Hoàn toàn bị chặn | Tìm mục tiêu khác |

### 🔄 Tìm đường thay thế với BFS
```python
# Sử dụng BFS để check bomb blockage chính xác hơn
enhanced_threat = pacman_ai.enhanced_check_bomb_threat_with_bfs(target_position)

# BFS check TẤT CẢ đường đi có thể, không chỉ shortest path
```

### Tìm fallback target an toàn
```python
# Khi target chính không an toàn
pacman_pos = (10, 15)
ghost_positions = [(8, 12), (12, 18)]

pacman_ai.find_fallback_target(pacman_pos, ghost_positions)
# Tự động set game.auto_target và game.auto_path đến vị trí an toàn
```

---

## 3. Thuật toán A*

### 📖 Mô tả
A* là thuật toán tìm đường tối ưu sử dụng heuristic để ưu tiên các đường đi có khả năng tốt nhất.

### Mục đích
- Tìm đường đi tối ưu nhanh hơn Dijkstra
- Sử dụng heuristic (Manhattan distance) để định hướng tìm kiếm
- Kết hợp với safety evaluation

### 💻 Cách sử dụng

```python
# A* được tích hợp trong game.calculate_auto_path()
# Pacman AI sẽ tự động sử dụng A* khi có sẵn

# Kiểm tra đường đi hiện tại có an toàn không
threat_detected, closest_threat, min_distance = pacman_ai.check_ghost_on_path_to_goal()

if threat_detected:
    print(f"Ma phát hiện trên đường đi!")
    print(f"   Vị trí ma: {closest_threat}")
    print(f"   Khoảng cách: {min_distance}")
```

### 🛡️ Đánh giá an toàn đường đi
```python
# Validate path safety
path = game.auto_path
ghost_positions = [(8, 12), (12, 18)]

is_safe = pacman_ai.validate_path_safety(path, ghost_positions)
# Returns: True nếu đường đi an toàn

# Tính penalty cho đường đi nguy hiểm
penalty = pacman_ai.calculate_path_safety_penalty(path, ghost_positions, avoidance_radius=4)
# Penalty cao = đường đi nguy hiểm
```

---

## 4. Line of Sight (Bresenham)

### 📖 Mô tả
Thuật toán Bresenham để kiểm tra đường nhìn thẳng giữa hai điểm, được sử dụng để phát hiện ma và đánh giá mối đe dọa.

### Mục đích
- Kiểm tra xem Pacman có nhìn thấy ma không (không bị tường chặn)
- Tăng threat score khi có line of sight
- Hỗ trợ predictive collision detection

### 💻 Cách sử dụng

```python
# Direct Line of Sight (strict)
pacman_pos = (10, 15)
ghost_pos = (10, 20)

has_los = pacman_ai._has_line_of_sight(pacman_pos, ghost_pos)
# Returns: True nếu có đường nhìn thẳng, không bị tường chặn

# Relaxed Line of Sight (cho phép 1-2 bức tường)
has_relaxed_los = pacman_ai._has_relaxed_line_of_sight(pacman_pos, ghost_pos, max_walls=2)
# Returns: True nếu chỉ có ít tường cản (phát hiện sớm hơn)
```

### 🔍 Các trường hợp sử dụng

| Trường hợp | Phương thức | Mô tả |
|-----------|------------|-------|
| Phát hiện trực tiếp | `_has_line_of_sight()` | Không có tường cản |
| Phát hiện sớm | `_has_relaxed_line_of_sight()` | Cho phép vài tường |
| Dự đoán nhanh | `_quick_line_of_sight_check()` | Tối ưu cho future positions |

### 📐 Cách hoạt động

```
Pacman (P)          Ghost (G)
   |                   |
   v                   v
   P . . . . . . . . . G    Direct LOS (cùng hàng, không tường)
   
   P
   .
   █ (wall)
   .
   G                        No LOS (có tường chặn)
   
   P
   .
   █
   .
   .
   G                        Relaxed LOS (1 tường, vẫn phát hiện)
```

---

## 5. Threat Score Calculation

### 📖 Mô tả
Hệ thống tính điểm mối đe dọa tổng hợp từ nhiều yếu tố để đánh giá mức độ nguy hiểm của ma.

### Các yếu tố tính toán

| Yếu tố | Trọng số | Mô tả |
|--------|----------|-------|
| **Khoảng cách** | 0-100 | Càng gần = càng nguy hiểm |
| **Line of Sight** | +30 (direct), +15 (relaxed) | Có thể nhìn thấy nhau |
| **Same Corridor** | +25 | Cùng hàng hoặc cột |
| **Predictive Collision** | +40 | Dự đoán va chạm tương lai |
| **Escape Routes** | +20 (1 route), +10 (2 routes) | Ít lối thoát = nguy hiểm hơn |

### 💻 Cách sử dụng

```python
# Tính threat score cho một ghost
pacman_row, pacman_col = 10, 15
ghost_row, ghost_col = 8, 15
distance = 2

threat_score = pacman_ai._calculate_comprehensive_threat_score(
    pacman_row, pacman_col, 
    ghost_row, ghost_col, 
    distance
)

print(f"Threat Score: {threat_score}/100")

# Phân loại mức độ nguy hiểm
if threat_score >= 80:
    print("🚨 CRITICAL - Thoát hiểm ngay lập tức!")
elif threat_score >= 60:
    print("HIGH - Rẽ chiến thuật")
elif threat_score >= 40:
    print("MODERATE - Cảnh giác")
else:
    print("LOW - An toàn")
```

### 📊 Ví dụ tính toán

```python
# Tình huống: Ma cách 3 ô, cùng hàng, có LOS
distance_score = 100 - (3 * 15) = 55    # Distance factor
los_bonus = 30                          # Direct LOS
corridor_bonus = 25                     # Same row
escape_penalty = 10                     # 2 escape routes

Total Threat Score = 55 + 30 + 25 + 10 = 120 → Capped at 100
→ CRITICAL THREAT! 🚨
```

---

## 6. Safety Score Algorithm

### 📖 Mô tả
Thuật toán tính điểm an toàn cho một vị trí, giúp Pacman chọn hướng thoát hiểm tốt nhất.

### Các yếu tố đánh giá

| Yếu tố | Điểm | Mô tả |
|--------|------|-------|
| **Ghost Distance** | +5 (min), +2 (avg) | Xa ma = an toàn hơn |
| **Not Dead-end** | +15 | Không phải ngõ cụt |
| **Multiple Escapes** | +3 per route | Nhiều lối thoát |
| **Moving Away** | +8 | Đang rời xa ma |
| **Moving Toward** | -6 | Đang tiến gần ma |
| **Break LOS** | +3 | Phá vỡ line of sight |
| **Dead-end** | -12 | Ngõ cụt nguy hiểm |

### 💻 Cách sử dụng

```python
# Tính safety score cho vị trí
test_row, test_col = 11, 15
current_row, current_col = 10, 15
direction = (1, 0)  # Moving down

danger_analysis = [
    {'pos': (8, 15), 'distance': 2, 'threat_score': 85},
    {'pos': (12, 18), 'distance': 4, 'threat_score': 45}
]

safety_score = pacman_ai._calculate_enhanced_safety_score(
    test_row, test_col,
    danger_analysis,
    current_row, current_col,
    direction
)

print(f"Safety Score: {safety_score}")
if safety_score > 30:
    print("An toàn - Có thể di chuyển")
elif safety_score > 15:
    print("Cẩn thận - Cân nhắc")
else:
    print("Nguy hiểm - Tránh đi")
```

### So sánh các hướng di chuyển

```python
directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
escape_options = []

for dx, dy in directions:
    new_col = pacman_col + dx
    new_row = pacman_row + dy
    
    if game.is_valid_position(new_col, new_row):
        score = pacman_ai._calculate_enhanced_safety_score(
            new_row, new_col, danger_analysis,
            pacman_row, pacman_col, (dx, dy)
        )
        escape_options.append((dx, dy, score))

# Sắp xếp theo điểm cao nhất
escape_options.sort(key=lambda x: x[2], reverse=True)
best_direction = escape_options[0]

print(f"Hướng tốt nhất: {best_direction[0:2]}, Score: {best_direction[2]}")
```

### 🧠 Caching để tối ưu

```python
# Safety score sử dụng cache để tránh tính toán lại
# Cache valid trong 100ms

# Lần 1: Tính toán thực
score1 = pacman_ai._calculate_enhanced_safety_score(...)  # ~0.5ms

# Lần 2 (trong 100ms): Lấy từ cache
score2 = pacman_ai._calculate_enhanced_safety_score(...)  # ~0.01ms ⚡
```

---

## 7. Predictive Collision Detection

### 📖 Mô tả
Dự đoán va chạm trong tương lai dựa trên hướng di chuyển hiện tại của Pacman và ma.

### Mục đích
- Phát hiện collision trước 4-6 bước
- Tránh tình huống "đi vào bẫy"
- Tăng proactive behavior

### 💻 Cách sử dụng

```python
# Dự đoán collision
pacman_row, pacman_col = 10, 15
ghost_row, ghost_col = 10, 20
distance = 5

ghost = {
    'pos': [ghost_col, ghost_row],
    'direction': [-1, 0]  # Moving left toward Pacman
}

will_collide = pacman_ai._predictive_collision_check(
    pacman_row, pacman_col,
    ghost_row, ghost_col,
    ghost,
    distance
)

if will_collide:
    print("CẢNH BÁO: Va chạm dự kiến trong 4-6 bước!")
    print("   → Nên đổi hướng ngay!")
```

### 🔮 Cách hoạt động

```
Bước hiện tại:
P → → →     ← ← ← G
|           |
Pacman      Ghost

Sau 3 bước (prediction):
        P → ← G
        ↓     ↓
    Va chạm! ❌

→ Predictive Collision Detected!
```

### ⚙️ Tham số điều chỉnh

```python
# Trong code:
prediction_steps = min(6, max(3, distance + 2))

# distance = 2 → predict 4 steps
# distance = 4 → predict 6 steps
# distance = 8 → predict 6 steps (max)
```

### Các trường hợp phát hiện

```python
# Case 1: Head-on collision (đối đầu)
pacman_dir = [1, 0]   # Moving right
ghost_dir = [-1, 0]   # Moving left
# → High chance of collision! ⚠️

# Case 2: Same direction (cùng hướng)
pacman_dir = [1, 0]   # Moving right
ghost_dir = [1, 0]    # Moving right
# → Low risk if Pacman faster ✅

# Case 3: Perpendicular (vuông góc)
pacman_dir = [1, 0]   # Moving right
ghost_dir = [0, 1]    # Moving down
# → Medium risk, check intersection point ⚠️
```

### 🧮 Kiểm tra "đang tiến về phía nhau"

```python
are_approaching = pacman_ai._are_moving_towards_each_other(
    pacman_pos, ghost_pos,
    pacman_direction, ghost_direction
)

if are_approaching:
    print("Đang tiến về phía nhau - Nguy hiểm!")
```

---

## 8. Anti-Loop Mechanism

### 📖 Mô tả
Hệ thống ngăn chặn Pacman bị kẹt trong vòng lặp di chuyển (ping-pong, quay vòng).

### Các vấn đề giải quyết

| Vấn đề | Mô tả | Giải pháp |
|--------|-------|----------|
| **Ping-Pong** | Đi qua lại 2 vị trí | Detect opposite directions |
| **Circular Loop** | Đi vòng tròn | Track direction history |
| **Stuck in Corner** | Kẹt ở góc | Force random movement |
| **Repeated Path** | Lặp lại đường đi | Penalty for recent directions |

### 💻 Cách sử dụng

```python
# Anti-loop tự động hoạt động trong emergency_ghost_avoidance()

# Lịch sử hướng di chuyển
print(pacman_ai.escape_direction_history)
# [[1, 0], [-1, 0], [1, 0], [-1, 0]]  ← Ping-pong detected! 🔄

# Thống kê
print(f"Escape timeout count: {pacman_ai.escape_timeout_count}")
print(f"Force movement count: {pacman_ai.force_movement_counter}")
```

### 🔍 Phát hiện Ping-Pong

```python
# Kiểm tra nếu đang ping-pong
recent_directions = escape_direction_history[-5:]
unique_directions = len(set(map(tuple, recent_directions)))

if unique_directions <= 2:
    # Check if opposite directions
    dir1, dir2 = list(set(map(tuple, recent_directions)))
    if dir1[0] == -dir2[0] and dir1[1] == -dir2[1]:
        print("🔄 PING-PONG DETECTED!")
        # → Force perpendicular turn
```

### Force Emergency Movement

```python
# Khi bị kẹt quá lâu (>1 second)
time_since_last_escape = current_time - pacman_ai.last_escape_time

if time_since_last_escape > 1000 and pacman_ai.escape_timeout_count > 1:
    print("FORCED MOVEMENT ACTIVATED!")
    
    # Tìm tất cả hướng hợp lệ
    valid_moves = []
    for direction in [(0,1), (0,-1), (1,0), (-1,0)]:
        if is_valid_and_safe(direction):
            valid_moves.append(direction)
    
    # Chọn ngẫu nhiên để break deadlock
    import random
    forced_direction = random.choice(valid_moves)
    pacman_ai.game.pacman_next_direction = forced_direction
```

### 📊 Adaptive Cooldown

```python
# Cooldown tăng dần khi detect loop
base_cooldown = 80  # ms
adaptive_cooldown = base_cooldown + (escape_timeout_count * 100)

# Loop lần 1: 80ms cooldown
# Loop lần 2: 180ms cooldown  
# Loop lần 3: 280ms cooldown
# → Ngăn spam direction changes
```

### Bonus cho hướng mới

```python
# Ưu tiên hướng chưa dùng gần đây
recently_used = set(escape_direction_history[-4:])

for direction in all_directions:
    safety_score = calculate_score(direction)
    
    if direction not in recently_used:
        safety_score += 25  # 🆕 Fresh direction bonus!
    else:
        safety_score -= 15  # ♻️ Repeated direction penalty
```

---

## 🎮 Ví dụ Tích hợp Hoàn chỉnh

### Scenario: Pacman bị ma đuổi trong mê cung có bom

```python
import pygame
from pacman_ai import PacmanAI

# Khởi tạo AI
ai = PacmanAI(game_instance)

# === FRAME 1: Phát hiện ma ===
nearby_ghosts = ai.check_ghosts_nearby(avoidance_radius=6, debug=True)

if nearby_ghosts:
    print(f"🚨 Phát hiện {len(nearby_ghosts)} ma gần đây!")
    
    # Tính threat score cho từng ma
    for ghost_pos, distance in nearby_ghosts:
        threat = ai._calculate_comprehensive_threat_score(
            pacman_row, pacman_col,
            ghost_pos[0], ghost_pos[1],
            distance
        )
        print(f"   Ma tại {ghost_pos}: Threat={threat}, Distance={distance}")
    
    # Kích hoạt emergency avoidance
    success = ai.emergency_ghost_avoidance(nearby_ghosts)
    if success:
        print("Emergency avoidance activated!")

# === FRAME 2: Kiểm tra bom trên đường đi ===
if game.current_goal:
    bomb_threat = ai.check_bomb_threat_level()
    
    if bomb_threat['threat_level'] == 'COMPLETE_BLOCKAGE':
        print("Bị bom chặn hoàn toàn!")
        print("   Tìm target thay thế...")
        
        # Sử dụng BFS để tìm fallback target
        ghost_positions = [g['pos'] for g in game.ghosts]
        ai.find_fallback_target(pacman_pos, ghost_positions)

# === FRAME 3: Kiểm tra tự do di chuyển ===
freedom = ai.check_movement_freedom(debug=True)

if freedom['is_trapped']:
    print("BỊ KẸT! Kích hoạt BFS escape...")
    
    # Tìm lối thoát tốt nhất
    escape_route = ai.find_bfs_escape_route(debug=True)
    
    if escape_route:
        print(f"Tìm thấy lối thoát: {escape_route['destination']}")
        print(f"   Safety score: {escape_route['safety_score']}")
        
        # Áp dụng escape strategy
        ai.apply_bfs_escape_strategy()

# === FRAME 4: Validate đường đi hiện tại ===
if game.auto_path:
    threat_detected, closest_threat, distance = ai.check_ghost_on_path_to_goal()
    
    if threat_detected:
        print(f"Ma phát hiện trên đường đi!")
        print(f"   Ma gần nhất: {closest_threat}, cách {distance} ô")
        
        # Tìm đường thay thế
        # ... reroute logic ...

# === FRAME 5: Anti-loop check ===
if len(ai.escape_direction_history) > 4:
    recent = ai.escape_direction_history[-5:]
    unique = len(set(map(tuple, recent)))
    
    if unique <= 2:
        print("🔄 Phát hiện vòng lặp!")
        print("   Lịch sử:", recent)
        # Force movement sẽ tự động kích hoạt
```

---

## 📈 Hiệu suất và Tối ưu

### Caching Strategy

```python
# Safety Score Cache (100ms TTL)
cache_key = (test_row, test_col, len(danger_analysis))
if cache_key in score_cache and is_recent(cache_key):
    return cached_score  # ~50x faster

# Ghost Distance History (1 second)
if ghost_id in ghost_distance_history:
    recent_history = filter_recent(ghost_distance_history[ghost_id])
    # Analyze trend without recalculating
```

### Độ phức tạp thuật toán

| Thuật toán | Độ phức tạp | Ghi chú |
|-----------|-------------|---------|
| BFS Flood Fill | O(N) | N = số ô trong radius |
| Dijkstra Shortest Path | O(E log V) | E = edges, V = vertices |
| A* Pathfinding | O(E log V) | Faster than Dijkstra with good heuristic |
| Line of Sight | O(D) | D = distance between points |
| Threat Score | O(G) | G = số ghosts |
| Safety Score | O(G × D) | G = ghosts, D = directions |
| Predictive Collision | O(S) | S = prediction steps (4-6) |

### 📊 Profiling Tips

```python
import time

# Measure function performance
start = time.time()
result = ai.check_ghosts_nearby(avoidance_radius=6)
elapsed = (time.time() - start) * 1000

print(f"check_ghosts_nearby: {elapsed:.2f}ms")

# Target: < 5ms per frame for smooth gameplay
```

---

## 🐛 Troubleshooting

### Vấn đề: Pacman bị kẹt trong vòng lặp

```python
# Giải pháp 1: Kiểm tra anti-loop mechanism
print(f"Escape timeout count: {ai.escape_timeout_count}")
print(f"Last escape time: {ai.last_escape_time}")

# Giải pháp 2: Tăng cooldown
# Trong emergency_ghost_avoidance(), tăng base_cooldown từ 80 lên 120

# Giải pháp 3: Enable force movement sớm hơn
# Giảm threshold từ 1000ms xuống 500ms
```

### Vấn đề: Pacman không tránh ma kịp thời

```python
# Giải pháp 1: Tăng avoidance radius
nearby_ghosts = ai.check_ghosts_nearby(avoidance_radius=8)  # Tăng từ 4 lên 8

# Giải pháp 2: Giảm adaptive cooldown
base_cooldown = 50  # Giảm từ 80 xuống 50

# Giải pháp 3: Enable relaxed LOS
# Sử dụng _has_relaxed_line_of_sight với max_walls=2
```

### Vấn đề: Performance lag

```python
# Giải pháp 1: Giảm BFS radius
freedom = ai.check_movement_freedom(radius=8)  # Giảm từ 10 xuống 8

# Giải pháp 2: Tăng cache TTL
# Trong _calculate_enhanced_safety_score(), tăng từ 100ms lên 200ms

# Giải pháp 3: Giảm prediction steps
# Trong _predictive_collision_check(), giảm max từ 6 xuống 4
```

---

## 📚 Tài liệu tham khảo

- **BFS Algorithm**: [Wikipedia - Breadth-First Search](https://en.wikipedia.org/wiki/Breadth-first_search)
- **Dijkstra Algorithm**: [Wikipedia - Dijkstra's Algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- **A* Algorithm**: [Wikipedia - A* Search Algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm)
- **Bresenham Line**: [Wikipedia - Bresenham's Line Algorithm](https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm)

---

## 🤝 Đóng góp

Nếu bạn muốn cải thiện các thuật toán hoặc thêm tính năng mới:

1. Fork repository
2. Tạo branch mới: `git checkout -b feature/new-algorithm`
3. Commit changes: `git commit -am 'Add new pathfinding algorithm'`
4. Push to branch: `git push origin feature/new-algorithm`
5. Tạo Pull Request

---

## 📄 License

MIT License - Free to use and modify

---

**📧 Contact**: [Your Email]
**🌐 GitHub**: [Repository Link]
**📅 Last Updated**: November 27, 2025

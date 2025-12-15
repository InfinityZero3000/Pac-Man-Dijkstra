# Pacman AI - Hướng dẫn hoạt động

## Tổng quan

Pacman AI sử dụng **hệ thống đa tầng** để điều khiển Pacman tự động, kết hợp:
- **A\*/Dijkstra** cho tìm đường
- **BFS Utilities** cho phân tích chiến lược
- **Ghost Avoidance System** cho né ma thông minh

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                    PACMAN AI                            │
├─────────────────────────────────────────────────────────┤
│  1. PATHFINDING (A*/Dijkstra)                           │
│     └── Tìm đường ngắn nhất đến goal                    │
│                                                         │
│  2. GHOST DETECTION (Multi-layer)                       │
│     ├── Immediate: ≤3 ô  → Emergency escape             │
│     ├── Close: ≤6 ô      → Tactical avoidance           │
│     └── Potential: ≤9 ô  → Preventive action            │
│                                                         │
│  3. ESCAPE SYSTEM                                       │
│     ├── Emergency turn                                  │
│     ├── Escape mode (commit direction)                  │
│     └── Post-escape cooldown                            │
│                                                         │
│  4. BFS UTILITIES (Strategic planning)                  │
│     ├── Flood fill analysis                             │
│     └── Escape route finding                            │
└─────────────────────────────────────────────────────────┘
```

---

## Luồng xử lý chính

```
[Mỗi frame]
    │
    ▼
┌──────────────────────┐
│ 1. Check ghost nearby│ (radius = 6 ô)
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    │ Có ma gần? │
    └──────┬──────┘
           │
    Yes    │    No
    ▼      │    ▼
┌────────────┐  ┌────────────────┐
│ ESCAPE     │  │ PATHFINDING    │
│ SYSTEM     │  │ (A*/Dijkstra)  │
└─────┬──────┘  └───────┬────────┘
      │                 │
      ▼                 ▼
┌────────────┐  ┌────────────────┐
│ Né ma      │  │ Đi đến goal    │
│ (quay/rẽ)  │  │ (dot/exit)     │
└─────┬──────┘  └───────┬────────┘
      │                 │
      └────────┬────────┘
               ▼
        [Di chuyển Pacman]
```

---

## Hệ thống phát hiện ma

### Tính khoảng cách
Sử dụng **Path Distance** (không phải Manhattan):
```python
# BFS tìm đường đi thực tế, không phải đường chim bay
actual_distance = _calculate_actual_path_distance(pacman_pos, ghost_pos)
```

### Threat Score (0-120)
| Yếu tố | Điểm |
|--------|------|
| Khoảng cách ≤2 ô | +100 |
| Line of sight trực tiếp | +40 |
| Cùng hành lang | +35 |
| Ma đang tiến về phía Pacman | +30 |
| Chỉ có 1 lối thoát | +30 |
| Dự đoán va chạm | +50 |

---

## Escape Mode

### Kích hoạt
- Ma trong phạm vi **≤3 ô** hoặc **threat score ≥80**

### Hoạt động
1. Chọn hướng an toàn nhất (tránh dead-end, xa ma)
2. **Commit** theo hướng đó (không đổi ý ngay)
3. Di chuyển tối thiểu **6 bước** hoặc **300ms**

### Ưu tiên hướng đi
```
1. Rẽ vuông góc (turn)      → Bonus +15
2. Tiếp tục thẳng (forward) → Bonus +5  
3. Quay đầu (backward)      → Penalty -8
```

---

## Post-Escape Cooldown

**Mục đích**: Tránh Pacman quay lại đường cũ ngay sau khi né ma

### Điều kiện thoát cooldown
```
Thời gian ≥ 1.5 giây
Ma cách xa ≥ 10 ô (path distance)
```

### Trong lúc cooldown
- Tiếp tục đi theo hướng an toàn
- **KHÔNG** tính đường mới đến goal
- Nếu ma đến gần (≤4 ô) → Cancel cooldown, né tiếp

---

## Imminent Collision Detection

Dự đoán va chạm trong **5 bước tiếp theo**:

```python
for step in range(1, 6):
    future_pacman = pacman_pos + pacman_dir * step
    future_ghost = ghost_pos + ghost_dir * step
    
    if distance(future_pacman, future_ghost) <= 1:
        → COLLISION WARNING!
```

---

## Các tham số quan trọng (config.py)

| Tham số | Giá trị | Mô tả |
|---------|---------|-------|
| `GHOST_AVOIDANCE_RADIUS` | 8 | Bán kính phát hiện ma |
| `GHOST_PENALTY_MULTIPLIER` | 15 | Hệ số né ma trong pathfinding |
| `EMERGENCY_UPDATE_INTERVAL_MS` | 30 | Tần suất check khẩn cấp |
| `PACMAN_SPEED` | 4.0 | Tốc độ Pacman (blocks/sec) |
| `GHOST_SPEED` | 3.0 | Tốc độ Ghost (blocks/sec) |

---

## Các method chính

### Ghost Detection
```python
check_ghosts_nearby(avoidance_radius=6)
# → Trả về list [(ghost_pos, distance), ...]
```

### Emergency Avoidance  
```python
emergency_ghost_avoidance(nearby_ghosts)
# → True nếu đã xử lý né ma thành công
```

### Threat Analysis
```python
_calculate_comprehensive_threat_score(pacman, ghost, distance)
# → Score 0-120 (càng cao càng nguy hiểm)
```

### Safe Zone Check
```python
check_safe_zone_status()
# → True nếu an toàn để tính đường mới
```

---

## Debug Logs

| Log | Ý nghĩa |
|-----|---------|
| `N threatening ghosts` | Phát hiện N ma trong vùng nguy hiểm |
| `CRITICAL ESCAPE` | Kích hoạt escape khẩn cấp |
| `POST-ESCAPE COOLDOWN` | Bắt đầu cooldown sau escape |
| `SAFE ZONE CONFIRMED` | Ma đã đi xa, an toàn |
| `IMMINENT COLLISION` | Dự đoán sẽ đụng ma |
| `PING-PONG DETECTED` | Phát hiện Pacman bị kẹt loop |

---

## Tips tối ưu

1. **Tăng `post_escape_safe_radius`** nếu Pacman hay quay lại sớm
2. **Giảm `min_escape_duration`** nếu muốn Pacman linh hoạt hơn
3. **Tăng `GHOST_AVOIDANCE_RADIUS`** để phát hiện ma sớm hơn
4. Dùng **BFS escape route** cho tình huống phức tạp (bị bao vây)

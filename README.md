# Maze Game - AI Pathfinding with Dijkstra Algorithm

Một trò chơi mê cung thông minh được xây dựng bằng Python và Pygame, sử dụng thuật toán Dijkstra để tìm đường đi tối ưu. Game mô phỏng phong cách Pacman với khả năng tạo mê cung ngẫu nhiên và hiển thị đường đi thông minh.

## Tính năng chính

- **Tạo mê cung ngẫu nhiên**: Sử dụng thuật toán DFS với đảm bảo kết nối
- **Tìm đường thông minh**: Thuật toán Dijkstra/A* với heuristic Manhattan
- **Giao diện đồ họa**: Pygame với hiệu ứng mượt mà và màu sắc rõ ràng
- **Điều khiển trực quan**: Di chuyển bằng phím mũi tên, tìm đường bằng Space
- **Làm mới tự động**: Tạo mê cung mới nếu không có đường đi
- **Kiểm tra hợp lệ**: Đảm bảo đường đi không xuyên qua tường
- **Thống kê chi tiết**: Hiển thị số bước và thời gian thực hiện

## Yêu cầu hệ thống

Cài đặt các package cần thiết:

```bash
pip install -r requirements.txt
```

Hoặc cài đặt thủ công:

```bash
pip install pygame numpy
```

## Cách chạy

Chạy game trực tiếp:

```bash
python maze_game.py
```

## Cấu hình nâng cao

Có thể điều chỉnh trong `maze_game.py`:

```python
# Thay đổi kích thước mê cung
width=51, height=41, cell_size=20

# Thay đổi màu sắc
self.BLACK = (0, 0, 0)      # Đường đi
self.BLUE = (0, 0, 255)     # Tường
self.YELLOW = (255, 255, 0) # Player
self.GREEN = (0, 255, 0)    # Goal
self.RED = (255, 0, 0)      # Path
```

## Báo cáo thuật toán chính

### 1) Dijkstra/A* Pathfinding (`dijkstra_algorithm.py`)

- Chức năng chính
  - Tìm đường tối ưu trên lưới 4 hướng bằng Dijkstra hoặc A* (heuristic Manhattan khi bật `config.USE_ASTAR`).
  - Các biến thể an toàn: né ma (ghost avoidance), né bom tuyệt đối (coi là tường), né theo bán kính/penalty.
  - Hỗ trợ đa mục tiêu (multi-objective), bộ nhớ ma (ghost memory), cache đường đi, ghi log thống kê.

- Ưu điểm & thế mạnh
  - Ổn định, đảm bảo đường đi ngắn nhất khi chi phí đồng nhất; A* tăng tốc đáng kể ở mê cung lớn.
  - Linh hoạt mở rộng bằng penalty để mô hình hoá vùng nguy hiểm (ma/bom) mà vẫn giữ tối ưu hoá.
  - Có hạ tầng đo lường (nodes explored, thời gian) giúp tối ưu hiệu năng thực tế.

- So sánh nhanh
  - Dijkstra vs A*: Dijkstra tối ưu nhưng chậm hơn; A* nhanh hơn nhờ heuristic, đặc biệt khi khoảng cách xa.
  - Né bom tuyệt đối vs penalty: tuyệt đối an toàn nhưng có thể bít đường; penalty giữ lựa chọn trong tình huống khẩn cấp.
  - Một mục tiêu vs đa mục tiêu: đa mục tiêu giàu ngữ cảnh nhưng phức tạp, phù hợp khi cần cân bằng an toàn/tiến độ.

### 2) AI né ma và điều hướng an toàn (`pacman_ai.py`)

- Chức năng chính
  - Đánh giá đe doạ nhiều mức (critical/high/moderate) theo khoảng cách, line-of-sight (thường/relaxed), cùng hành lang, số lối thoát.
  - Dự đoán va chạm (moving-towards), kiểm tra giao cắt với đường đi, lookahead an toàn nhiều bước.
  - Ưu tiên ngã rẽ an toàn (junction detection), tránh ngõ cụt, chế độ tạm rời đường (path avoidance mode) và quay lại khi an toàn.

- Ưu điểm & thế mạnh
  - Phản ứng theo ngữ cảnh, hạn chế rung lắc nhờ cooldown/turn-tracking.
  - Chủ động phòng ngừa (lookahead) thay vì chỉ phản ứng theo khoảng cách tức thời.
  - Kết hợp nhiều tín hiệu (LOS, hành lang, lối thoát) để đưa quyết định chắc chắn hơn.

- So sánh nhanh
  - Heuristic an toàn đa yếu tố vs khoảng cách thuần: bền vững hơn khi hành lang dài/LOS trực diện.
  - Ưu tiên rẽ sớm vs giữ thẳng: rẽ sớm giảm rủi ro “đối đầu” trong hành lang thẳng.
  - Dự đoán hướng di chuyển vs tĩnh: giảm tai nạn ở giao lộ, khi ma thay đổi chế độ.

### 3) Sinh và hợp thức hoá môi trường chơi (`maze_game.py`)

- Chức năng chính
  - Sinh mê cung (`MazeGenerator`) với độ phức tạp điều chỉnh; chọn cổng thoát ở vị trí đối đỉnh hợp lệ.
  - Rải dots/power pellets với ràng buộc khoảng cách tối thiểu; spawn 4 ghosts gần trung tâm ở ô hợp lệ.
  - Đặt bom có kiểm chứng đường đi: thử vị trí và xác nhận còn đường từ start → goal bằng Dijkstra/A*.
  - Tính/hiển thị đường ngắn nhất, đánh giá an toàn đường, làm mượt đường đi khi cần.

- Ưu điểm & thế mạnh
  - Bảo toàn khả năng về đích dù có bom/vật cản nhờ kiểm chứng pathfinding từng bước.
  - Phân bố vật thể hợp lý (min-distance/greedy) giúp gameplay cân bằng, tránh dồn cụm.
  - Kết nối chặt chẽ với AI để trực quan hoá đường đi và vùng nguy hiểm.

- So sánh nhanh
  - Đặt bom “coi như tường” an toàn tuyệt đối vs đặt kèm penalty linh hoạt: tuỳ mục tiêu độ khó/trải nghiệm.
  - Spawn ghost gần trung tâm cho nhịp độ ổn định hơn so với spawn cố định ở rìa.

### Gợi ý cấu hình/thực nghiệm

- Bật A* (`config.USE_ASTAR=True`) khi mê cung lớn, mục tiêu xa để giảm thời gian tìm kiếm.
- Dùng né bom theo bán kính khi muốn giữ “cửa thoát hiểm” trong tình huống bí.
- Tăng avoidance radius khi mật độ ma cao; giảm khi muốn nhịp độ nhanh và táo bạo hơn.

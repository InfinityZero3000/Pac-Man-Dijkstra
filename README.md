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

## 🔧 Cấu hình nâng cao

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

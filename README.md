# 🎮 Maze Game - AI Pathfinding with Dijkstra Algorithm

Một trò chơi mê cung thông minh được xây dựng bằng Python và Pygame, sử dụng thuật toán Dijkstra để tìm đường đi tối ưu. Game mô phỏng phong cách Pacman với khả năng tạo mê cung ngẫu nhiên và hiển thị đường đi thông minh.

## ✨ Tính năng chính

- 🏗️ **Tạo mê cung ngẫu nhiên**: Sử dụng thuật toán DFS với đảm bảo kết nối
- 🎯 **Tìm đường thông minh**: Thuật toán Dijkstra/A* với heuristic Manhattan
- 🎨 **Giao diện đồ họa**: Pygame với hiệu ứng mượt mà và màu sắc rõ ràng
- 🕹️ **Điều khiển trực quan**: Di chuyển bằng phím mũi tên, tìm đường bằng Space
- 🔄 **Làm mới tự động**: Tạo mê cung mới nếu không có đường đi
- 🛡️ **Kiểm tra hợp lệ**: Đảm bảo đường đi không xuyên qua tường
- 📊 **Thống kê chi tiết**: Hiển thị số bước và thời gian thực hiện

## 📋 Yêu cầu hệ thống

Cài đặt các package cần thiết:

```bash
pip install -r requirements.txt
```

Hoặc cài đặt thủ công:

```bash
pip install pygame numpy
```

## 🚀 Cách chạy

Chạy game trực tiếp:

```bash
python maze_game.py
```

## 🎮 Hướng dẫn điều khiển

- **⬆️⬇️⬅️➡️ Phím mũi tên**: Di chuyển nhân vật (chấm vàng)
- **🔍 Space**: Tìm và hiển thị đường đi ngắn nhất đến đích (chấm xanh lá)
- **🔄 R**: Tạo mê cung mới
- **❌ Escape**: Thoát game

## 📁 Cấu trúc dự án

```
game-AI/
├── maze_game.py              # Game chính với giao diện Pygame
├── maze_generator.py         # Tạo mê cung ngẫu nhiên
├── dijkstra_algorithm.py     # Thuật toán tìm đường Dijkstra/A*
├── path_validator.py         # Kiểm tra tính hợp lệ của đường đi
├── config.py                 # Cấu hình game
├── pathfinding_data_logger.py # Ghi log dữ liệu pathfinding
├── scripts/
│   ├── generate_training_data.py # Tạo dữ liệu training
│   ├── train_model.py           # Huấn luyện model AI
│   └── infer_policy.py          # Suy luận policy
├── requirements.txt          # Các package cần thiết
└── README.md                # Tài liệu này
```

## 🧪 Testing và Debug

Chạy các test để kiểm tra tính năng:

```bash
# Test tổng quát
python test_maze_comprehensive.py

# Test pathfinding cơ bản  
python test_dijkstra.py

# Debug coordinate system
python debug_coordinates.py

# Test wall crossing prevention
python test_enhanced_wall_crossing.py
```

## ⚙️ Thông số kỹ thuật

### Cấu hình mê cung
- **Kích thước mặc định**: 41x41 cells
- **Kích thước cell**: 20x20 pixels
- **Kích thước màn hình**: 820x820 pixels
- **Tỷ lệ đường đi**: ~50% không gian mở
- **Độ phức tạp**: Bao gồm ngõ cụt và nhánh rẽ

### Thuật toán
- **Tạo mê cung**: Randomized Depth-First Search (DFS)
- **Tìm đường**: Dijkstra với A* optimization
- **Heuristic**: Manhattan distance
- **Validation**: Kiểm tra từng bước không đi qua tường
- **Performance**: Tối ưu cho mê cung lớn

### Màu sắc và ký hiệu
- 🟦 **Màu xanh**: Tường/vật cản (maze[row,col] = 1)
- ⬜ **Màu đen**: Đường đi (maze[row,col] = 0)  
- 🟡 **Chấm vàng**: Nhân vật (player)
- 🟢 **Chấm xanh lá**: Đích đến (goal)
- 🔴 **Chấm đỏ**: Đường đi tối ưu

## 🔧 Cấu hình nâng cao

Có thể điều chỉnh trong `maze_game.py`:

```python
# Thay đổi kích thước mê cung
width=41, height=41, cell_size=20

# Thay đổi màu sắc
self.BLACK = (0, 0, 0)      # Đường đi
self.BLUE = (0, 0, 255)     # Tường
self.YELLOW = (255, 255, 0) # Player
self.GREEN = (0, 255, 0)    # Goal
self.RED = (255, 0, 0)      # Path
```

## 🐛 Troubleshooting

### Lỗi "No path found!"
- Mê cung được tạo tự động với đảm bảo kết nối
- Nếu vẫn gặp lỗi, ấn **R** để tạo mê cung mới

### Đường đi đi qua tường
- Đã được khắc phục với validation nghiêm ngặt
- Chỉ hiển thị đường đi hợp lệ (maze[row,col] = 0)

### Performance chậm
- Tối ưu cho mê cung 41x41
- Có thể giảm kích thước nếu cần tăng tốc

## 📈 Các cải tiến đã thực hiện

- ✅ Fix coordinate system mismatch
- ✅ Implement strict path validation  
- ✅ Optimize A* with Manhattan heuristic
- ✅ Add comprehensive error handling
- ✅ Improve visual rendering
- ✅ Add debugging utilities
- ✅ Enhance user interface

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Hãy tạo issue hoặc pull request.

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

---

*Được phát triển với ❤️ bằng Python và Pygame*

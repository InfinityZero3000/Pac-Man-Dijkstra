# 🎮 Ghost Avoidance Visualizer - Hướng Dẫn Sử Dụng

## ✅ Đã Tích Hợp Thành Công!

Visualizer đã được tích hợp vào `pacman_game.py` và sẵn sàng sử dụng!

---

## 🎯 Các Phím Điều Khiển

### **Phím V** - Toggle Visualization
- **Bật/Tắt** overlay hiển thị AI debug
- Hiển thị:
  - 🔴 **Threat Zones**: Vùng nguy hiểm xung quanh ma
  - 🟢 **Safety Scores**: Điểm an toàn của các vị trí
  - 🔮 **Predictions**: Dự đoán đường đi của Pacman và ma
  - 🛣️ **Escape Routes**: Đường thoát hiểm

### **Phím B** - Print Debug Info
- In ra console phân tích chi tiết về:
  - Vị trí Pacman hiện tại
  - Các mối đe dọa (ghosts) gần
  - Trạng thái AI (escape mode, turns, etc.)
  - Phân tích độ an toàn

### **Phím Shift + S** - Save Analysis Report
- Lưu báo cáo phân tích chi tiết ra file JSON
- File chứa:
  - Metrics hiệu suất
  - Lịch sử quyết định
  - Phân tích các lần chết
  - Lịch sử escape attempts

---

## 📊 Visualization Elements

### 1️⃣ **Threat Zones** (Vùng Đe Dọa)
- **🔴 Critical (Red)**: Ma rất gần (≤ 3 ô)
- **🟠 High (Orange)**: Ma gần (4-5 ô)
- **🟡 Medium (Yellow)**: Ma trung bình (6 ô)
- **🟢 Low (Light Green)**: Ma xa (7-8 ô)

### 2️⃣ **Safety Score Heatmap**
- **Màu gradient**: Từ đỏ (nguy hiểm) → vàng (trung bình) → xanh (an toàn)
- Số điểm hiển thị cho các vị trí quan trọng
- Giúp hiểu AI đang đánh giá độ an toàn như thế nào

### 3️⃣ **Movement Predictions**
- **Cyan circles**: Đường đi dự đoán của Pacman
- **Magenta circles**: Đường đi dự đoán của ma
- Giúp thấy AI có đang dự đoán collision không

### 4️⃣ **Escape Routes**
- **Cyan highlighted path**: Đường thoát hiểm đang sử dụng
- Hiển thị khi ở escape mode

---

## 📈 Performance Metrics Panel

Hiển thị ở **góc trái trên** khi visualization bật:

```
╔════════════════════════════════╗
║   Performance Metrics          ║
║   ────────────────────────     ║
║   Total Avoidances: 45         ║
║   Successful Escapes: 38       ║
║   Failed Escapes: 7            ║
║   Success Rate: 84.4%          ║
║   Loop Detections: 3           ║
╚════════════════════════════════╝
```

---

## 🤖 AI Decision State Panel

Hiển thị ở **góc phải trên** khi visualization bật:

```
╔════════════════════════════════╗
║   AI Decision State            ║
║   ────────────────────────     ║
║   Escape Mode: YES             ║
║   Escape Steps: 4              ║
║   Consecutive Turns: 2         ║
║   Total Turns: 12              ║
║   Forced Moves: 1              ║
║   Timeout Count: 0             ║
╚════════════════════════════════╝
```

---

## 📝 Console Debug Output (Phím B)

Khi nhấn **B**, console sẽ hiển thị:

```
============================================================
GHOST AVOIDANCE REAL-TIME ANALYSIS
============================================================

📍 Pacman Position: (23, 14)

👻 Active Threats: 2
   1. Distance: 4, Score: 68.5, LOS: Yes
   2. Distance: 6, Score: 42.0, LOS: No

🤖 AI State:
   Escape Mode: True
   Escape Steps: 3
   Consecutive Turns: 1
   Force Movements: 0

🛡️  Safety Analysis:
   Average Safety: 45.2
   Max Safety: 82.0
   Min Safety: 12.5
============================================================
```

---

## 💾 Analysis Report (Shift + S)

File JSON được lưu với tên: `ghost_avoidance_analysis_YYYYMMDD_HHMMSS.json`

### Cấu trúc file:

```json
{
  "timestamp": "2025-11-27T10:30:45",
  "metrics": {
    "total_avoidances": 45,
    "successful_escapes": 38,
    "failed_escapes": 7,
    "success_rate": 84.4,
    "loop_detections": 3,
    "forced_movements": 2,
    "threat_level_distribution": {
      "CRITICAL": 12,
      "HIGH": 18,
      "MEDIUM": 10,
      "LOW": 5
    }
  },
  "death_analysis": [
    {
      "time": "2025-11-27T10:25:30",
      "ghost_data": [...],
      "decisions": {...},
      "recent_history": [...]
    }
  ],
  "escape_history": [...],
  "recent_decisions": [...]
}
```

---

## 🔧 Cách Sử Dụng Để Debug

### 1️⃣ **Phân Tích Lỗi Ghost Avoidance**

1. Bật visualization (**V**)
2. Bật auto mode (**A** hoặc **Space**)
3. Quan sát:
   - Pacman có né ma đúng cách không?
   - Safety scores có hợp lý không?
   - AI có bị stuck trong loop không?

### 2️⃣ **Theo Dõi Real-time**

1. Nhấn **B** liên tục để xem debug info
2. Theo dõi:
   - Threat scores có chính xác không?
   - Escape mode có kích hoạt đúng lúc không?
   - Consecutive turns có quá nhiều không? (dấu hiệu loop)

### 3️⃣ **Phân Tích Sau Khi Chết**

1. Khi Pacman chết, nhấn **Shift + S** để lưu report
2. Mở file JSON và xem:
   - `death_analysis`: Tình huống dẫn đến cái chết
   - `recent_history`: 10 quyết định gần nhất trước khi chết
   - `ghost_data`: Vị trí và trạng thái ma lúc chết

### 4️⃣ **Tối Ưu Thuật Toán**

Dựa trên metrics:
- **Success Rate < 70%**: Cần cải thiện threat detection
- **Loop Detections > 10**: Anti-loop mechanism cần tăng cường
- **Forced Movements > 5**: AI bị stuck quá nhiều

---

## 🎨 Màu Sắc và Ý Nghĩa

| Màu | Element | Ý Nghĩa |
|-----|---------|---------|
| 🔴 Red | Critical Threat | Ma rất gần - nguy hiểm cao |
| 🟠 Orange | High Threat | Ma gần - cần né tránh |
| 🟡 Yellow | Medium Threat | Ma trung bình - cẩn thận |
| 🟢 Green | Safe Zone | Vùng an toàn |
| 🔵 Cyan | Escape Route | Đường thoát hiểm |
| 🟣 Magenta | Prediction | Dự đoán collision |
| ⚪ White | Decision Marker | Điểm quyết định |

---

## 💡 Tips & Tricks

### ✅ **Best Practices**

1. **Bật visualization ngay từ đầu** để thấy AI hoạt động
2. **Sử dụng B key thường xuyên** để monitor real-time
3. **Lưu report sau mỗi session** để phân tích xu hướng
4. **So sánh metrics giữa các run** để đánh giá cải thiện

### ⚠️ **Lưu Ý**

- Visualization có thể **giảm FPS một chút** (5-10%)
- Nếu FPS thấp, tắt visualization đi (**V**)
- Console output (**B**) không ảnh hưởng performance nhiều

### 🐛 **Troubleshooting**

**Q: Visualization không hiển thị?**
- A: Nhấn **V** để bật lên

**Q: Không thấy metrics panel?**
- A: Đảm bảo visualization đang enabled (nhấn **V**)

**Q: File report không lưu được?**
- A: Check quyền ghi file trong thư mục hiện tại

**Q: Console bị spam quá nhiều?**
- A: Đừng giữ **B** quá lâu, chỉ nhấn khi cần debug

---

## 🚀 Next Steps

Sau khi sử dụng visualizer, bạn có thể:

1. **Phân tích patterns** từ reports
2. **Tối ưu threat scoring** trong `pacman_ai.py`
3. **Cải thiện anti-loop mechanism**
4. **Fine-tune escape thresholds**
5. **Implement ML-based prediction** (nếu muốn)

---

## 📞 Support

Nếu có vấn đề, check:
- Import đã đúng chưa
- Visualizer có initialize thành công không (xem console khi start game)
- Các error messages trong console

**Happy Debugging! 🎮✨**

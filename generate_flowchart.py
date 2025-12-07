import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Create figure with white background - more compact
fig, ax = plt.subplots(1, 1, figsize=(14, 18), facecolor='white')
ax.set_xlim(0, 10)
ax.set_ylim(0, 24)
ax.axis('off')

# Color scheme
color_start = '#4CAF50'
color_main = '#2196F3'
color_decision = '#FF9800'
color_algorithm = '#9C27B0'
color_bfs = '#00BCD4'
color_emergency = '#F44336'
color_end = '#607D8B'

def draw_box(ax, x, y, width, height, text, color, fontsize=9, bold=False):
    """Draw a rounded rectangle box with text"""
    box = FancyBboxPatch((x-width/2, y-height/2), width, height,
                         boxstyle="round,pad=0.1", 
                         edgecolor='black', facecolor=color, 
                         linewidth=2, alpha=0.9)
    ax.add_patch(box)
    
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text, ha='center', va='center', 
           fontsize=fontsize, weight=weight, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, label='', style='->'):
    """Draw arrow between boxes"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                          arrowstyle=style, color='black', 
                          linewidth=2, mutation_scale=20)
    ax.add_patch(arrow)
    
    if label:
        mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
        ax.text(mid_x + 0.3, mid_y, label, fontsize=8, 
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

def draw_diamond(ax, x, y, width, height, text, color):
    """Draw a diamond shape for decisions"""
    vertices = [(x, y+height/2), (x+width/2, y), 
                (x, y-height/2), (x-width/2, y)]
    diamond = mpatches.Polygon(vertices, closed=True, 
                              edgecolor='black', facecolor=color, 
                              linewidth=2, alpha=0.9)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', 
           fontsize=8, weight='bold')

# Title
ax.text(5, 23, 'PACMAN AI - SƠ ĐỒ LUỒNG HỆ THỐNG', 
       ha='center', fontsize=18, weight='bold', 
       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

# START
draw_box(ax, 5, 21.5, 2, 0.6, 'BẮT ĐẦU\nKhởi tạo AI', 
         color_start, fontsize=10, bold=True)

# Main Decision Loop
draw_arrow(ax, 5, 21.2, 5, 20.7)
draw_box(ax, 5, 20.3, 2.5, 0.7, 'VÒNG LẶP AI CHÍNH\n(Mỗi khung hình)', 
         color_main, fontsize=10, bold=True)

# Check Ghost Threat
draw_arrow(ax, 5, 20, 5, 19.5)
draw_diamond(ax, 5, 19, 2.5, 0.8, 'Có Ma\nGần?', color_decision)

# Ghost Detection Branch (YES)
draw_arrow(ax, 6.25, 19, 7.5, 19, 'CÓ')
draw_box(ax, 8.5, 19, 2, 0.6, 'Phát hiện Ma\n(Đa lớp)', 
         color_algorithm, fontsize=8)

# Emergency Ghost Avoidance
draw_arrow(ax, 8.5, 18.7, 8.5, 18.2)
draw_box(ax, 8.5, 17.8, 2.3, 0.7, 'Tránh Ma Khẩn Cấp\n+ Chống vòng lặp', 
         color_emergency, fontsize=9)

# Threat Assessment
draw_arrow(ax, 8.5, 17.45, 8, 17)
draw_diamond(ax, 8.5, 16.3, 2, 0.8, 'Mức độ?', color_decision)

# Critical Threat
draw_arrow(ax, 8.5, 15.9, 8.5, 15.4)
draw_box(ax, 8.5, 15, 2, 0.6, 'NGUY CẤP\nThoát ngay', 
         color_emergency, fontsize=8)

# High Threat (right)
draw_arrow(ax, 9.5, 16.3, 10, 16.3)
draw_box(ax, 10, 15, 1.6, 0.6, 'CAO\nRẽ nhanh', 
         color_emergency, fontsize=8)
draw_arrow(ax, 10, 14.7, 10, 14.3)
draw_arrow(ax, 10, 14.3, 8.5, 14.3)

# Choose Escape Direction
draw_arrow(ax, 8.5, 14.7, 8.5, 13.5)
draw_box(ax, 8.5, 13.2, 2.2, 0.5, 'Chọn Hướng Thoát', 
         color_algorithm, fontsize=8)

# Path to Goal Branch (NO ghost nearby)
draw_arrow(ax, 3.75, 19, 2.5, 19, 'KHÔNG')
draw_box(ax, 1.5, 19, 2, 0.6, 'Kiểm tra\nĐường đi', 
         color_algorithm, fontsize=8)

# Bomb Threat Check
draw_arrow(ax, 1.5, 18.7, 1.5, 18.2)
draw_box(ax, 1.5, 17.8, 2, 0.7, 'Kiểm tra Bom\n(Dijkstra)', 
         color_algorithm, fontsize=8)

# Path Safety Decision
draw_arrow(ax, 1.5, 17.45, 1.5, 17)
draw_diamond(ax, 1.5, 16.3, 2, 0.8, 'An toàn?', color_decision)

# Safe Path - Continue
draw_arrow(ax, 0.5, 16.3, 0, 16.3, 'CÓ')
draw_box(ax, 0, 15, 1.5, 0.6, 'Đi theo\nA*/Dijkstra', 
         color_algorithm, fontsize=8)

# Unsafe Path - Reroute
draw_arrow(ax, 2.5, 16.3, 3.5, 16.3, 'KHÔNG')
draw_box(ax, 3.5, 15, 1.7, 0.6, 'Đổi lộ trình\n(BFS)', 
         color_bfs, fontsize=8)

# Merge paths
draw_arrow(ax, 0, 14.7, 0, 13)
draw_arrow(ax, 0, 13, 2.5, 13)
draw_arrow(ax, 3.5, 14.7, 3.5, 13)
draw_arrow(ax, 3.5, 13, 2.5, 13)

# Convergence point from ghost branch
draw_arrow(ax, 8.5, 12.95, 8.5, 12.5)
draw_arrow(ax, 8.5, 12.5, 5, 12.5)
draw_arrow(ax, 2.5, 13, 2.5, 12.5)
draw_arrow(ax, 2.5, 12.5, 5, 12.5)

# Decision execution
draw_box(ax, 5, 12, 2.2, 0.6, 'Thực thi Di chuyển', 
         color_main, fontsize=9, bold=True)

# Post-movement checks
draw_arrow(ax, 5, 11.7, 5, 11.2)
draw_box(ax, 5, 10.8, 2.3, 0.6, 'Cập nhật Trạng thái\n+ Chống vòng lặp', 
         color_main, fontsize=8)

# Check if stuck
draw_arrow(ax, 5, 10.5, 5, 10)
draw_diamond(ax, 5, 9.5, 2, 0.8, 'Bị Kẹt?', color_decision)

# Force movement if stuck
draw_arrow(ax, 6, 9.5, 7.5, 9.5, 'CÓ')
draw_box(ax, 8.5, 9.5, 1.8, 0.5, 'Ép Di chuyển', 
         color_emergency, fontsize=8)
draw_arrow(ax, 8.5, 9.25, 8.5, 8.5)
draw_arrow(ax, 8.5, 8.5, 5, 8.5)

# Continue normal flow
draw_arrow(ax, 5, 9.1, 5, 8.5, 'KHÔNG')

# Return to main loop
draw_arrow(ax, 5, 8.5, 5, 8)
draw_box(ax, 5, 7.6, 2, 0.6, 'KẾT THÚC KHUNG HÌNH', 
         color_end, fontsize=9)

# Loop back indicator
draw_arrow(ax, 5, 7.3, 5, 6.8)
ax.text(5, 6.3, '↻ Lặp lại', ha='center', fontsize=10, weight='bold',
       bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# Compact legend - algorithms used
legend_y = 4.5
ax.text(5, legend_y, 'THUẬT TOÁN SỬ DỤNG', 
       ha='center', fontsize=13, weight='bold',
       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

algorithms = [
    '• BFS (Tìm kiếm Chiều rộng) - Phân tích Thoát hiểm',
    '• Dijkstra - Đường đi Ngắn nhất, Phát hiện Bom',
    '• A* - Tìm đường Tối ưu',
    '• Bresenham - Phát hiện Ma (Line of Sight)',
    '• Threat Score - Đa yếu tố (Khoảng cách, LOS, Dự đoán)',
    '• Safety Score - An toàn Đường đi, Ngõ cụt',
    '• Predictive Collision - Dự đoán Va chạm',
    '• Anti-Loop - Chống Vòng lặp & Ping-Pong',
]

for i, algo in enumerate(algorithms):
    ax.text(5, legend_y - 0.4 - i*0.3, algo, 
           ha='center', fontsize=7.5)

plt.tight_layout()
plt.savefig('/Users/nguyenhuuthang/Documents/RepoGitHub/game-AI/pacman_ai_flowchart.png', 
            dpi=300, bbox_inches='tight', facecolor='white')
print("✅ Flowchart đã được tạo: pacman_ai_flowchart.png")
plt.close()

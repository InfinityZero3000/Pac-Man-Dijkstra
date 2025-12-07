"""
GHOST AVOIDANCE VISUALIZER & DEBUGGER
======================================
Công cụ debug và phân tích chi tiết cách Pacman AI né ma

Features:
1. Visualize threat zones & safety scores
2. Real-time decision tracking
3. Movement prediction analysis
4. Performance metrics & statistics
5. Escape route visualization
6. Anti-loop detection monitoring

Usage:
    python ghost_avoidance_visualizer.py
    hoặc import vào game chính
"""

import pygame
import json
import time
from collections import deque, defaultdict
from datetime import datetime
import math


class GhostAvoidanceVisualizer:
    """
    Visualizer cho ghost avoidance system với real-time debugging
    """
    
    def __init__(self, game_instance):
        """
        Initialize visualizer
        
        Args:
            game_instance: Instance của PacmanGame
        """
        self.game = game_instance
        self.enabled = False
        
        # Visualization settings
        self.show_threat_zones = True
        self.show_safety_scores = True
        self.show_escape_routes = True
        self.show_decision_tree = True
        self.show_predictions = True
        
        # Colors
        self.COLORS = {
            'critical_threat': (255, 0, 0, 128),      # Red - critical danger
            'high_threat': (255, 128, 0, 128),        # Orange - high danger
            'medium_threat': (255, 255, 0, 128),      # Yellow - medium danger
            'low_threat': (128, 255, 128, 128),       # Light green - low threat
            'safe_zone': (0, 255, 0, 128),            # Green - safe
            'escape_route': (0, 255, 255, 200),       # Cyan - escape path
            'prediction': (255, 0, 255, 150),         # Magenta - prediction
            'decision': (255, 255, 255, 255),         # White - decision marker
            'blocked': (128, 0, 0, 180),              # Dark red - blocked
        }
        
        # Tracking data
        self.decision_history = deque(maxlen=100)
        self.threat_history = deque(maxlen=100)
        self.escape_history = deque(maxlen=50)
        self.death_analysis = []
        
        # Performance metrics
        self.metrics = {
            'total_avoidances': 0,
            'successful_escapes': 0,
            'failed_escapes': 0,
            'loop_detections': 0,
            'forced_movements': 0,
            'average_escape_time': 0,
            'threat_level_distribution': defaultdict(int),
            'decision_types': defaultdict(int),
        }
        
        # Real-time analysis
        self.current_frame_data = {}
        self.analysis_log = []
        
        # Font for text rendering
        pygame.font.init()
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        print("✅ Ghost Avoidance Visualizer initialized")
        print("   Press V to toggle visualization")
        print("   Press D to toggle debug info")
        print("   Press S to save analysis report")
    
    def update(self, ai_instance):
        """
        Update visualizer với AI state hiện tại
        
        Args:
            ai_instance: Instance của PacmanAI
        """
        if not self.enabled:
            return
        
        current_time = pygame.time.get_ticks()
        pacman_pos = (int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0]))
        
        # Collect current frame data
        self.current_frame_data = {
            'timestamp': current_time,
            'pacman_pos': pacman_pos,
            'ghosts': self._collect_ghost_data(),
            'threats': self._analyze_threats(ai_instance),
            'escape_mode': ai_instance.escape_mode,
            'escape_steps': ai_instance.escape_steps,
            'decisions': self._collect_decision_data(ai_instance),
            'safety_map': self._generate_safety_map(ai_instance),
        }
        
        # Track history
        self.decision_history.append({
            'time': current_time,
            'data': self.current_frame_data.copy()
        })
    
    def _collect_ghost_data(self):
        """Collect comprehensive ghost data"""
        ghost_data = []
        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        
        for i, ghost in enumerate(self.game.ghosts):
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            distance = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            ghost_data.append({
                'id': i,
                'pos': (ghost_row, ghost_col),
                'direction': ghost.get('direction', [0, 0]),
                'scared': ghost.get('scared', False),
                'is_eyes': self.game.can_pacman_pass_through_ghost(ghost),
                'distance': distance,
                'threat_level': self._calculate_threat_level(distance, ghost.get('scared', False)),
            })
        
        return ghost_data
    
    def _calculate_threat_level(self, distance, is_scared):
        """Calculate threat level string"""
        if is_scared:
            return 'NONE'
        elif distance <= 2:
            return 'CRITICAL'
        elif distance <= 4:
            return 'HIGH'
        elif distance <= 6:
            return 'MEDIUM'
        elif distance <= 8:
            return 'LOW'
        else:
            return 'SAFE'
    
    def _analyze_threats(self, ai_instance):
        """Analyze all threats comprehensively"""
        threats = []
        nearby_ghosts = ai_instance.check_ghosts_nearby(avoidance_radius=8, debug=False)
        
        for ghost_pos, distance in nearby_ghosts:
            ghost_row, ghost_col = ghost_pos
            pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
            
            # Calculate comprehensive threat score
            threat_score = ai_instance._calculate_comprehensive_threat_score(
                pacman_row, pacman_col, ghost_row, ghost_col, distance
            )
            
            threats.append({
                'pos': (ghost_row, ghost_col),
                'distance': distance,
                'threat_score': threat_score,
                'has_los': ai_instance._has_line_of_sight((pacman_row, pacman_col), (ghost_row, ghost_col)),
                'same_corridor': ghost_row == pacman_row or ghost_col == pacman_col,
            })
        
        return threats
    
    def _collect_decision_data(self, ai_instance):
        """Collect AI decision data"""
        return {
            'escape_mode': ai_instance.escape_mode,
            'escape_steps': ai_instance.escape_steps,
            'consecutive_turns': getattr(ai_instance, 'consecutive_turns', 0),
            'turn_count': getattr(ai_instance, 'turn_count', 0),
            'force_movement_counter': getattr(ai_instance, 'force_movement_counter', 0),
            'escape_timeout_count': getattr(ai_instance, 'escape_timeout_count', 0),
            'direction_history': getattr(ai_instance, 'escape_direction_history', [])[-5:],
        }
    
    def _generate_safety_map(self, ai_instance):
        """Generate safety score map for nearby positions"""
        safety_map = {}
        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        
        # Collect danger analysis
        danger_analysis = []
        nearby_ghosts = ai_instance.check_ghosts_nearby(avoidance_radius=8, debug=False)
        for ghost_pos, distance in nearby_ghosts:
            ghost_row, ghost_col = ghost_pos
            threat_score = ai_instance._calculate_comprehensive_threat_score(
                pacman_row, pacman_col, ghost_row, ghost_col, distance
            )
            danger_analysis.append({
                'pos': (ghost_row, ghost_col),
                'distance': distance,
                'threat_score': threat_score,
            })
        
        # Calculate safety for positions in 5x5 area
        for dr in range(-5, 6):
            for dc in range(-5, 6):
                test_row = pacman_row + dr
                test_col = pacman_col + dc
                
                if not self.game.is_valid_position(test_col, test_row):
                    continue
                
                # Calculate safety score
                safety_score = ai_instance._calculate_enhanced_safety_score(
                    test_row, test_col, danger_analysis, 
                    pacman_row, pacman_col, (dc, dr)
                )
                
                safety_map[(test_row, test_col)] = safety_score
        
        return safety_map
    
    def render(self, screen, cell_size):
        """
        Render visualization overlay
        
        Args:
            screen: pygame surface
            cell_size: size of each cell in pixels
        """
        if not self.enabled or not self.current_frame_data:
            return
        
        # Create transparent overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        
        # Render different visualization layers
        if self.show_threat_zones:
            self._render_threat_zones(overlay, cell_size)
        
        if self.show_safety_scores:
            self._render_safety_scores(overlay, cell_size)
        
        if self.show_predictions:
            self._render_predictions(overlay, cell_size)
        
        if self.show_escape_routes:
            self._render_escape_routes(overlay, cell_size)
        
        # Blit overlay to screen
        screen.blit(overlay, (0, 0))
        
        # Render UI elements
        if self.show_decision_tree:
            self._render_decision_info(screen)
        
        self._render_metrics(screen)
        self._draw_pacman_direction_arrow(screen, cell_size)  # Vẽ mũi tên hướng di chuyển
    
    def _draw_pacman_direction_arrow(self, screen, cell_size):
        """Vẽ mũi tên hiển thị hướng Pacman đang di chuyển"""
        if not hasattr(self.game, 'ai') or not hasattr(self.game.ai, 'last_direction'):
            return
        
        if self.game.ai.last_direction is None:
            return
        
        # Lấy vị trí Pacman (pixel)
        pacman_pixel_x, pacman_pixel_y = self.game.pacman_pos
        center_x = int(pacman_pixel_x * cell_size + cell_size // 2)
        center_y = int(pacman_pixel_y * cell_size + cell_size // 2)
        
        # Hướng di chuyển
        dx, dy = self.game.ai.last_direction
        
        # Màu mũi tên: đỏ nếu escape mode, xanh dương nếu bình thường
        arrow_color = (255, 50, 50) if self.game.ai.escape_mode else (50, 150, 255)
        
        # Vẽ mũi tên
        arrow_length = cell_size * 0.7
        end_x = center_x + int(dx * arrow_length)
        end_y = center_y + int(dy * arrow_length)
        
        # Vẽ thân mũi tên (dày hơn)
        pygame.draw.line(screen, arrow_color, (center_x, center_y), (end_x, end_y), 5)
        
        # Vẽ đầu mũi tên
        if dx != 0 or dy != 0:
            arrow_head_size = 10
            # Tính góc vuông góc
            if dx != 0:
                perp_dx, perp_dy = 0, 1
            else:
                perp_dx, perp_dy = 1, 0
            
            # 2 điểm của đầu mũi tên
            head_point1 = (end_x - dx * arrow_head_size + perp_dx * arrow_head_size,
                          end_y - dy * arrow_head_size + perp_dy * arrow_head_size)
            head_point2 = (end_x - dx * arrow_head_size - perp_dx * arrow_head_size,
                          end_y - dy * arrow_head_size - perp_dy * arrow_head_size)
            
            pygame.draw.polygon(screen, arrow_color, [(end_x, end_y), head_point1, head_point2])
    
    def _render_threat_zones(self, overlay, cell_size):
        """Render threat zones around ghosts"""
        if 'ghosts' not in self.current_frame_data:
            return
        
        for ghost_data in self.current_frame_data['ghosts']:
            if ghost_data['is_eyes'] or ghost_data['scared']:
                continue
            
            ghost_row, ghost_col = ghost_data['pos']
            threat_level = ghost_data['threat_level']
            
            # Determine color and radius based on threat level
            if threat_level == 'CRITICAL':
                color = self.COLORS['critical_threat']
                radius = 3
            elif threat_level == 'HIGH':
                color = self.COLORS['high_threat']
                radius = 5
            elif threat_level == 'MEDIUM':
                color = self.COLORS['medium_threat']
                radius = 6
            else:
                color = self.COLORS['low_threat']
                radius = 8
            
            # Draw threat zone circles
            for r in range(1, radius + 1):
                circle_alpha = int(128 * (1 - r / (radius + 1)))
                circle_color = (*color[:3], circle_alpha)
                center_x = ghost_col * cell_size + cell_size // 2
                center_y = ghost_row * cell_size + cell_size // 2
                pygame.draw.circle(overlay, circle_color, (center_x, center_y), 
                                 r * cell_size, 2)
    
    def _render_safety_scores(self, overlay, cell_size):
        """Render safety scores as colored cells"""
        if 'safety_map' not in self.current_frame_data:
            return
        
        safety_map = self.current_frame_data['safety_map']
        
        # Normalize scores for color mapping
        if not safety_map:
            return
        
        max_score = max(safety_map.values()) if safety_map else 1
        min_score = min(safety_map.values()) if safety_map else 0
        score_range = max_score - min_score if max_score != min_score else 1
        
        for (row, col), score in safety_map.items():
            # Normalize score to 0-1
            normalized = (score - min_score) / score_range if score_range > 0 else 0.5
            
            # Color gradient from red (0) to green (1)
            if normalized < 0.5:
                # Red to yellow
                r = 255
                g = int(255 * (normalized * 2))
                b = 0
            else:
                # Yellow to green
                r = int(255 * (2 - normalized * 2))
                g = 255
                b = 0
            
            color = (r, g, b, 80)
            
            # Draw colored cell
            rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)
            pygame.draw.rect(overlay, color, rect)
            
            # Draw score text for ALL scores - always white for visibility
            text_color = (255, 255, 255, 255)  # White text for all scores
            
            score_text = self.font_small.render(f"{int(score)}", True, text_color)
            text_x = col * cell_size + cell_size // 4
            text_y = row * cell_size + cell_size // 4
            overlay.blit(score_text, (text_x, text_y))
    
    def _render_predictions(self, overlay, cell_size):
        """Render predicted paths for Pacman and ghosts"""
        if 'ghosts' not in self.current_frame_data:
            return
        
        pacman_row, pacman_col = self.current_frame_data['pacman_pos']
        pacman_dir = self.game.pacman_direction
        
        # Predict Pacman's path
        for step in range(1, 6):
            future_col = pacman_col + pacman_dir[0] * step
            future_row = pacman_row + pacman_dir[1] * step
            
            if not self.game.is_valid_position(future_col, future_row):
                break
            
            alpha = int(200 * (1 - step / 6))
            color = (0, 255, 255, alpha)  # Cyan
            center_x = future_col * cell_size + cell_size // 2
            center_y = future_row * cell_size + cell_size // 2
            pygame.draw.circle(overlay, color, (center_x, center_y), cell_size // 4)
        
        # Predict ghost paths
        for ghost_data in self.current_frame_data['ghosts']:
            if ghost_data['is_eyes'] or ghost_data['scared']:
                continue
            
            ghost_row, ghost_col = ghost_data['pos']
            ghost_dir = ghost_data['direction']
            
            for step in range(1, 6):
                future_col = ghost_col + ghost_dir[0] * step
                future_row = ghost_row + ghost_dir[1] * step
                
                if not self.game.is_valid_position(future_col, future_row):
                    break
                
                alpha = int(150 * (1 - step / 6))
                color = (255, 0, 255, alpha)  # Magenta
                center_x = future_col * cell_size + cell_size // 2
                center_y = future_row * cell_size + cell_size // 2
                pygame.draw.circle(overlay, color, (center_x, center_y), cell_size // 5)
    
    def _render_escape_routes(self, overlay, cell_size):
        """Render possible escape routes"""
        if 'decisions' not in self.current_frame_data:
            return
        
        if not self.current_frame_data['decisions']['escape_mode']:
            return
        
        pacman_row, pacman_col = self.current_frame_data['pacman_pos']
        
        # Highlight escape direction
        escape_dirs = self.current_frame_data['decisions']['direction_history']
        if escape_dirs:
            last_dir = escape_dirs[-1]
            for step in range(1, 4):
                escape_col = pacman_col + last_dir[0] * step
                escape_row = pacman_row + last_dir[1] * step
                
                if not self.game.is_valid_position(escape_col, escape_row):
                    break
                
                color = self.COLORS['escape_route']
                rect = pygame.Rect(escape_col * cell_size + 2, escape_row * cell_size + 2,
                                 cell_size - 4, cell_size - 4)
                pygame.draw.rect(overlay, color, rect, 3)
    
    def _render_decision_info(self, screen):
        """Render decision tree information"""
        if 'decisions' not in self.current_frame_data:
            return
        
        decisions = self.current_frame_data['decisions']
        # Position aligned with FPS panel, below Performance Metrics
        panel_height = 150  # Tăng từ 130
        panel_width = 240
        maze_width = self.game.maze_gen.width * self.game.cell_size
        x_offset = maze_width + 5
        y_offset = 275  # Tăng từ 260 (do panel trên cao hơn)
        
        # Background panel
        panel_rect = pygame.Rect(x_offset, y_offset, 240, 150)  # Tăng từ 130
        pygame.draw.rect(screen, (0, 0, 0, 180), panel_rect)
        pygame.draw.rect(screen, (255, 255, 255), panel_rect, 2)
        
        # Title
        title = self.font_medium.render("AI Decision State", True, (255, 255, 0))
        screen.blit(title, (x_offset + 10, y_offset + 10))
        y_offset += 30
        
        # Decision info
        info_lines = [
            f"Escape Mode: {'YES' if decisions['escape_mode'] else 'NO'}",
            f"Escape Steps: {decisions['escape_steps']}",
            f"Consecutive Turns: {decisions['consecutive_turns']}",
            f"Total Turns: {decisions['turn_count']}",
            f"Forced Moves: {decisions['force_movement_counter']}",
            f"Timeout Count: {decisions['escape_timeout_count']}",
        ]
        
        for line in info_lines:
            color = (255, 255, 255)
            if 'YES' in line or decisions['escape_mode']:
                color = (255, 100, 100)  # Red for escape mode
            
            text = self.font_small.render(line, True, color)
            screen.blit(text, (x_offset + 10, y_offset))
            y_offset += 18
    
    def _render_metrics(self, screen):
        """Render performance metrics"""
        # Move to right side (middle position)
        panel_height = 125  # Tăng từ 110
        panel_width = 240
        # Position aligned with FPS panel, below it
        maze_width = self.game.maze_gen.width * self.game.cell_size
        x_offset = maze_width + 5
        y_offset = 140
        
        # Background panel
        panel_rect = pygame.Rect(x_offset, y_offset, 240, 125)  # Tăng từ 110
        pygame.draw.rect(screen, (0, 0, 0, 180), panel_rect)
        pygame.draw.rect(screen, (255, 255, 255), panel_rect, 2)
        
        # Title
        title = self.font_medium.render("Performance Metrics", True, (0, 255, 0))
        screen.blit(title, (x_offset + 10, y_offset + 10))
        y_offset += 30
        
        # Metrics
        success_rate = 0
        total_escapes = self.metrics['successful_escapes'] + self.metrics['failed_escapes']
        if total_escapes > 0:
            success_rate = (self.metrics['successful_escapes'] / total_escapes) * 100
        
        metrics_lines = [
            f"Total Avoidances: {self.metrics['total_avoidances']}",
            f"Successful Escapes: {self.metrics['successful_escapes']}",
            f"Failed Escapes: {self.metrics['failed_escapes']}",
            f"Success Rate: {success_rate:.1f}%",
            f"Loop Detections: {self.metrics['loop_detections']}",
        ]
        
        for line in metrics_lines:
            text = self.font_small.render(line, True, (255, 255, 255))
            screen.blit(text, (x_offset + 10, y_offset))
            y_offset += 18
    
    def log_escape_attempt(self, success, duration, threat_level):
        """
        Log an escape attempt
        
        Args:
            success: bool - whether escape was successful
            duration: int - time in ms
            threat_level: str - threat level at start
        """
        self.metrics['total_avoidances'] += 1
        if success:
            self.metrics['successful_escapes'] += 1
        else:
            self.metrics['failed_escapes'] += 1
        
        self.metrics['threat_level_distribution'][threat_level] += 1
        
        self.escape_history.append({
            'time': pygame.time.get_ticks(),
            'success': success,
            'duration': duration,
            'threat_level': threat_level,
        })
    
    def log_loop_detection(self):
        """Log anti-loop mechanism trigger"""
        self.metrics['loop_detections'] += 1
    
    def log_forced_movement(self):
        """Log forced movement trigger"""
        self.metrics['forced_movements'] += 1
    
    def log_death(self, ghost_data, decisions):
        """
        Log death event for analysis
        
        Args:
            ghost_data: ghost information at death
            decisions: AI decisions leading to death
        """
        self.death_analysis.append({
            'time': datetime.now().isoformat(),
            'ghost_data': ghost_data,
            'decisions': decisions,
            'recent_history': list(self.decision_history)[-10:],
        })
    
    def save_analysis_report(self, filename=None):
        """
        Save comprehensive analysis report
        
        Args:
            filename: optional filename, defaults to timestamp
        """
        if filename is None:
            filename = f"ghost_avoidance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': dict(self.metrics),
            'death_analysis': self.death_analysis,
            'escape_history': list(self.escape_history),
            'recent_decisions': list(self.decision_history)[-20:],
        }
        
        # Convert defaultdict to regular dict
        report['metrics']['threat_level_distribution'] = dict(report['metrics']['threat_level_distribution'])
        report['metrics']['decision_types'] = dict(report['metrics']['decision_types'])
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"✅ Analysis report saved to: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error saving report: {e}")
            return False
    
    def toggle_visualization(self):
        """Toggle visualization on/off"""
        self.enabled = not self.enabled
        status = "ENABLED" if self.enabled else "DISABLED"
        print(f"🔄 Ghost Avoidance Visualization: {status}")
    
    def print_real_time_analysis(self):
        """Print real-time analysis to console"""
        if not self.current_frame_data:
            return
        
        print("\n" + "="*60)
        print("GHOST AVOIDANCE REAL-TIME ANALYSIS")
        print("="*60)
        
        # Pacman state
        pacman_pos = self.current_frame_data['pacman_pos']
        print(f"\n📍 Pacman Position: {pacman_pos}")
        
        # Ghost threats
        if 'threats' in self.current_frame_data:
            print(f"\n👻 Active Threats: {len(self.current_frame_data['threats'])}")
            for i, threat in enumerate(self.current_frame_data['threats'][:3]):
                print(f"   {i+1}. Distance: {threat['distance']}, "
                      f"Score: {threat['threat_score']:.1f}, "
                      f"LOS: {'Yes' if threat['has_los'] else 'No'}")
        
        # AI decisions
        if 'decisions' in self.current_frame_data:
            decisions = self.current_frame_data['decisions']
            print(f"\n🤖 AI State:")
            print(f"   Escape Mode: {decisions['escape_mode']}")
            print(f"   Escape Steps: {decisions['escape_steps']}")
            print(f"   Consecutive Turns: {decisions['consecutive_turns']}")
            print(f"   Force Movements: {decisions['force_movement_counter']}")
        
        # Safety analysis
        if 'safety_map' in self.current_frame_data:
            safety_map = self.current_frame_data['safety_map']
            if safety_map:
                avg_safety = sum(safety_map.values()) / len(safety_map)
                max_safety = max(safety_map.values())
                min_safety = min(safety_map.values())
                print(f"\n🛡️  Safety Analysis:")
                print(f"   Average Safety: {avg_safety:.1f}")
                print(f"   Max Safety: {max_safety:.1f}")
                print(f"   Min Safety: {min_safety:.1f}")
        
        print("="*60 + "\n")


# Standalone test mode
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   GHOST AVOIDANCE VISUALIZER & DEBUGGER                 ║
    ║   ────────────────────────────────────────────           ║
    ║   Công cụ debug và phân tích AI ghost avoidance         ║
    ╚══════════════════════════════════════════════════════════╝
    
    🎯 Features:
       • Real-time threat zone visualization
       • Safety score heatmap
       • Movement prediction display
       • Escape route tracking
       • Performance metrics
       • Decision tree analysis
       
    🎮 Controls (when integrated):
       • V - Toggle visualization
       • D - Toggle debug info
       • S - Save analysis report
       
    📝 Usage:
       1. Import vào game chính:
          from ghost_avoidance_visualizer import GhostAvoidanceVisualizer
          visualizer = GhostAvoidanceVisualizer(game_instance)
          
       2. Update mỗi frame:
          visualizer.update(pacman_ai_instance)
          
       3. Render overlay:
          visualizer.render(screen, cell_size)
    
    ⚠️  Note: File này cần được integrate vào pacman_game.py
              để hoạt động đầy đủ. Xem hướng dẫn integrate bên dưới.
    """)
    
    print("\n" + "="*60)
    print("INTEGRATION GUIDE")
    print("="*60)
    print("""
1. Trong pacman_game.py, thêm import:
   from ghost_avoidance_visualizer import GhostAvoidanceVisualizer

2. Trong __init__ của PacmanGame:
   self.visualizer = GhostAvoidanceVisualizer(self)

3. Trong game loop, sau khi update AI:
   self.visualizer.update(self.pacman_ai)

4. Trong render, trước khi pygame.display.flip():
   self.visualizer.render(self.screen, self.cell_size)

5. Trong event handling, thêm:
   if event.key == pygame.K_v:
       self.visualizer.toggle_visualization()
   if event.key == pygame.K_d:
       self.visualizer.print_real_time_analysis()
   if event.key == pygame.K_s:
       self.visualizer.save_analysis_report()

6. Khi Pacman chết, thêm:
   self.visualizer.log_death(ghost_data, ai_decisions)
    """)
    print("="*60)

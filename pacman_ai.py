import pygame
import random
import math
import config


class PacmanAI:
    """
    Lớp xử lý thuật toán AI cho Pacman, bao gồm:
    - Thuật toán né ma (ghost avoidance)
    - Tìm đường đi an toàn (pathfinding with safety)
    - Logic di chuyển thông minh (intelligent movement)
    """
    
    def __init__(self, game_instance):
        """
        Khởi tạo AI với tham chiếu đến game instance
        
        Args:
            game_instance: Instance của PacmanGame để truy cập maze, ghosts, etc.
        """
        self.game = game_instance
        
        # Ghost avoidance variables
        self.escape_mode = False  # Đang trong chế độ thoát hiểm
        self.escape_steps = 0     # Số bước đã di chuyển thoát hiểm
        self.min_escape_distance = 6  # Tối thiểu 6 bước trước khi quay lại
        self.original_direction = None  # Hướng đi ban đầu trước khi quay đầu
        
        # Emergency turn tracking
        self.last_emergency_turn = 0
        self.last_turn_direction = None
        self.turn_count = 0
        self.consecutive_turns = 0
        
        # Path avoidance on route to goal
        self.path_avoidance_mode = False
        self.path_avoidance_start_time = 0
        self.path_avoidance_direction = None
        self.original_goal_path = []
        self.temporary_avoidance_target = None
        
        # Advanced tracking
        self.continuous_avoidance_count = 0
    
    def set_escape_target(self):
        """Set target to exit gate for emergency escape"""
        if hasattr(self.game, 'exit_gate'):
            self.game.auto_target = self.game.exit_gate
            self.game.calculate_auto_path()
        else:
            pass
    
    def emergency_ghost_avoidance(self, nearby_ghosts):
        """
        ENHANCED Emergency ghost avoidance với adaptive response và anti-loop mechanism
        """
        current_time = pygame.time.get_ticks()

        # Khởi tạo biến nếu chưa có
        if not hasattr(self, 'last_emergency_turn'):
            self.last_emergency_turn = 0
        if not hasattr(self, 'last_turn_direction'):
            self.last_turn_direction = None
        if not hasattr(self, 'turn_count'):
            self.turn_count = 0
        if not hasattr(self, 'consecutive_turns'):
            self.consecutive_turns = 0
        if not hasattr(self, 'recent_deaths'):
            self.recent_deaths = 0
        if not hasattr(self, 'escape_direction_history'):
            self.escape_direction_history = []
        if not hasattr(self, 'last_escape_time'):
            self.last_escape_time = 0
        if not hasattr(self, 'escape_timeout_count'):
            self.escape_timeout_count = 0

        # ANTI-LOOP MECHANISM - Detect if stuck in escape loop
        if len(self.escape_direction_history) > 5:
            # Check if repeating same direction too much
            recent_directions = self.escape_direction_history[-6:]
            if len(set(map(tuple, recent_directions))) <= 2:  # Only 1-2 unique directions
                print(f"🔄 ESCAPE LOOP DETECTED! Clearing history and trying new strategy")
                self.escape_direction_history.clear()
                self.escape_timeout_count += 1
                # Force longer cooldown to break the loop
                adaptive_cooldown = 100 + (self.escape_timeout_count * 50)
            else:
                # Normal adaptive cooldown
                base_cooldown = 30 if self.consecutive_turns <= 1 else 60
                adaptive_cooldown = max(10, base_cooldown - (self.recent_deaths * 5))
        else:
            base_cooldown = 30 if self.consecutive_turns <= 1 else 60
            adaptive_cooldown = max(10, base_cooldown - (self.recent_deaths * 5))
        
        if current_time - self.last_emergency_turn < adaptive_cooldown:
            return False

        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        
        # ENHANCED THREAT ANALYSIS với priority scoring
        danger_analysis = []
        for ghost_pos, distance in nearby_ghosts:
            ghost_row, ghost_col = ghost_pos
            
            # Tính threat score tổng hợp
            threat_score = self._calculate_comprehensive_threat_score(
                pacman_row, pacman_col, ghost_row, ghost_col, distance
            )
            
            danger_analysis.append({
                'pos': (ghost_row, ghost_col),
                'distance': distance,
                'threat_score': threat_score,
                'threat_vector': [pacman_col - ghost_col, pacman_row - ghost_row]
            })

        # Sắp xếp theo threat score (cao nhất trước)
        danger_analysis.sort(key=lambda x: x['threat_score'], reverse=True)
        
        if not danger_analysis:
            return False

        # Lấy ghost nguy hiểm nhất
        primary_threat = danger_analysis[0]
        min_distance = primary_threat['distance']

        # === ENHANCED RESPONSE SYSTEM với MULTI-DIRECTIONAL ESCAPE ===
        
        # LEVEL 1: CRITICAL (≤ 3 ô hoặc high threat score) 
        if min_distance <= 3 or primary_threat['threat_score'] >= 80:
            success = self._handle_critical_danger_enhanced(pacman_row, pacman_col, danger_analysis, current_time)
            if success:
                # Track escape direction để tránh loop
                chosen_direction = self.game.pacman_direction
                self.escape_direction_history.append(chosen_direction)
                if len(self.escape_direction_history) > 10:
                    self.escape_direction_history.pop(0)  # Keep only recent 10
                return True
        
        # LEVEL 2: HIGH DANGER (4-5 ô với moderate threat)
        elif min_distance <= 5 or primary_threat['threat_score'] >= 60:
            success = self._handle_high_danger_enhanced(pacman_row, pacman_col, danger_analysis, current_time)
            if success:
                chosen_direction = self.game.pacman_direction
                self.escape_direction_history.append(chosen_direction)
                if len(self.escape_direction_history) > 10:
                    self.escape_direction_history.pop(0)
                return True
        
        # LEVEL 3: MODERATE DANGER (6+ ô với low threat) - Preventive action
        elif primary_threat['threat_score'] >= 40:
            success = self._handle_moderate_danger(pacman_row, pacman_col, danger_analysis, current_time)
            if success:
                chosen_direction = self.game.pacman_direction
                self.escape_direction_history.append(chosen_direction)
                if len(self.escape_direction_history) > 10:
                    self.escape_direction_history.pop(0)
                return True
        
        return False

    def _calculate_comprehensive_threat_score(self, pacman_row, pacman_col, ghost_row, ghost_col, distance):
        """
        Tính threat score tổng hợp dựa trên nhiều yếu tố
        """
        score = 0
        
        # 1. Distance factor (closer = more dangerous)
        distance_score = max(0, 100 - (distance * 15))  # 100 at distance 0, decreases by 15 per block
        score += distance_score
        
        # 2. Line of sight factor
        if self._has_line_of_sight((pacman_row, pacman_col), (ghost_row, ghost_col)):
            score += 30
        elif self._has_relaxed_line_of_sight((pacman_row, pacman_col), (ghost_row, ghost_col)):
            score += 15
        
        # 3. Same corridor factor
        if ghost_row == pacman_row or ghost_col == pacman_col:
            score += 25
        
        # 4. Predictive movement factor
        ghost = None
        for g in self.game.ghosts:
            if int(g['pos'][1]) == ghost_row and int(g['pos'][0]) == ghost_col:
                ghost = g
                break
        
        if ghost and self._predictive_collision_check(pacman_row, pacman_col, ghost_row, ghost_col, ghost, distance):
            score += 40
        
        # 5. Escape route factor - penalize if limited escape routes
        escape_routes = self._count_escape_routes(pacman_row, pacman_col)
        if escape_routes <= 1:
            score += 20
        elif escape_routes <= 2:
            score += 10
        
        return min(100, score)  # Cap at 100

    def _count_escape_routes(self, row, col):
        """Count available escape routes from current position, bỏ qua ghost eyes"""
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        escape_count = 0
        
        for dx, dy in directions:
            test_col, test_row = col + dx, row + dy
            if self.game.is_valid_position_ignore_eyes(test_col, test_row):
                # Check if this direction leads to open space (not dead end)
                if not self._is_dead_end(test_col, test_row):
                    escape_count += 1
        
        return escape_count

    def _handle_critical_danger_enhanced(self, pacman_row, pacman_col, danger_analysis, current_time):
        """
        ENHANCED Critical danger handler với smart escape và multi-ghost awareness và ANTI-LOOP
        """
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        escape_options = []
        
        # ANTI-LOOP: Tránh các hướng đã dùng gần đây nếu có thể
        recently_used_directions = set()
        if hasattr(self, 'escape_direction_history') and len(self.escape_direction_history) > 3:
            recently_used_directions = set(map(tuple, self.escape_direction_history[-4:]))
        
        for dx, dy in directions:
            new_col, new_row = pacman_col + dx, pacman_row + dy
            
            if not self.game.is_valid_position(new_col, new_row):
                continue
                
            # ENHANCED safety calculation với multi-ghost awareness
            safety_score = self._calculate_enhanced_safety_score(
                new_row, new_col, danger_analysis, 
                pacman_row, pacman_col, (dx, dy)
            )
            
            # ANTI-LOOP BONUS: Prefer directions not used recently
            if (dx, dy) not in recently_used_directions:
                safety_score += 20  # Bonus for fresh directions
                print(f"🆕 Fresh direction [{dx}, {dy}] gets bonus, score: {safety_score}")
            elif len(recently_used_directions) > 0:
                safety_score -= 15  # Penalty for repeated directions
                print(f"♻️  Repeated direction [{dx}, {dy}] gets penalty, score: {safety_score}")
            
            escape_options.append((dx, dy, safety_score))
        
        if escape_options:
            # Sắp xếp theo safety score
            escape_options.sort(key=lambda x: x[2], reverse=True)
            
            # ENHANCED SELECTION: If top 2-3 options are close in score, randomize to avoid predictability
            if len(escape_options) > 1:
                top_score = escape_options[0][2]
                good_options = [opt for opt in escape_options if opt[2] >= top_score - 8]
                if len(good_options) > 1:
                    import random
                    chosen = random.choice(good_options)
                    dx, dy, score = chosen
                    print(f"🎲 Randomizing among {len(good_options)} good options, chose: [{dx}, {dy}]")
                else:
                    dx, dy, score = escape_options[0]
                    print(f"🎯 Clear best option: [{dx}, {dy}] (score: {score})")
            else:
                dx, dy, score = escape_options[0]
            
            self.game.pacman_next_direction = [dx, dy]
            self.last_emergency_turn = current_time
            self._update_turn_tracking((dx, dy))
            
            # ENHANCED escape mode với adaptive duration
            self.escape_mode = True
            self.escape_steps = 0
            self.min_escape_distance = min(4, len(danger_analysis) + 1)  # Adaptive based on ghost count
            
            return True
        
        # Fallback: stay in place if no good options
        return False

    def _handle_high_danger_enhanced(self, pacman_row, pacman_col, danger_analysis, current_time):
        """
        ENHANCED High danger handler với predictive movement selection
        """
        current_dir = self.game.pacman_direction
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        # Phân loại movement options
        forward_dir = current_dir
        backward_dir = [-current_dir[0], -current_dir[1]]
        side_dirs = [d for d in directions if d != forward_dir and d != backward_dir]
        
        movement_options = []
        
        # ENHANCED evaluation cho từng hướng
        # 1. Side movements (turns) - highest priority
        for dx, dy in side_dirs:
            new_col, new_row = pacman_col + dx, pacman_row + dy
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_enhanced_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, (dx, dy)
                )
                # BONUS for turning + future safety
                future_safety = self._calculate_future_safety(new_row, new_col, (dx, dy), danger_analysis)
                total_score = safety_score + 15 + future_safety
                movement_options.append((dx, dy, total_score, 'turn'))
        
        # 2. Forward movement - modified priority
        if forward_dir != [0, 0]:
            new_col = pacman_col + forward_dir[0]
            new_row = pacman_row + forward_dir[1]
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_enhanced_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, forward_dir
                )
                future_safety = self._calculate_future_safety(new_row, new_col, forward_dir, danger_analysis)
                total_score = safety_score + 5 + future_safety
                movement_options.append((forward_dir[0], forward_dir[1], total_score, 'forward'))
        
        # 3. Backward movement - last resort với smart evaluation
        if len(movement_options) == 0 or max(opt[2] for opt in movement_options) < 15:
            new_col = pacman_col + backward_dir[0]
            new_row = pacman_row + backward_dir[1]
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_enhanced_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, backward_dir
                )
                # Reduced penalty if it's genuinely safer
                penalty = 3 if safety_score > 20 else 8
                total_score = safety_score - penalty
                movement_options.append((backward_dir[0], backward_dir[1], total_score, 'backward'))
        
        # Select best movement
        if movement_options:
            movement_options.sort(key=lambda x: x[2], reverse=True)
            best_move = movement_options[0]
            dx, dy, score, move_type = best_move
            
            # Execute if score is acceptable
            if score > 10 or move_type in ['turn', 'forward']:
                self.game.pacman_next_direction = [dx, dy]
                self.last_emergency_turn = current_time
                self._update_turn_tracking((dx, dy))
                
                # Conditional escape mode
                if move_type == 'backward' or score < 20:
                    self.escape_mode = True
                    self.escape_steps = 0
                    self.min_escape_distance = 2
                
                return True
        
        return False

    def _handle_moderate_danger(self, pacman_row, pacman_col, danger_analysis, current_time):
        """
        NEW: Handle moderate danger với preventive path adjustment
        """
        current_dir = self.game.pacman_direction
        
        # Check if current path is leading into danger
        if current_dir != [0, 0]:
            future_pos = (pacman_row + current_dir[1], pacman_col + current_dir[0])
            future_danger = self._evaluate_position_danger(future_pos[0], future_pos[1], danger_analysis)
            
            if future_danger > 30:  # Moderate danger threshold
                # Look for alternative path
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                best_alternative = None
                best_score = -1
                
                for dx, dy in directions:
                    if [dx, dy] == current_dir:  # Skip current direction
                        continue
                        
                    new_col, new_row = pacman_col + dx, pacman_row + dy
                    if self.game.is_valid_position(new_col, new_row):
                        safety_score = self._calculate_enhanced_safety_score(
                            new_row, new_col, danger_analysis,
                            pacman_row, pacman_col, (dx, dy)
                        )
                        
                        if safety_score > best_score:
                            best_score = safety_score
                            best_alternative = (dx, dy)
                
                if best_alternative and best_score > future_danger + 10:
                    self.game.pacman_next_direction = list(best_alternative)
                    self.last_emergency_turn = current_time
                    return True
        
        return False

    def _calculate_enhanced_safety_score(self, test_row, test_col, danger_analysis, 
                                       current_row, current_col, direction):
        """
        ENHANCED safety score calculation với comprehensive threat assessment
        """
        score = 0
        
        # 1. Multi-ghost distance analysis
        ghost_distances = []
        for ghost in danger_analysis:
            ghost_row, ghost_col = ghost['pos']
            distance = abs(test_row - ghost_row) + abs(test_col - ghost_col)
            threat_score = ghost.get('threat_score', 0)
            
            # Weight distance by threat score
            weighted_distance = distance * (1 + threat_score / 100)
            ghost_distances.append(weighted_distance)
            
        if ghost_distances:
            min_weighted_dist = min(ghost_distances)
            avg_weighted_dist = sum(ghost_distances) / len(ghost_distances)
            
            score += min_weighted_dist * 5  # Primary ghost avoidance
            score += avg_weighted_dist * 2  # General safety from all ghosts
        
        # 2. Enhanced dead end detection
        if not self._is_dead_end(test_col, test_row):
            score += 15
            
            # Bonus for positions with multiple escape routes
            escape_routes = self._count_escape_routes(test_row, test_col)
            score += escape_routes * 3
        else:
            score -= 12
        
        # 3. Movement direction analysis
        for ghost in danger_analysis:
            ghost_row, ghost_col = ghost['pos']
            
            # Check if moving away from ghost
            current_dist = abs(current_row - ghost_row) + abs(current_col - ghost_col)
            new_dist = abs(test_row - ghost_row) + abs(test_col - test_col)
            
            if new_dist > current_dist:
                score += 8  # Bonus for increasing distance
            elif new_dist < current_dist:
                score -= 6  # Penalty for decreasing distance
        
        # 4. Line of sight considerations
        total_los_penalty = 0
        for ghost in danger_analysis:
            ghost_pos = ghost['pos']
            if self._has_line_of_sight((test_row, test_col), ghost_pos):
                total_los_penalty += 4
            elif not self._has_relaxed_line_of_sight((test_row, test_col), ghost_pos):
                score += 3  # Bonus for breaking line of sight
        
        score -= total_los_penalty
        
        return score

    def _calculate_future_safety(self, row, col, direction, danger_analysis, steps=2):
        """
        Calculate safety of future positions trong direction này
        """
        future_safety = 0
        
        for step in range(1, steps + 1):
            future_row = row + direction[1] * step
            future_col = col + direction[0] * step
            
            if not self.game.is_valid_position(future_col, future_row):
                future_safety -= 5  # Penalty for hitting wall
                break
            
            # Calculate danger at future position
            min_future_dist = float('inf')
            for ghost in danger_analysis:
                ghost_row, ghost_col = ghost['pos']
                dist = abs(future_row - ghost_row) + abs(future_col - ghost_col)
                min_future_dist = min(min_future_dist, dist)
            
            if min_future_dist == float('inf'):
                continue
                
            # Score based on future safety
            if min_future_dist >= 4:
                future_safety += 3
            elif min_future_dist >= 2:
                future_safety += 1
            else:
                future_safety -= 4
        
        return future_safety

    def _evaluate_position_danger(self, row, col, danger_analysis):
        """
        Evaluate danger level at specific position
        """
        if not self.game.is_valid_position(col, row):
            return 100  # Maximum danger for invalid positions
            
        danger = 0
        
        for ghost in danger_analysis:
            ghost_row, ghost_col = ghost['pos']
            distance = abs(row - ghost_row) + abs(col - ghost_col)
            threat_score = ghost.get('threat_score', 50)
            
            # Distance-based danger
            if distance <= 1:
                danger += 50
            elif distance <= 2:
                danger += 30
            elif distance <= 3:
                danger += 15
            
            # Threat score influence
            danger += max(0, (threat_score - 30) / 10)
        
        return min(100, danger)

    def _handle_critical_danger(self, pacman_row, pacman_col, danger_analysis, current_time):
        """Xử lý nguy hiểm cấp độ 1: Ma rất gần (≤2 ô)"""
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        escape_options = []
        
        for dx, dy in directions:
            new_col, new_row = pacman_col + dx, pacman_row + dy
            
            if not self.game.is_valid_position(new_col, new_row):
                continue
                
            # Tính điểm an toàn cho hướng này
            safety_score = self._calculate_safety_score(
                new_row, new_col, danger_analysis, 
                pacman_row, pacman_col, (dx, dy)
            )
            
            escape_options.append((dx, dy, safety_score))
        
        if escape_options:
            # Chọn hướng an toàn nhất
            escape_options.sort(key=lambda x: x[2], reverse=True)
            best_escape = escape_options[0]
            dx, dy, score = best_escape
            
            self.game.pacman_next_direction = [dx, dy]
            self.last_emergency_turn = current_time
            self._update_turn_tracking((dx, dy))
            
            # Kích hoạt escape mode ngắn
            self.escape_mode = True
            self.escape_steps = 0
            self.min_escape_distance = 2
            
            return True
        
        return False

    def _handle_high_danger(self, pacman_row, pacman_col, danger_analysis, current_time):
        """Xử lý nguy hiểm cấp độ 2: Ma gần (3-4 ô) - Ưu tiên ngã rẽ"""
        current_dir = self.game.pacman_direction
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        
        # Phân loại các hướng di chuyển
        forward_dir = current_dir
        backward_dir = [-current_dir[0], -current_dir[1]]
        side_dirs = [d for d in directions if d != forward_dir and d != backward_dir]
        
        # Ưu tiên: 1) Ngã rẽ, 2) Tiến thẳng (nếu an toàn), 3) Quay đầu (cuối cùng)
        movement_options = []
        
        # 1. Kiểm tra ngã rẽ trước (ưu tiên cao nhất)
        for dx, dy in side_dirs:
            new_col, new_row = pacman_col + dx, pacman_row + dy
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, (dx, dy)
                )
                # Bonus cho ngã rẽ
                movement_options.append((dx, dy, safety_score + 10, 'turn'))
        
        # 2. Kiểm tra tiến thẳng
        if forward_dir != [0, 0]:
            new_col = pacman_col + forward_dir[0]
            new_row = pacman_row + forward_dir[1]
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, forward_dir
                )
                movement_options.append((forward_dir[0], forward_dir[1], safety_score + 5, 'forward'))
        
        # 3. Quay đầu (chỉ khi thực sự cần thiết)
        if len(movement_options) == 0 or max(opt[2] for opt in movement_options) < 5:
            new_col = pacman_col + backward_dir[0]
            new_row = pacman_row + backward_dir[1]
            if self.game.is_valid_position(new_col, new_row):
                safety_score = self._calculate_safety_score(
                    new_row, new_col, danger_analysis,
                    pacman_row, pacman_col, backward_dir
                )
                # Penalty cho quay đầu, nhưng vẫn cần thiết nếu không có lựa chọn
                penalty = 5 if self.consecutive_turns >= 2 else 2
                movement_options.append((backward_dir[0], backward_dir[1], safety_score - penalty, 'backward'))
        
        # Chọn hướng tốt nhất
        if movement_options:
            movement_options.sort(key=lambda x: x[2], reverse=True)
            best_move = movement_options[0]
            dx, dy, score, move_type = best_move
            
            # Chỉ thực hiện nếu đủ an toàn hoặc không có lựa chọn
            if score > 3 or move_type in ['turn', 'forward']:
                self.game.pacman_next_direction = [dx, dy]
                self.last_emergency_turn = current_time
                self._update_turn_tracking((dx, dy))
                
                # Escape mode ngắn hơn cho level này
                if move_type == 'backward':
                    self.escape_mode = True
                    self.escape_steps = 0
                    self.min_escape_distance = 1
                
                return True
        
        return False

    def _calculate_safety_score(self, test_row, test_col, danger_analysis, 
                              current_row, current_col, direction):
        """Tính điểm an toàn cho một vị trí với nhiều yếu tố"""
        score = 0
        
        # 1. Khoảng cách đến ma gần nhất
        min_dist_to_ghost = min(
            abs(test_row - ghost['pos'][0]) + abs(test_col - ghost['pos'][1])
            for ghost in danger_analysis
        )
        score += min_dist_to_ghost * 3  # Càng xa ma càng tốt
        
        # 2. Tránh dead end
        if not self._is_dead_end(test_col, test_row):
            score += 8
        else:
            score -= 5
        
        # 3. Kiểm tra có tạo khoảng cách lớn hơn hiện tại không
        current_min_dist = min(
            abs(current_row - ghost['pos'][0]) + abs(current_col - ghost['pos'][1])
            for ghost in danger_analysis
        )
        if min_dist_to_ghost > current_min_dist:
            score += 5  # Bonus nếu tăng khoảng cách
        
        # 4. Tránh di chuyển về phía ma
        for ghost in danger_analysis:
            ghost_row, ghost_col = ghost['pos']
            # Vector từ vị trí hiện tại đến ma
            to_ghost = [ghost_col - current_col, ghost_row - current_row]
            # Vector di chuyển
            move_vec = direction
            
            # Tính tích vô hướng để xem có di chuyển về phía ma không
            dot_product = to_ghost[0] * move_vec[0] + to_ghost[1] * move_vec[1]
            if dot_product > 0:  # Di chuyển về phía ma
                score -= 3
            else:  # Di chuyển ra xa ma
                score += 2
        
        # 5. Kiểm tra có line of sight với ma không (sau khi di chuyển)
        for ghost in danger_analysis:
            if not self._has_line_of_sight((test_row, test_col), ghost['pos']):
                score += 4  # Bonus nếu sẽ mất line of sight với ma
        
        return score

    def _update_turn_tracking(self, new_direction):
        """Cập nhật tracking cho việc quay đầu"""
        if not hasattr(self, 'last_turn_direction'):
            self.last_turn_direction = None
            
        # Kiểm tra có phải quay đầu không (hướng ngược lại)
        current_dir = self.game.pacman_direction
        is_opposite = (new_direction[0] == -current_dir[0] and 
                      new_direction[1] == -current_dir[1])
        
        if is_opposite:
            self.consecutive_turns = getattr(self, 'consecutive_turns', 0) + 1
        else:
            self.consecutive_turns = 0
            
        self.last_turn_direction = new_direction

    def check_ghost_on_path_to_goal(self):
        """
        ENHANCED path checking với adaptive threat assessment và smart rerouting
        """
        if not self.game.current_goal:
            return False, None, 0
            
        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        current_pos = (pacman_row, pacman_col)
        
        # ENHANCED path analysis với extended checking
        if hasattr(self.game, 'auto_path') and self.game.auto_path and len(self.game.auto_path) > 0:
            # Check more steps ahead for better planning
            check_distance = min(12, len(self.game.auto_path))  # Increased from 8 to 12
            path_to_check = self.game.auto_path[:check_distance]
        else:
            # Enhanced direct path generation
            goal_row, goal_col = self.game.current_goal
            path_to_check = self._generate_smart_check_path(
                pacman_row, pacman_col, goal_row, goal_col
            )
        
        # MULTI-LAYER ghost checking
        threat_detected = False
        closest_threat = None
        min_threat_distance = float('inf')
        
        for ghost in self.game.ghosts:
            # BỎ QUA ghost đã bị ăn (chỉ còn eyes) - không nguy hiểm
            if self.game.can_pacman_pass_through_ghost(ghost):
                continue
                
            if ghost.get('scared', False):
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            ghost_pos = (ghost_row, ghost_col)
            
            # LAYER 1: Direct threat to Pacman
            distance_to_pacman = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            if distance_to_pacman <= 6:  # Increased detection range
                threat_level = self._assess_direct_threat(
                    current_pos, ghost_pos, distance_to_pacman, ghost
                )
                
                if threat_level > 60:  # High threat threshold
                    threat_detected = True
                    if distance_to_pacman < min_threat_distance:
                        min_threat_distance = distance_to_pacman
                        closest_threat = ghost_pos
            
            # LAYER 2: Path intersection analysis
            path_threat = self._analyze_path_intersection(
                path_to_check, ghost_pos, ghost, distance_to_pacman
            )
            
            if path_threat['is_threatening']:
                threat_detected = True
                if path_threat['distance'] < min_threat_distance:
                    min_threat_distance = path_threat['distance']
                    closest_threat = ghost_pos
                        
        return threat_detected, closest_threat, min_threat_distance

    def _generate_smart_check_path(self, start_row, start_col, goal_row, goal_col, max_steps=10):
        """
        Generate smarter path for checking threats
        """
        path = []
        steps = max(abs(goal_row - start_row), abs(goal_col - start_col))
        check_steps = min(max_steps, steps)
        
        if check_steps > 0:
            for i in range(1, check_steps + 1):
                progress = i / steps
                check_row = int(start_row + (goal_row - start_row) * progress)
                check_col = int(start_col + (goal_col - start_col) * progress)
                
                # Only add valid positions
                if self.game.is_valid_position(check_col, check_row):
                    path.append((check_row, check_col))
        
        return path

    def _assess_direct_threat(self, pacman_pos, ghost_pos, distance, ghost):
        """
        Assess direct threat level from ghost to Pacman
        """
        threat_score = 0
        
        # Distance factor
        if distance <= 2:
            threat_score += 80
        elif distance <= 4:
            threat_score += 60
        elif distance <= 6:
            threat_score += 40
        
        # Line of sight factor
        if self._has_line_of_sight(pacman_pos, ghost_pos):
            threat_score += 20
        elif self._has_relaxed_line_of_sight(pacman_pos, ghost_pos):
            threat_score += 10
        
        # Movement prediction
        if self._predictive_collision_check(
            pacman_pos[0], pacman_pos[1], ghost_pos[0], ghost_pos[1], ghost, distance
        ):
            threat_score += 30
        
        return threat_score

    def _analyze_path_intersection(self, path, ghost_pos, ghost, distance_to_pacman):
        """
        Analyze if ghost threatens the planned path
        """
        ghost_row, ghost_col = ghost_pos
        min_path_distance = float('inf')
        threatening_positions = 0
        
        for i, path_pos in enumerate(path):
            path_distance = abs(path_pos[0] - ghost_row) + abs(path_pos[1] - ghost_col)
            min_path_distance = min(min_path_distance, path_distance)
            
            # Check if ghost threatens this path position
            if path_distance <= 3:  # Close to path
                # Consider ghost movement
                ghost_direction = ghost.get('direction', [0, 0])
                steps_to_intercept = i + 1  # Steps for Pacman to reach this position
                
                # Predict where ghost will be
                future_ghost_col = ghost_col + ghost_direction[0] * steps_to_intercept
                future_ghost_row = ghost_row + ghost_direction[1] * steps_to_intercept
                
                future_distance = abs(path_pos[0] - future_ghost_row) + abs(path_pos[1] - future_ghost_col)
                
                if future_distance <= 2:  # Potential collision
                    threatening_positions += 1
        
        # Determine if path is threatened
        threat_ratio = threatening_positions / len(path) if path else 0
        is_threatening = (min_path_distance <= 3 and threat_ratio > 0.2) or threat_ratio > 0.4
        
        return {
            'is_threatening': is_threatening,
            'distance': min(min_path_distance, distance_to_pacman),
            'threat_ratio': threat_ratio,
            'threatening_positions': threatening_positions
        }

    def find_nearest_turn_from_path(self):
        """
        Tìm ngã rẽ gần nhất từ đường đi hiện tại
        Trả về hướng di chuyển để đến ngã rẽ đó
        """
        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        
        # Tìm tất cả các ngã rẽ trong phạm vi 6 ô
        potential_turns = []
        search_radius = 6
        
        for dr in range(-search_radius, search_radius + 1):
            for dc in range(-search_radius, search_radius + 1):
                test_row = pacman_row + dr
                test_col = pacman_col + dc
                
                if not self.game.is_valid_position(test_col, test_row):
                    continue
                    
                # Kiểm tra có phải là ngã rẽ không (có ít nhất 3 hướng đi)
                if self._is_junction(test_col, test_row):
                    distance = abs(dr) + abs(dc)
                    # Tính điểm ưu tiên: gần + tránh ma
                    safety_score = self._calculate_turn_safety_score(test_row, test_col)
                    potential_turns.append((test_row, test_col, distance, safety_score))
        
        if potential_turns:
            # Sắp xếp theo: safety_score cao + khoảng cách gần
            potential_turns.sort(key=lambda x: (x[3], -x[2]), reverse=True)
            best_turn = potential_turns[0]
            turn_row, turn_col = best_turn[0], best_turn[1]
            
            # Tính hướng đi đến ngã rẽ này
            if turn_col > pacman_col:
                return [1, 0]  # Đi phải
            elif turn_col < pacman_col:
                return [-1, 0]  # Đi trái
            elif turn_row > pacman_row:
                return [0, 1]  # Đi xuống
            elif turn_row < pacman_row:
                return [0, -1]  # Đi lên
                
        return None

    def _is_junction(self, col, row):
        """Kiểm tra vị trí có phải là ngã rẽ không (có ít nhất 3 hướng đi)"""
        if not self.game.is_valid_position(col, row):
            return False
            
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        valid_directions = 0
        
        for dx, dy in directions:
            next_col, next_row = col + dx, row + dy
            if self.game.is_valid_position(next_col, next_row):
                valid_directions += 1
                
        return valid_directions >= 3

    def _calculate_turn_safety_score(self, turn_row, turn_col):
        """Tính điểm an toàn của một ngã rẽ"""
        score = 10  # Điểm cơ bản
        
        # Trừ điểm nếu gần ma
        for ghost in self.game.ghosts:
            # BỎ QUA ghost đã bị ăn (chỉ còn eyes) - không nguy hiểm
            if self.game.can_pacman_pass_through_ghost(ghost):
                continue
                
            if ghost.get('scared', False):
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            distance_to_ghost = abs(turn_row - ghost_row) + abs(turn_col - ghost_col)
            
            if distance_to_ghost <= 3:
                score -= (4 - distance_to_ghost) * 2
                
        # Cộng điểm nếu có nhiều lối thoát
        exit_count = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dx, dy in directions:
            next_col, next_row = turn_col + dx, turn_row + dy
            if self.game.is_valid_position(next_col, next_row):
                exit_count += 1
                
        score += exit_count * 2
        
        return score

    def start_path_avoidance(self, avoidance_direction):
        """Bắt đầu chế độ né ma trên đường đi"""
        self.path_avoidance_mode = True
        self.path_avoidance_start_time = pygame.time.get_ticks()
        self.path_avoidance_direction = avoidance_direction
        
        # Lưu đường đi gốc
        if hasattr(self.game, 'auto_path'):
            self.original_goal_path = self.game.auto_path.copy()

    def should_return_to_original_path(self):
        """Kiểm tra có nên quay lại đường đi gốc không - IMPROVED with safety check"""
        if not self.path_avoidance_mode:
            return False
            
        current_time = pygame.time.get_ticks()
        avoidance_duration = current_time - self.path_avoidance_start_time
        
        # ENHANCED: Check ghost safety with larger radius before returning
        nearby_ghosts = self.check_ghosts_nearby(avoidance_radius=8)  # Increased from 5 to 8
        
        # Only return if:
        # 1. No ghosts within 8 cells AND
        # 2. At least 2 seconds have passed (increased for safety)
        if avoidance_duration >= 2000 and not nearby_ghosts:  # Increased from 1.5s to 2s
            return True
                
        # Emergency return only after 4 seconds (increased from 2.5s)
        if avoidance_duration >= 4000:  # 4 seconds
            # Even in emergency, still check for very close ghosts
            close_ghosts = self.check_ghosts_nearby(avoidance_radius=3)
            return len(close_ghosts) == 0  # Only return if no very close ghosts
            
        return False

    def _is_dead_end(self, col, row):
        """Kiểm tra xem vị trí có phải là dead end không - cải thiện để tránh kẹt, bỏ qua ghost eyes"""
        if not self.game.is_valid_position_ignore_eyes(col, row):
            return True
        
        valid_exits = 0
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # down, up, right, left
        
        # Đếm số lối ra hợp lệ (bỏ qua ghost eyes)
        for dx, dy in directions:
            next_col, next_row = col + dx, row + dy
            if self.game.is_valid_position_ignore_eyes(next_col, next_row):
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
                if self.game.is_valid_position_ignore_eyes(next_col, next_row):
                    exits.append((dx, dy))
            
            # Nếu 2 exits đối diện nhau (corridor thẳng), không coi là dead end
            if len(exits) == 2:
                dx1, dy1 = exits[0]
                dx2, dy2 = exits[1]
                if (dx1 + dx2 == 0 and dy1 + dy2 == 0):  # Đối diện nhau
                    return False  # Không phải dead end, chỉ là corridor
            
            return True  # Góc cụt
        
        return False  # Đủ rộng rãi

    def check_ghosts_nearby(self, avoidance_radius=4, debug=False):
        """
        ENHANCED Multi-layer ghost detection system với predictive capabilities
        Layer 1: Immediate threat (≤2) - Emergency
        Layer 2: Close threat (≤4) - Tactical  
        Layer 3: Potential threat (≤6) - Preventive
        """
        pacman_row, pacman_col = int(self.game.pacman_pos[1]), int(self.game.pacman_pos[0])
        
        nearby_ghosts = []
        threat_levels = {'immediate': [], 'close': [], 'potential': []}
        
        if debug:
            print(f"🔍 Enhanced checking ghosts from Pacman position: ({pacman_row}, {pacman_col})")
        
        for i, ghost in enumerate(self.game.ghosts):
            # BỎ QUA ghost đã bị ăn (chỉ còn eyes) - không nguy hiểm
            if self.game.can_pacman_pass_through_ghost(ghost):
                if debug:
                    print(f"  👻 Ghost {i}: JUST EYES - skipping (can pass through)")
                continue
                
            # Bỏ qua ghost đang scared - không cần tránh
            if ghost.get('scared', False):
                if debug:
                    print(f"  👻 Ghost {i}: SCARED - skipping")
                continue
                
            ghost_row, ghost_col = int(ghost['pos'][1]), int(ghost['pos'][0])
            current_distance = abs(pacman_row - ghost_row) + abs(pacman_col - ghost_col)
            
            if debug:
                print(f"  👻 Ghost {i}: pos=({ghost_row}, {ghost_col}), distance={current_distance}")
            
            # MULTI-LAYER THREAT ASSESSMENT
            threat_level = self._assess_threat_level(current_distance, avoidance_radius)
            
            if threat_level != 'safe':
                # Enhanced detection với predictive movement
                detection_result = self._enhanced_ghost_detection(
                    pacman_row, pacman_col, ghost_row, ghost_col, 
                    current_distance, ghost, threat_level, debug
                )
                
                if detection_result['should_avoid']:
                    ghost_data = ((ghost_row, ghost_col), current_distance)
                    nearby_ghosts.append(ghost_data)
                    threat_levels[threat_level].append(ghost_data)
                    
                    if debug:
                        print(f"    ✅ Added to {threat_level} threat level")
                else:
                    if debug:
                        print(f"    ❌ Ghost ignored - no clear threat")
        if debug:
            print(f"🎯 Enhanced result: {len(nearby_ghosts)} nearby ghosts")
            for level, ghosts in threat_levels.items():
                if ghosts:
                    print(f"  {level.upper()}: {len(ghosts)} ghosts")
        
        return nearby_ghosts

    def _assess_threat_level(self, distance, avoidance_radius):
        """Assess threat level based on distance"""
        if distance <= 2:
            return 'immediate'
        elif distance <= avoidance_radius:
            return 'close'
        elif distance <= avoidance_radius + 2:
            return 'potential'
        else:
            return 'safe'

    def _enhanced_ghost_detection(self, pacman_row, pacman_col, ghost_row, ghost_col, 
                                distance, ghost, threat_level, debug=False):
        """
        Enhanced ghost detection với multiple methods và predictive analysis
        """
        detection_methods = {
            'direct_los': False,
            'relaxed_los': False,
            'proximity': False,
            'corridor': False,
            'predictive': False
        }
        
        # Method 1: Direct line of sight
        detection_methods['direct_los'] = self._has_line_of_sight(
            (pacman_row, pacman_col), (ghost_row, ghost_col)
        )
        
        # Method 2: Relaxed line of sight
        detection_methods['relaxed_los'] = self._has_relaxed_line_of_sight(
            (pacman_row, pacman_col), (ghost_row, ghost_col)
        )
        
        # Method 3: Proximity check
        detection_methods['proximity'] = distance <= 2
        
        # Method 4: Same corridor
        same_row = ghost_row == pacman_row
        same_col = ghost_col == pacman_col
        detection_methods['corridor'] = same_row or same_col
        
        # Method 5: PREDICTIVE - Dự đoán collision trong tương lai
        detection_methods['predictive'] = self._predictive_collision_check(
            pacman_row, pacman_col, ghost_row, ghost_col, ghost, distance
        )
        
        # ENHANCED DECISION LOGIC theo threat level
        should_avoid = False
        
        if threat_level == 'immediate':
            # Immediate threat - any detection method triggers avoidance
            should_avoid = any(detection_methods.values())
        elif threat_level == 'close':
            # Close threat - need at least 2 methods or direct LOS
            method_count = sum(detection_methods.values())
            should_avoid = detection_methods['direct_los'] or method_count >= 2
        elif threat_level == 'potential':
            # Potential threat - need strong evidence
            should_avoid = (detection_methods['direct_los'] and 
                          (detection_methods['corridor'] or detection_methods['predictive']))
        
        if debug and any(detection_methods.values()):
            print(f"    Detection methods: {detection_methods}")
            print(f"    Threat level: {threat_level}")
            print(f"    Decision: {'AVOID' if should_avoid else 'IGNORE'}")
        
        return {
            'should_avoid': should_avoid,
            'methods': detection_methods,
            'threat_level': threat_level
        }

    def _predictive_collision_check(self, pacman_row, pacman_col, ghost_row, ghost_col, ghost, distance):
        """
        IMPROVED Predictive collision detection với enhanced ghost movement patterns
        """
        # Enhanced distance threshold for better prediction
        if distance > 8:  # Increased from 6 to 8 for more comprehensive prediction
            return False
            
        ghost_direction = ghost.get('direction', [0, 0])
        pacman_direction = self.game.pacman_direction
        
        # Predict positions for next 4-6 steps (increased range)
        prediction_steps = min(6, max(3, distance + 2))  # Minimum 3 steps, up to 6
        
        for steps in range(1, prediction_steps + 1):
            # Predicted future positions with movement speed consideration
            future_ghost_col = ghost_col + ghost_direction[0] * steps
            future_ghost_row = ghost_row + ghost_direction[1] * steps
            future_pacman_col = pacman_col + pacman_direction[0] * steps  
            future_pacman_row = pacman_row + pacman_direction[1] * steps
            
            # Check if both positions are valid (account for walls)
            if (not self.game.is_valid_position(future_ghost_col, future_ghost_row) or
                not self.game.is_valid_position(future_pacman_col, future_pacman_row)):
                continue
            
            # Calculate future distance (Manhattan distance)
            future_distance = abs(future_pacman_row - future_ghost_row) + abs(future_pacman_col - future_ghost_col)
            
            # Enhanced collision risk detection - stricter threshold
            if future_distance <= 1.5:  # Increased sensitivity from 1 to 1.5
                # Additional safety checks:
                if self._are_moving_towards_each_other(
                    (pacman_row, pacman_col), (ghost_row, ghost_col),
                    pacman_direction, ghost_direction
                ):
                    return True
                    
                # Also check if they'll be adjacent in next step
                if steps == 1 and future_distance <= 1:
                    return True
        
        # Additional check: if ghost is directly in Pacman's path within 3 steps
        for step in range(1, 4):
            check_col = pacman_col + pacman_direction[0] * step
            check_row = pacman_row + pacman_direction[1] * step
            
            if (abs(check_row - ghost_row) <= 1 and abs(check_col - ghost_col) <= 1):
                return True
        
        return False

    def _is_ghost_gaining_ground(self, pacman_row, pacman_col, ghost_row, ghost_col, ghost, distance):
        """Check if ghost is getting closer over time"""
        ghost_id = ghost.get('id', 0)
        current_time = pygame.time.get_ticks()
        
        # Initialize ghost tracking if not exists
        if not hasattr(self, 'ghost_distance_history'):
            self.ghost_distance_history = {}
        
        if ghost_id not in self.ghost_distance_history:
            self.ghost_distance_history[ghost_id] = []
        
        # Record current distance
        self.ghost_distance_history[ghost_id].append({
            'distance': distance,
            'time': current_time,
            'position': (ghost_row, ghost_col)
        })
        
        # Keep only recent history (last 1 second = ~60 frames)
        recent_history = [
            entry for entry in self.ghost_distance_history[ghost_id]
            if current_time - entry['time'] <= 1000  # 1 second
        ]
        self.ghost_distance_history[ghost_id] = recent_history
        
        # Analyze if ghost is gaining ground
        if len(recent_history) >= 3:
            distances = [entry['distance'] for entry in recent_history[-3:]]
            
            # If distance is consistently decreasing
            if distances[0] > distances[1] > distances[2]:
                return True
            
            # If average distance is decreasing significantly
            if len(recent_history) >= 5:
                old_avg = sum(entry['distance'] for entry in recent_history[:3]) / 3
                new_avg = sum(entry['distance'] for entry in recent_history[-3:]) / 3
                if old_avg - new_avg > 1.0:  # Gained more than 1 block closer
                    return True
        
        return False

    def _are_moving_towards_each_other(self, pacman_pos, ghost_pos, pacman_dir, ghost_dir):
        """Check if Pacman and ghost are moving towards each other"""
        # Vector from pacman to ghost
        to_ghost = [ghost_pos[1] - pacman_pos[1], ghost_pos[0] - pacman_pos[0]]
        
        # Dot product to check if pacman moving towards ghost
        pacman_towards = (to_ghost[0] * pacman_dir[0] + to_ghost[1] * pacman_dir[1]) > 0
        
        # Vector from ghost to pacman  
        to_pacman = [-to_ghost[0], -to_ghost[1]]
        
        # Dot product to check if ghost moving towards pacman
        ghost_towards = (to_pacman[0] * ghost_dir[0] + to_pacman[1] * ghost_dir[1]) > 0
        
        return pacman_towards and ghost_towards

    def _quick_line_of_sight_check(self, pos1, pos2):
        """
        Kiểm tra line of sight nhanh - tối ưu cho dự đoán tương lai
        """
        x1, y1 = pos1[1], pos1[0]  # col, row
        x2, y2 = pos2[1], pos2[0]  # col, row
        
        # Khoảng cách ngắn - kiểm tra trực tiếp
        if abs(x2 - x1) <= 1 and abs(y2 - y1) <= 1:
            return True
        
        # Kiểm tra đường thẳng đơn giản (horizontal/vertical)
        if x1 == x2:  # Vertical line
            start_y, end_y = min(y1, y2), max(y1, y2)
            for y in range(start_y + 1, end_y):
                if not self.game.is_valid_position(x1, y):
                    return False
            return True
        elif y1 == y2:  # Horizontal line  
            start_x, end_x = min(x1, x2), max(x1, x2)
            for x in range(start_x + 1, end_x):
                if not self.game.is_valid_position(x, y1):
                    return False
            return True
        
        # Đường chéo - sử dụng thuật toán Bresenham đơn giản
        return self._has_line_of_sight(pos1, pos2)

    def _has_relaxed_line_of_sight(self, pos1, pos2, max_walls=2):
        """
        Relaxed line of sight - allows small number of wall obstructions
        This is more realistic for ghost detection in maze games
        """
        row1, col1 = pos1
        row2, col2 = pos2
        
        # Same position
        if pos1 == pos2:
            return True
        
        # Very close - always true
        distance = abs(row2 - row1) + abs(col2 - col1)
        if distance <= 2:
            return True
        
        # Count walls in between using Bresenham's algorithm
        dx = abs(col2 - col1)
        dy = abs(row2 - row1)
        
        step_x = 1 if col1 < col2 else -1
        step_y = 1 if row1 < row2 else -1
        
        err = dx - dy
        current_col, current_row = col1, row1
        wall_count = 0
        
        while not (current_col == col2 and current_row == row2):
            # Skip start position
            if not (current_col == col1 and current_row == row1):
                if self.game.is_wall(current_col, current_row):
                    wall_count += 1
                    if wall_count > max_walls:
                        return False
            
            # Move to next position
            e2 = 2 * err
            
            if e2 > -dy:
                err -= dy
                current_col += step_x
                
            if e2 < dx:
                err += dx
                current_row += step_y
        
        return True  # Few enough walls to still detect ghost

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
            if self.game.is_wall(current_col, current_row):
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

    def find_fallback_target(self, pacman_pos, ghost_positions):
        """Find a safe fallback target when primary targets are unsafe - CẢI THIỆN"""
        try:
            # Sử dụng Dijkstra với ghost avoidance để tìm target an toàn
            if hasattr(self.game, 'dijkstra'):
                # Tìm tất cả các vị trí trong bán kính 15 ô
                all_positions = []
                for radius in range(8, 16):  # Bắt đầu từ 8 ô để đảm bảo an toàn
                    for dr in range(-radius, radius + 1):
                        for dc in range(-radius, radius + 1):
                            if abs(dr) + abs(dc) == radius:  # Chỉ check vị trí ở exact radius
                                new_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                                
                                # Check if position is valid
                                if (new_pos[0] >= 0 and new_pos[0] < self.game.maze_gen.height and
                                    new_pos[1] >= 0 and new_pos[1] < self.game.maze_gen.width and
                                    not self.game.maze_gen.is_wall(new_pos)):
                                    
                                    # Tính safety score dựa trên khoảng cách đến tất cả ghosts
                                    min_ghost_dist = min([abs(new_pos[0] - gr) + abs(new_pos[1] - gc) 
                                                        for gr, gc in ghost_positions]) if ghost_positions else 10
                                    
                                    # Chỉ coi là an toàn nếu cách ghost ít nhất 4 ô
                                    if min_ghost_dist >= 4:
                                        # Kiểm tra xem có phải dead end không
                                        is_dead_end = self._is_dead_end(new_pos[1], new_pos[0])  # col, row for _is_dead_end
                                        
                                        if not is_dead_end:
                                            # Thử tìm đường đi bằng ghost avoidance algorithm
                                            path, cost = self.game.dijkstra.shortest_path_with_ghost_avoidance(
                                                pacman_pos, new_pos, ghost_positions, avoidance_radius=4
                                            )
                                            
                                            if path and len(path) > 1:
                                                # Tính final score: khoảng cách an toàn + khả năng di chuyển
                                                safety_score = min_ghost_dist + (10 / len(path))  # Ưu tiên đường ngắn
                                                all_positions.append((new_pos, safety_score, path, cost))
                    
                    # Nếu tìm được đủ vị trí an toàn, stop
                    if len(all_positions) >= 5:
                        break
                
                # Chọn vị trí tốt nhất
                if all_positions:
                    # Sắp xếp theo safety score (cao nhất trước)
                    all_positions.sort(key=lambda x: x[1], reverse=True)
                    best_pos, best_score, best_path, best_cost = all_positions[0]
                    
                    self.game.auto_target = best_pos
                    self.game.auto_path = best_path
                    return
            
            # Fallback method nếu Dijkstra ghost avoidance không có
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # right, left, down, up
            search_radius = 12  # Tăng search radius
            
            # Find safe positions in expanding radius
            for radius in range(6, search_radius + 1):  # Bắt đầu từ 6 ô
                safe_positions = []
                
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        if abs(dr) + abs(dc) != radius:  # Chỉ check positions ở exact radius
                            continue
                        
                        new_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                        
                        # Check if position is valid
                        if (new_pos[0] >= 0 and new_pos[0] < self.game.maze_gen.height and
                            new_pos[1] >= 0 and new_pos[1] < self.game.maze_gen.width and
                            not self.game.is_wall(new_pos[1], new_pos[0])):  # col, row for is_wall
                            
                            # Check safety from ghosts
                            min_ghost_dist = min([abs(new_pos[0] - gr) + abs(new_pos[1] - gc) 
                                                for gr, gc in ghost_positions]) if ghost_positions else 10
                            
                            if min_ghost_dist >= 5:  # Tăng khoảng cách an toàn từ 3 lên 5
                                # Kiểm tra không phải dead end
                                if not self._is_dead_end(new_pos[1], new_pos[0]):
                                    # Thử tìm đường đi bằng normal pathfinding
                                    if hasattr(self.game, 'dijkstra'):
                                        path, distance = self.game.dijkstra.shortest_path(pacman_pos, new_pos)
                                        if path:
                                            safe_positions.append((new_pos, min_ghost_dist, distance))
                
                # Choose best safe position from this radius
                if safe_positions:
                    # Sort by safety first, then by path distance
                    safe_positions.sort(key=lambda x: (-x[1], x[2]))
                    best_pos = safe_positions[0][0]
                    
                    self.game.auto_target = best_pos
                    self.game.calculate_auto_path()
                    return
            
            # Emergency: try to move away from nearest ghost
            if ghost_positions:
                nearest_ghost = min(ghost_positions, 
                                  key=lambda g: abs(pacman_pos[0] - g[0]) + abs(pacman_pos[1] - g[1]))
                
                # Move in opposite direction from nearest ghost
                escape_directions = []
                if nearest_ghost[0] > pacman_pos[0]:  # Ghost below, move up
                    escape_directions.append((-3, 0))  # Move 3 steps up
                elif nearest_ghost[0] < pacman_pos[0]:  # Ghost above, move down
                    escape_directions.append((3, 0))   # Move 3 steps down
                
                if nearest_ghost[1] > pacman_pos[1]:  # Ghost right, move left
                    escape_directions.append((0, -3))  # Move 3 steps left
                elif nearest_ghost[1] < pacman_pos[1]:  # Ghost left, move right
                    escape_directions.append((0, 3))   # Move 3 steps right
                
                for dr, dc in escape_directions:
                    escape_pos = (pacman_pos[0] + dr, pacman_pos[1] + dc)
                    if (escape_pos[0] >= 0 and escape_pos[0] < self.game.maze_gen.height and
                        escape_pos[1] >= 0 and escape_pos[1] < self.game.maze_gen.width and
                        not self.game.is_wall(escape_pos[1], escape_pos[0])):
                        
                        self.game.auto_target = escape_pos
                        self.game.calculate_auto_path()
                        return
            
            self.game.auto_target = None
            self.game.auto_path = []
            
        except Exception as e:
            print(f"Error in find_fallback_target: {e}")
            self.game.auto_target = None
            self.game.auto_path = []
            
            # Last resort: stay in place but keep looking
            self.game.auto_target = pacman_pos
            self.game.auto_path = [pacman_pos]

    def evaluate_path_safety(self, path, ghost_positions, avoidance_radius):
        """Evaluate if a path is safe from ghosts"""
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
        
        # Path is safe if less than threshold fraction of positions are dangerous
        safety_threshold = getattr(config, 'SAFETY_DANGER_THRESHOLD', 0.2)
        return (danger_count / total_positions) < safety_threshold

    def calculate_path_safety_penalty(self, path, ghost_positions, avoidance_radius):
        """Calculate safety penalty for a path (higher = more dangerous)"""
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

    def validate_path_safety(self, path, ghost_positions):
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

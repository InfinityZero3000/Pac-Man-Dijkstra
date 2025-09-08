#!/usr/bin/env python3
"""
Game Performance Test
Test Enhanced Pacman AI in real game scenario
"""

import pygame
import sys
import time
import json
from datetime import datetime
import random

def game_performance_test():
    """Test AI performance in game-like scenario"""
    print(" GAME PERFORMANCE TEST")
    print("=" * 40)
    
    # Import modules
    try:
        import pacman_ai
        import config
        # Use config constants where available
        WINDOW_WIDTH = getattr(config, 'WINDOW_WIDTH', 800)
        WINDOW_HEIGHT = getattr(config, 'WINDOW_HEIGHT', 600)
        CELL_SIZE = getattr(config, 'CELL_SIZE', 20)
    except ImportError:
        # Fallback constants
        WINDOW_WIDTH = 800
        WINDOW_HEIGHT = 600
        CELL_SIZE = 20
    
    # Define color constants locally
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    YELLOW = (255, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    ORANGE = (255, 165, 0)
    PINK = (255, 192, 203)
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AI Performance Test")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    
    # Game setup
    class TestGame:
        def __init__(self):
            self.pacman_pos = [WINDOW_WIDTH//2, WINDOW_HEIGHT//2]
            self.ghosts = []
            self.current_goal: tuple[int, int] = (30, 25)
            self.maze = [[0 for _ in range(40)] for _ in range(30)]
            self.auto_path = []
            
        def is_valid_position(self, x, y):
            return 0 <= x < 40 and 0 <= y < 30
        
        def spawn_random_ghost(self):
            """Spawn a ghost at random position"""
            ghost = {
                'pos': [
                    random.randint(50, WINDOW_WIDTH-50),
                    random.randint(50, WINDOW_HEIGHT-50)
                ],
                'direction': random.choice([[1,0], [-1,0], [0,1], [0,-1]]),
                'scared': False,
                'color': (random.randint(100, 255), 0, random.randint(100, 255)),
                'speed': random.uniform(0.5, 2.0)
            }
            return ghost
        
        def update_ghosts(self):
            """Update ghost positions"""
            for ghost in self.ghosts:
                # Random direction change
                if random.random() < 0.05:  # 5% chance
                    ghost['direction'] = random.choice([[1,0], [-1,0], [0,1], [0,-1]])
                
                # Move ghost
                speed = ghost.get('speed', 1.0)
                new_x = ghost['pos'][0] + ghost['direction'][0] * CELL_SIZE * speed
                new_y = ghost['pos'][1] + ghost['direction'][1] * CELL_SIZE * speed
                
                # Bounce off walls
                if new_x <= 0 or new_x >= WINDOW_WIDTH:
                    ghost['direction'][0] *= -1
                else:
                    ghost['pos'][0] = new_x
                    
                if new_y <= 0 or new_y >= WINDOW_HEIGHT:
                    ghost['direction'][1] *= -1
                else:
                    ghost['pos'][1] = new_y
    
    game = TestGame()
    ai = pacman_ai.PacmanAI(game)
    
    # Test metrics
    metrics = {
        'start_time': time.time(),
        'ghost_encounters': 0,
        'avoidance_attempts': 0,
        'successful_avoidances': 0,
        'emergency_responses': 0,
        'path_recalculations': 0,
        'total_operations': 0,
        'response_times': [],
        'ghost_distances': [],
        'ai_decisions': []
    }
    
    test_duration = 30  # 30 seconds test
    
    # Spawn initial ghosts
    for _ in range(3):
        game.ghosts.append(game.spawn_random_ghost())
    
    print(f"Running {test_duration}s performance test...")
    
    # Main test loop
    running = True
    while running and (time.time() - metrics['start_time'] < test_duration):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Update game state
        game.update_ghosts()
        
        # Spawn new ghost occasionally
        if random.random() < 0.02 and len(game.ghosts) < 6:  # 2% chance, max 6 ghosts
            game.ghosts.append(game.spawn_random_ghost())
        
        # AI Performance Testing
        operation_start = time.time()
        
        try:
            # 1. Ghost detection test
            nearby_ghosts = ai.check_ghosts_nearby()
            metrics['total_operations'] += 1
            
            if nearby_ghosts:
                metrics['ghost_encounters'] += 1
                
                # Calculate closest ghost distance
                pacman_x, pacman_y = game.pacman_pos
                min_distance = float('inf')
                
                for ghost in game.ghosts:
                    distance = ((ghost['pos'][0] - pacman_x)**2 + (ghost['pos'][1] - pacman_y)**2)**0.5
                    min_distance = min(min_distance, distance)
                
                metrics['ghost_distances'].append(min_distance)
                
                # 2. Emergency avoidance test
                try:
                    emergency_move = ai.emergency_ghost_avoidance(nearby_ghosts)
                    metrics['avoidance_attempts'] += 1
                    
                    if (emergency_move and 
                        isinstance(emergency_move, (list, tuple)) and 
                        len(emergency_move) == 2 and
                        emergency_move != (0, 0)):
                        
                        metrics['successful_avoidances'] += 1
                        metrics['emergency_responses'] += 1
                        
                        # Move Pacman based on AI decision
                        move_x, move_y = emergency_move[0], emergency_move[1]
                        new_x = game.pacman_pos[0] + move_x * CELL_SIZE
                        new_y = game.pacman_pos[1] + move_y * CELL_SIZE
                        
                        # Keep Pacman in bounds
                        if 0 <= new_x < WINDOW_WIDTH and 0 <= new_y < WINDOW_HEIGHT:
                            game.pacman_pos[0] = new_x
                            game.pacman_pos[1] = new_y
                        
                        metrics['ai_decisions'].append({
                            'type': 'emergency_avoidance',
                            'move': emergency_move,
                            'ghost_distance': min_distance
                        })
                
                except Exception as e:
                    print(f"Emergency avoidance error: {e}")
            
            # 3. Path planning test
            try:
                threat_on_path, threat_pos, distance = ai.check_ghost_on_path_to_goal()
                if threat_on_path:
                    metrics['path_recalculations'] += 1
                    
                    # Move goal to new position
                    game.current_goal = (
                        random.randint(5, 35),
                        random.randint(5, 25)
                    )
                    
                    metrics['ai_decisions'].append({
                        'type': 'path_recalculation',
                        'threat_distance': distance
                    })
                        
            except Exception as e:
                print(f"Path checking error: {e}")
        
        except Exception as e:
            print(f"AI operation error: {e}")
        
        # Record response time
        operation_time = time.time() - operation_start
        metrics['response_times'].append(operation_time)
        
        # Rendering
        screen.fill(BLACK)
        
        # Draw Pacman
        pygame.draw.circle(screen, YELLOW, 
                         (int(game.pacman_pos[0]), int(game.pacman_pos[1])), 12)
        
        # Draw ghosts
        for i, ghost in enumerate(game.ghosts):
            pygame.draw.circle(screen, ghost['color'],
                             (int(ghost['pos'][0]), int(ghost['pos'][1])), 10)
        
        # Draw goal
        goal_x = game.current_goal[0] * CELL_SIZE
        goal_y = game.current_goal[1] * CELL_SIZE
        pygame.draw.circle(screen, (0, 255, 0), (goal_x, goal_y), 8)
        
        # Display metrics
        elapsed = time.time() - metrics['start_time']
        progress = (elapsed / test_duration) * 100
        
        texts = [
            f"Progress: {progress:.1f}%",
            f"Ghosts: {len(game.ghosts)}",
            f"Encounters: {metrics['ghost_encounters']}",
            f"Avoidances: {metrics['successful_avoidances']}/{metrics['avoidance_attempts']}",
            f"Emergency: {metrics['emergency_responses']}",
            f"Path Recalc: {metrics['path_recalculations']}",
            f"Operations: {metrics['total_operations']}"
        ]
        
        for i, text in enumerate(texts):
            surface = font.render(text, True, WHITE)
            screen.blit(surface, (10, 10 + i * 25))
        
        pygame.display.flip()
        clock.tick(60)
    
    # Calculate final metrics
    metrics['end_time'] = time.time()
    metrics['total_duration'] = metrics['end_time'] - metrics['start_time']
    
    # Calculate success rates
    if metrics['avoidance_attempts'] > 0:
        avoidance_rate = (metrics['successful_avoidances'] / metrics['avoidance_attempts']) * 100
    else:
        avoidance_rate = 0
    
    if metrics['response_times']:
        avg_response_time = sum(metrics['response_times']) / len(metrics['response_times'])
        max_response_time = max(metrics['response_times'])
    else:
        avg_response_time = 0
        max_response_time = 0
    
    if metrics['ghost_distances']:
        avg_ghost_distance = sum(metrics['ghost_distances']) / len(metrics['ghost_distances'])
        min_ghost_distance = min(metrics['ghost_distances'])
    else:
        avg_ghost_distance = 0
        min_ghost_distance = 0
    
    ops_per_second = metrics['total_operations'] / metrics['total_duration']
    
    # Display results
    print(f"\n GAME PERFORMANCE RESULTS:")
    print(f"     Duration: {metrics['total_duration']:.1f}s")
    print(f"    Ghost Encounters: {metrics['ghost_encounters']}")
    print(f"     Avoidance Success: {metrics['successful_avoidances']}/{metrics['avoidance_attempts']} ({avoidance_rate:.1f}%)")
    print(f"    Emergency Responses: {metrics['emergency_responses']}")
    print(f"    Path Recalculations: {metrics['path_recalculations']}")
    print(f"    Operations/sec: {ops_per_second:.1f}")
    print(f"    Avg Ghost Distance: {avg_ghost_distance:.1f}")
    print(f"    Min Ghost Distance: {min_ghost_distance:.1f}")
    print(f"     Avg Response Time: {avg_response_time:.4f}s")
    print(f"     Max Response Time: {max_response_time:.4f}s")
    
    # Performance grade
    performance_score = (
        (avoidance_rate * 0.4) +  # 40% weight on avoidance success
        (min(ops_per_second / 100 * 100, 100) * 0.3) +  # 30% weight on speed
        (max(0, 100 - max_response_time * 1000) * 0.2) +  # 20% weight on response time
        (min(metrics['emergency_responses'] / max(1, metrics['ghost_encounters']) * 100, 100) * 0.1)  # 10% weight on emergency responses
    )
    
    if performance_score >= 90:
        grade = "A+ (Outstanding)"
    elif performance_score >= 80:
        grade = "A (Excellent)"
    elif performance_score >= 70:
        grade = "B (Good)"
    elif performance_score >= 60:
        grade = "C (Acceptable)"
    else:
        grade = "F (Needs Improvement)"
    
    print(f"    Performance Score: {performance_score:.1f}%")
    print(f"    Grade: {grade}")
    
    # Save detailed results
    final_results = {
        'test_type': 'game_performance',
        'timestamp': datetime.now().isoformat(),
        'duration': metrics['total_duration'],
        'metrics': metrics,
        'calculated_metrics': {
            'avoidance_success_rate': avoidance_rate,
            'operations_per_second': ops_per_second,
            'average_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'average_ghost_distance': avg_ghost_distance,
            'min_ghost_distance': min_ghost_distance,
            'performance_score': performance_score,
            'grade': grade
        }
    }
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"game_performance_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"    Results saved: {filename}")
    
    pygame.quit()
    return final_results

def main():
    """Run game performance test"""
    try:
        print(" STARTING GAME PERFORMANCE TEST")
        print("=" * 50)
        
        results = game_performance_test()
        
        print("\n GAME PERFORMANCE TEST COMPLETED!")
        print(" Your Enhanced Pacman AI has been tested in a real game scenario!")
        
        return results
        
    except Exception as e:
        print(f" Game performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()

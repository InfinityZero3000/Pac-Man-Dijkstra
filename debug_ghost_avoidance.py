#!/usr/bin/env python3
"""
Debug script để test và cải thiện thuật toán né ma
"""

import pygame
import time
from pacman_game import PacmanGame
from pacman_ai import PacmanAI
import config

def test_ghost_avoidance_scenarios():
    """Test various ghost avoidance scenarios"""
    print("🔍 DEBUGGING GHOST AVOIDANCE ALGORITHM")
    print("=" * 50)
    
    # Initialize pygame but don't show window
    pygame.init()
    
    # Create test game
    game = PacmanGame()
    game.create_new_game()
    
    # Create AI
    ai = PacmanAI(game)
    
    # Check if AI has proper initialization
    print(f"✅ AI Initialization Check:")
    print(f"   - has escape_direction_history: {hasattr(ai, 'escape_direction_history')}")
    print(f"   - has last_escape_time: {hasattr(ai, 'last_escape_time')}")
    print(f"   - has escape_timeout_count: {hasattr(ai, 'escape_timeout_count')}")
    print(f"   - has stuck_prevention_timer: {hasattr(ai, 'stuck_prevention_timer')}")
    print(f"   - has force_movement_counter: {hasattr(ai, 'force_movement_counter')}")
    
    # Simulate a loop scenario
    print(f"\n🔄 SIMULATING ESCAPE LOOP SCENARIO:")
    
    # Initialize AI attributes if needed
    current_time = time.time() * 1000
    
    # Add some repeated directions to simulate loop
    if not hasattr(ai, 'escape_direction_history'):
        ai.escape_direction_history = []
    if not hasattr(ai, 'last_escape_time'):
        ai.last_escape_time = current_time - 3000  # 3 seconds ago
    if not hasattr(ai, 'escape_timeout_count'):
        ai.escape_timeout_count = 0
    
    # Simulate repeated escape directions
    repeated_directions = [[1, 0], [-1, 0], [1, 0], [-1, 0], [1, 0], [-1, 0]]
    ai.escape_direction_history.extend(repeated_directions)
    
    print(f"   - Escape history length: {len(ai.escape_direction_history)}")
    print(f"   - Recent directions: {ai.escape_direction_history[-6:]}")
    print(f"   - Unique directions in recent 6: {len(set(map(tuple, ai.escape_direction_history[-6:])))}")
    print(f"   - Time since last escape: {current_time - ai.last_escape_time}ms")
    print(f"   - Escape timeout count: {ai.escape_timeout_count}")
    
    # Test forced movement
    print(f"\n⚡ TESTING FORCED MOVEMENT:")
    pacman_row, pacman_col = 10, 10  # Test position
    
    # Set conditions for forced movement
    ai.escape_timeout_count = 3  # High timeout count
    ai.last_escape_time = current_time - 3000  # 3 seconds ago
    
    # Check if forced movement would trigger
    time_since_last_escape = current_time - ai.last_escape_time
    should_force = (time_since_last_escape > 2000 and ai.escape_timeout_count > 2)
    
    print(f"   - Should force movement: {should_force}")
    print(f"   - Time condition: {time_since_last_escape} > 2000 = {time_since_last_escape > 2000}")
    print(f"   - Timeout condition: {ai.escape_timeout_count} > 2 = {ai.escape_timeout_count > 2}")
    
    if should_force:
        # Test the forced movement function
        try:
            result = ai._force_emergency_movement(pacman_row, pacman_col, current_time)
            print(f"   - Forced movement result: {result}")
        except Exception as e:
            print(f"   - Forced movement error: {e}")
    
    # Test loop detection logic
    print(f"\n🔍 TESTING LOOP DETECTION:")
    
    # Test with different escape histories
    test_histories = [
        [[1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0]],  # All same direction
        [[1, 0], [-1, 0], [1, 0], [-1, 0], [1, 0], [-1, 0]],  # Alternating (loop)
        [[1, 0], [0, 1], [-1, 0], [0, -1], [1, 0], [0, 1]],  # Mixed directions
    ]
    
    for i, test_history in enumerate(test_histories):
        unique_count = len(set(map(tuple, test_history)))
        is_loop = unique_count <= 2
        print(f"   Test {i+1}: {test_history}")
        print(f"           Unique directions: {unique_count}, Is loop: {is_loop}")
    
    print(f"\n📊 CURRENT CONFIG VALUES:")
    print(f"   - PACMAN_SPEED: {getattr(config, 'PACMAN_SPEED', 'Not set')}")
    print(f"   - GHOST_SPEED: {getattr(config, 'GHOST_SPEED', 'Not set')}")
    print(f"   - ENABLE_DYNAMIC_SPEED: {getattr(config, 'ENABLE_DYNAMIC_SPEED', 'Not set')}")
    print(f"   - COLLISION_CHECK_DISTANCE: {getattr(config, 'COLLISION_CHECK_DISTANCE', 'Not set')}")
    
    pygame.quit()
    print(f"\n✅ DEBUG COMPLETE")

def test_improved_logic():
    """Test with improved anti-loop logic"""
    print(f"\n🚀 TESTING IMPROVED ANTI-LOOP LOGIC")
    print("=" * 50)
    
    # Initialize pygame
    pygame.init()
    
    # Test conditions that would trigger improvements
    print("Testing various escape scenarios:")
    
    scenarios = [
        {
            'name': 'Normal movement',
            'history': [[1, 0], [0, 1], [1, 0], [0, -1]],
            'time_since_escape': 500,
            'timeout_count': 0
        },
        {
            'name': 'Simple loop detected',
            'history': [[1, 0], [-1, 0], [1, 0], [-1, 0], [1, 0], [-1, 0]],
            'time_since_escape': 1000,
            'timeout_count': 1
        },
        {
            'name': 'Stuck situation',
            'history': [[0, 1], [0, 1], [0, 1], [0, 1], [0, 1], [0, 1]],
            'time_since_escape': 3000,
            'timeout_count': 3
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        history = scenario['history']
        unique_directions = len(set(map(tuple, history)))
        
        # Check loop condition
        is_loop = len(history) > 5 and unique_directions <= 2
        
        # Check forced movement condition
        should_force = (scenario['time_since_escape'] > 2000 and 
                       scenario['timeout_count'] > 2)
        
        print(f"   History: {history}")
        print(f"   Unique directions: {unique_directions}")
        print(f"   Is loop: {is_loop}")
        print(f"   Should force movement: {should_force}")
        
        # Recommend action
        if should_force:
            print(f"   ⚡ RECOMMENDED: Force emergency movement")
        elif is_loop:
            print(f"   🔄 RECOMMENDED: Clear history, extended cooldown")
        else:
            print(f"   ✅ RECOMMENDED: Normal operation")
    
    pygame.quit()

if __name__ == "__main__":
    test_ghost_avoidance_scenarios()
    test_improved_logic()

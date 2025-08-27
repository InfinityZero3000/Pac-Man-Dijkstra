#!/usr/bin/env python3
"""
Robust path validation utility to ensure no wall crossing
"""

class PathValidator:
    def __init__(self, maze_generator):
        self.maze_gen = maze_generator
        self.maze = maze_generator.maze
        
    def is_position_valid(self, pos):
        """Check if a position is valid (within bounds and not a wall)"""
        # Use maze_generator's is_wall method for consistency
        return not self.maze_gen.is_wall(pos)
    
    def validate_path_strict(self, path):
        """Strictly validate that path contains no walls and only adjacent moves"""
        if not path or len(path) < 1:
            return False
            
        # Check each position
        for pos in path:
            if not self.is_position_valid(pos):
                print(f"Invalid position in path: {pos} (wall or out of bounds)")
                return False
        
        # Check adjacency for consecutive positions
        for i in range(len(path) - 1):
            pos1, pos2 = path[i], path[i + 1]
            if not self.are_adjacent(pos1, pos2):
                print(f"Non-adjacent positions in path: {pos1} -> {pos2}")
                return False
                
        return True
    
    def are_adjacent(self, pos1, pos2):
        """Check if two positions are adjacent (4-connected)"""
        y1, x1 = pos1
        y2, x2 = pos2
        
        dy = abs(y1 - y2)
        dx = abs(x1 - x2)
        
        # Must be exactly 1 step away in 4-directions
        return (dy == 1 and dx == 0) or (dy == 0 and dx == 1)
    
    def clean_path(self, path):
        """Remove any invalid positions from path"""
        if not path:
            return []
            
        clean = []
        for pos in path:
            if self.is_position_valid(pos):
                clean.append(pos)
            else:
                print(f"Removing invalid position: {pos}")
                
        return clean
    
    def get_valid_neighbors(self, pos):
        """Get all valid 4-connected neighbors of a position"""
        # Use maze_generator's get_neighbors method for consistency
        return self.maze_gen.get_neighbors(pos)

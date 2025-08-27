# Maze Game - Pacman Style with Dijkstra Algorithm

This is a maze game built in Python using Pygame, featuring a Pacman-like character that navigates through a randomly generated maze. The game utilizes Dijkstra's algorithm to find the shortest path to the goal.

## Features

- Randomly generated maze using DFS algorithm with connectivity guarantee
- Pacman-like character movement
- Dijkstra's algorithm for shortest path finding with path validation
- Pygame-based graphics
- Interactive controls
- Automatic maze regeneration if no path exists

## Requirements

Install the required packages using:

```bash
pip install -r requirements.txt
```

## How to Run

Run the game using:

```bash
python quick_test.py
```

Or directly:

```bash
python maze_game.py
```

## Controls

- **Arrow Keys**: Move the character
- **Space**: Find and display the shortest path to the goal
- **R**: Reset the game with a new maze
- **Escape**: Quit the game

## Files

- `maze_generator.py`: Contains the MazeGenerator class for creating random mazes
- `dijkstra_algorithm.py`: Implements Dijkstra's algorithm with path validation
- `maze_game.py`: Main game class using Pygame
- `quick_test.py`: Entry point to run the game
- `test_dijkstra.py`: Basic test for maze generation and pathfinding
- `test_maze_comprehensive.py`: Comprehensive test suite for larger mazes and complexity analysis
- `requirements.txt`: List of required Python packages

## Testing

Run the comprehensive test suite to validate maze generation and pathfinding:

```bash
python test_maze_comprehensive.py
```

This will test:
- Different maze sizes (21x21 to 51x51)
- Path validation and alternative paths
- Maze complexity analysis
- Pathfinding performance benchmarks

## Maze Characteristics

- **Default Size**: 41x41 (larger than original 21x21)
- **Size Range**: 21x21 to 51x51 (configurable)
- **Path Density**: ~50% open spaces for balanced gameplay
- **Complexity**: Includes dead ends and branching points for interesting navigation
- **Connectivity**: Guaranteed path from start to goal
- **Performance**: Fast pathfinding even on large mazes

## Technical Details

- **Maze Generation**: Uses randomized DFS to create perfect mazes
- **Pathfinding**: Dijkstra's algorithm ensures shortest path
- **Validation**: Paths are validated to prevent going through walls
- **Connectivity**: Mazes are guaranteed to have a path from start to goal

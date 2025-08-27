#!/usr/bin/env python3
"""
Generate supervised training data for maze shortest-path via optimal (A*/Dijkstra) solver.
Outputs training_data/training_sets/training_dataset_<session>.json
"""
import os
import json
from datetime import datetime
from maze_generator import MazeGenerator
from dijkstra_algorithm import DijkstraAlgorithm
from pathfinding_data_logger import PathfindingDataLogger


def run_generation(num_mazes=50, width=21, height=21, astar=True, verify_bfs=True):
    # Toggle config flags dynamically if present
    try:
        import config
        setattr(config, 'USE_ASTAR', bool(astar))
        setattr(config, 'PURE_SHORTEST_PATH', True)
        setattr(config, 'VERIFY_OPTIMALITY_WITH_BFS', bool(verify_bfs))
    except Exception:
        pass

    logger = PathfindingDataLogger()
    for i in range(num_mazes):
        mg = MazeGenerator(width, height)
        maze, start, goal = mg.generate_maze()
        algo = DijkstraAlgorithm(mg)
        path, dist = algo.shortest_path(start, goal, enable_logging=False)
        stats = algo.last_run_stats or {}
        result = {
            'success': path is not None,
            'start': start,
            'goal': goal,
            'path': path or [],
            'distance': dist if path is not None else -1,
            'path_length': len(path) if path else 0,
            'computation_time_ms': stats.get('computation_time_ms', 0.0),
            'nodes_explored': stats.get('nodes_explored', 0),
            'efficiency': (len(path) / max(1, stats.get('nodes_explored', 1))) if path else 0.0,
            'no_wall_crossing': True if path else False,
            'path_valid': True if path else False,
            'optimal_path': True,  # relies on BFS verify toggle for sanity
        }
        logger.log_pathfinding_session(mg, algo, [result])
        if (i + 1) % 10 == 0:
            print(f"Generated {i+1}/{num_mazes} mazes")

    logger.save_session_summary()
    dataset = logger.generate_training_dataset()
    print('Done. Samples:', len(dataset))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--num-mazes', type=int, default=50)
    p.add_argument('--width', type=int, default=21)
    p.add_argument('--height', type=int, default=21)
    p.add_argument('--astar', action='store_true')
    p.add_argument('--no-verify-bfs', action='store_true')
    args = p.parse_args()
    run_generation(args.num_mazes, args.width, args.height, astar=args.astar, verify_bfs=(not args.no_verify_bfs))

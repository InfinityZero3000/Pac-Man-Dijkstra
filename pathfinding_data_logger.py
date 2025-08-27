#!/usr/bin/env python3
"""
Advanced Pathfinding Data Logger for Training Data Collection
"""

import json
import os
import numpy as np
from datetime import datetime
import hashlib
from collections import defaultdict

class PathfindingDataLogger:
    def __init__(self, base_dir="training_data"):
        self.base_dir = base_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_data = []
        self.maze_cache = {}  # Cache to avoid duplicate mazes

        # Create directory structure
        self._create_directories()

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.base_dir,
            os.path.join(self.base_dir, "sessions"),
            os.path.join(self.base_dir, "mazes"),
            os.path.join(self.base_dir, "paths"),
            os.path.join(self.base_dir, "training_sets")
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def log_pathfinding_session(self, maze_generator, dijkstra_algorithm, test_results):
        """Log a complete pathfinding session"""
        maze_hash = self._get_maze_hash(maze_generator.maze)

        # Skip if maze already processed
        if maze_hash in self.maze_cache:
            return

        self.maze_cache[maze_hash] = True

        session_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "maze_info": {
                "hash": maze_hash,
                "size": f"{maze_generator.height}x{maze_generator.width}",
                "dimensions": [maze_generator.height, maze_generator.width],
                "start": maze_generator.start,
                "goal": maze_generator.goal,
                "maze_data": maze_generator.maze.tolist()
            },
            "algorithm_info": {
                "type": "optimized_dijkstra",
                "features": [
                    "wall_detection",
                    "obstacle_penalty",
                    "path_validation",
                    "performance_tracking"
                ]
            },
            "test_results": test_results,
            "performance_metrics": self._calculate_performance_metrics(test_results)
        }

        self.session_data.append(session_data)

        # Save individual files
        self._save_maze_data(maze_generator, maze_hash)
        self._save_path_data(test_results, maze_hash)

    def _get_maze_hash(self, maze):
        """Generate unique hash for maze"""
        maze_bytes = np.array(maze).tobytes()
        return hashlib.md5(maze_bytes).hexdigest()

    def _save_maze_data(self, maze_generator, maze_hash):
        """Save maze data separately"""
        maze_data = {
            "hash": maze_hash,
            "size": f"{maze_generator.height}x{maze_generator.width}",
            "start": maze_generator.start,
            "goal": maze_generator.goal,
            "maze": maze_generator.maze.tolist(),
            "metadata": {
                "wall_density": np.mean(maze_generator.maze),
                "path_density": 1 - np.mean(maze_generator.maze),
                "complexity_score": self._calculate_maze_complexity(maze_generator)
            }
        }

        filename = f"maze_{maze_hash}.json"
        filepath = os.path.join(self.base_dir, "mazes", filename)

        with open(filepath, 'w') as f:
            json.dump(maze_data, f, indent=2)

    def _save_path_data(self, test_results, maze_hash):
        """Save path data separately"""
        for i, result in enumerate(test_results):
            if result.get("success", False):
                path_data = {
                    "maze_hash": maze_hash,
                    "path_id": f"{maze_hash}_{i}",
                    "start": result["start"],
                    "goal": result["goal"],
                    "path": result["path"],
                    "distance": result["distance"],
                    "path_length": len(result["path"]),
                    "computation_time_ms": result["computation_time_ms"],
                    "nodes_explored": result["nodes_explored"],
                    "efficiency": result["path_length"] / result["nodes_explored"] if result["nodes_explored"] > 0 else 0,
                    "validation": {
                        "no_wall_crossing": result.get("no_wall_crossing", True),
                        "path_valid": result.get("path_valid", True),
                        "optimal_path": result.get("optimal_path", True)
                    }
                }

                filename = f"path_{maze_hash}_{i}.json"
                filepath = os.path.join(self.base_dir, "paths", filename)

                with open(filepath, 'w') as f:
                    json.dump(path_data, f, indent=2)

    def _calculate_maze_complexity(self, maze_generator):
        """Calculate maze complexity score"""
        maze = maze_generator.maze
        height, width = maze.shape

        # Dead ends
        dead_ends = 0
        branches = 0

        for i in range(1, height - 1):
            for j in range(1, width - 1):
                if maze[i, j] == 0:  # Path
                    neighbors = maze_generator.get_neighbors((i, j))
                    if len(neighbors) == 1:
                        dead_ends += 1
                    elif len(neighbors) >= 3:
                        branches += 1

        # Complexity score
        complexity = {
            "dead_ends": dead_ends,
            "branches": branches,
            "branching_ratio": branches / max(dead_ends, 1),
            "total_junctions": dead_ends + branches
        }

        return complexity

    def _calculate_performance_metrics(self, test_results):
        """Calculate overall performance metrics"""
        if not test_results:
            return {}

        successful_tests = [r for r in test_results if r.get("success", False)]

        if not successful_tests:
            return {"success_rate": 0}

        metrics = {
            "total_tests": len(test_results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(test_results),
            "avg_path_length": np.mean([r["path_length"] for r in successful_tests]),
            "avg_distance": np.mean([r["distance"] for r in successful_tests]),
            "avg_computation_time": np.mean([r["computation_time_ms"] for r in successful_tests]),
            "avg_efficiency": np.mean([r["efficiency"] for r in successful_tests]),
            "avg_nodes_explored": np.mean([r["nodes_explored"] for r in successful_tests])
        }

        return metrics

    def save_session_summary(self):
        """Save session summary"""
        summary_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_mazes": len(self.session_data),
            "summary": self._calculate_overall_summary()
        }

        filename = f"session_summary_{self.session_id}.json"
        filepath = os.path.join(self.base_dir, "sessions", filename)

        with open(filepath, 'w') as f:
            json.dump(summary_data, f, indent=2)

        print(f"Session summary saved: {filepath}")

    def _calculate_overall_summary(self):
        """Calculate overall session summary"""
        if not self.session_data:
            return {}

        all_results = []
        for session in self.session_data:
            all_results.extend(session["test_results"])

        return self._calculate_performance_metrics(all_results)

    def generate_training_dataset(self, output_file=None):
        """Generate a consolidated training dataset"""
        if not output_file:
            output_file = f"training_dataset_{self.session_id}.json"

        training_data = []

        # Collect all successful paths
        for session in self.session_data:
            for result in session["test_results"]:
                if result.get("success", False):
                    # Convert to training format
                    sample = {
                        "maze_features": self._extract_maze_features(session["maze_info"]),
                        "start_position": result["start"],
                        "goal_position": result["goal"],
                        "optimal_path": result["path"],
                        "path_length": result["path_length"],
                        "distance": result["distance"],
                        "metadata": {
                            "maze_hash": session["maze_info"]["hash"],
                            "computation_time": result["computation_time_ms"],
                            "efficiency": result["efficiency"]
                        }
                    }
                    training_data.append(sample)

        # Save training dataset
        filepath = os.path.join(self.base_dir, "training_sets", output_file)
        with open(filepath, 'w') as f:
            json.dump(training_data, f, indent=2)

        print(f"Training dataset saved: {filepath}")
        print(f"Total training samples: {len(training_data)}")

        return training_data

    def _extract_maze_features(self, maze_info):
        """Extract features from maze for ML training"""
        maze = np.array(maze_info["maze_data"])
        height, width = maze.shape

        features = {
            "dimensions": [height, width],
            "wall_density": np.mean(maze),
            "path_density": 1 - np.mean(maze),
            "maze_pattern": maze.tolist(),
            "start_relative": [
                maze_info["start"][0] / height,
                maze_info["start"][1] / width
            ],
            "goal_relative": [
                maze_info["goal"][0] / height,
                maze_info["goal"][1] / width
            ]
        }

        return features

    def cleanup(self):
        """Clean up resources"""
        self.session_data = []
        self.maze_cache = {}

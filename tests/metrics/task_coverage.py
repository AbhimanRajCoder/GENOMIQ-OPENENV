import os
import yaml
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class TaskMetric(BaseModel):
    score: float
    passed: bool
    details: str
    tasks: List[Dict[str, Any]] = []

def scan_tasks(repo_path: str = ".") -> TaskMetric:
    """Scans for task definitions in openenv.yaml or tasks/ folder."""
    tasks = []
    
    # 1. Check openenv.yaml in repo root
    openenv_yaml = os.path.join(repo_path, "openenv.yaml")
    if os.path.exists(openenv_yaml):
        try:
            with open(openenv_yaml, "r") as f:
                data = yaml.safe_load(f)
                if "tasks" in data:
                    for task in data["tasks"]:
                        tasks.append({
                            "name": task.get("name", "unknown"),
                            "difficulty": task.get("difficulty", "unknown"),
                            "source": "openenv.yaml"
                        })
        except Exception as e:
            print(f"Error parsing openenv.yaml: {e}")

    # 2. Check for env/tasks.py or similar
    tasks_py = os.path.join(repo_path, "env", "tasks.py")
    if os.path.exists(tasks_py):
        try:
            with open(tasks_py, "r") as f:
                content = f.read()
                # Find Task(...) definitions using regex
                # Example: Task(name="single_regulator", ..., difficulty="easy", ...)
                task_matches = re.finditer(r'Task\(\s*name="(?P<name>[^"]+)",\s*.*?difficulty="(?P<difficulty>[^"]+)"', content, re.DOTALL)
                for match in task_matches:
                    tasks.append({
                        "name": match.group("name"),
                        "difficulty": match.group("difficulty"),
                        "source": "env/tasks.py"
                    })
        except Exception as e:
            print(f"Error parsing tasks.py: {e}")

    # 3. Check for datasets/ folder
    datasets_dir = os.path.join(repo_path, "datasets")
    if os.path.exists(datasets_dir):
        for item in os.listdir(datasets_dir):
            if item.endswith(".csv"):
                tasks.append({
                    "name": item.replace(".csv", ""),
                    "difficulty": "unknown",
                    "source": "datasets folder"
                })

    # Scoring logic
    score = 100.0
    errors = []
    
    # Check for min 3 tasks
    if len(tasks) < 3:
        score -= (3 - len(tasks)) * 20
        errors.append(f"Fewer than 3 tasks detected (found {len(tasks)}).")
    
    # Check for difficulty labels (easy/medium/hard)
    diffs = set(t["difficulty"] for t in tasks)
    required_diffs = {"easy", "medium", "hard"}
    missing_diffs = required_diffs - diffs
    if missing_diffs:
        score -= len(missing_diffs) * 10
        errors.append(f"Missing difficulty labels: {', '.join(missing_diffs)}.")

    score = max(0, score)
    passed = len(tasks) >= 3 and score >= 70
    
    details = f"Detected {len(tasks)} tasks." if passed else " ".join(errors)
    return TaskMetric(score=score, passed=passed, details=details, tasks=tasks)

if __name__ == "__main__":
    res = scan_tasks()
    import json
    print(res.model_dump_json(indent=2))

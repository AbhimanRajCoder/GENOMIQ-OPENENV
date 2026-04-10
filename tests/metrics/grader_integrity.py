import os
import sys
import importlib.util
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class GraderMetric(BaseModel):
    score: float
    passed: bool
    details: str
    results: List[Dict[str, Any]] = []

def verify_grader(repo_path: str = ".") -> GraderMetric:
    """Verifies grader returns scores in [0.0, 1.0] and is deterministic."""
    graders_path = os.path.join(repo_path, "env", "graders.py")
    if not os.path.exists(graders_path):
        return GraderMetric(score=0, passed=False, details="graders.py not found.")

    try:
        # Dynamic import of graders.py
        spec = importlib.util.spec_from_file_location("env.graders", graders_path)
        graders = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graders)
        
        # Test the grade() function
        if not hasattr(graders, "grade"):
            return GraderMetric(score=0, passed=False, details="grade() function not found in graders.py.")

        # Dummy trajectory and final state
        dummy_trajectory = [{"step": 1, "action": 0, "reward": 0.0, "gene_tested": "TP53"}]
        dummy_final_state = {
            "submitted_candidates": ["TP53"],
            "true_targets": ["TP53"],
            "hypothesis_confidence": 0.9,
            "max_steps": 50,
            "submitted": True,
            "steps_used": 1
        }
        
        # Run 3x to check determinism
        results = []
        for _ in range(3):
            res = graders.grade(dummy_trajectory, dummy_final_state, "single_regulator")
            results.append(res)
            
        # Scoring logic
        score = 100.0
        errors = []
        
        # Check scores in [0.0, 1.0]
        for res in results:
            if not isinstance(res, (float, int)):
                score -= 30
                errors.append(f"Grader returned non-numeric score: {type(res)}")
                break
            if not (0.0 <= res <= 1.0):
                score -= 30
                errors.append(f"Grader score {res} outside [0.0, 1.0].")
                break
        
        # Check determinism
        if len(set(results)) > 1:
            score -= 50
            errors.append(f"Grader is non-deterministic: {results}")

        score = max(0, score)
        passed = score >= 80
        
        details = "Grader is deterministic and scores are within [0.0, 1.0]." if passed else " ".join(errors)
        return GraderMetric(score=score, passed=passed, details=details, results=[{"task": "single_regulator", "scores": results}])

    except Exception as e:
        return GraderMetric(score=0, passed=False, details=f"Error running grader: {str(e)}")

if __name__ == "__main__":
    res = verify_grader()
    import json
    print(res.model_dump_json(indent=2))

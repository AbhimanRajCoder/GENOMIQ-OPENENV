import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel

class RewardMetric(BaseModel):
    score: float
    passed: bool
    details: str
    stats: Dict[str, Any]

def analyze_rewards(step_lines: List[Dict[str, Any]]) -> RewardMetric:
    """Analyzes the quality of the reward signal."""
    if not step_lines:
        return RewardMetric(
            score=0, 
            passed=False, 
            details="No reward data to analyze.",
            stats={}
        )

    rewards = [float(line["data"]["reward"]) for line in step_lines]
    
    mean_val = np.mean(rewards)
    std_val = np.std(rewards)
    min_val = np.min(rewards)
    max_val = np.max(rewards)
    unique_vals = len(set(rewards))
    
    zeros_count = rewards.count(0.0)
    zeros_pct = zeros_count / len(rewards)
    
    is_sparse = zeros_pct > 0.80
    is_constant = std_val == 0
    
    # Check for partial signal (more than just 0 and 1)
    unique_set = set(rewards)
    has_partial = any(0 < abs(r) < 1 for r in unique_set) if unique_set else False
    
    # Scoring logic
    score = 100.0
    warnings = []
    
    if is_sparse:
        score -= 30
        warnings.append("SPARSE: >80% of rewards are 0.00.")
    
    if is_constant:
        score -= 50
        warnings.append("CONSTANT: Reward signal has zero variance.")
    
    if not has_partial and unique_vals <= 2:
        score -= 20
        warnings.append("NO_PARTIAL_SIGNAL: Only discrete rewards (e.g. 0 and 1) detected.")

    score = max(0, score)
    passed = not is_constant and score >= 50
    
    stats = {
        "mean": float(mean_val),
        "std": float(std_val),
        "min": float(min_val),
        "max": float(max_val),
        "unique_values": unique_vals,
        "zeros_pct": float(zeros_pct)
    }
    
    details = "Reward signal is healthy." if passed else " ".join(warnings)
    return RewardMetric(score=score, passed=passed, details=details, stats=stats)

if __name__ == "__main__":
    # Test with dummy data
    test_data = [{"data": {"reward": "0.00"}}, {"data": {"reward": "0.50"}}, {"data": {"reward": "1.00"}}]
    res = analyze_rewards(test_data)
    print(res.model_dump_json(indent=2))

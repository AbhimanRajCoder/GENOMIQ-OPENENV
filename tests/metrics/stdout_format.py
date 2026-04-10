import re
import subprocess
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class StdoutMetric(BaseModel):
    score: float
    passed: bool
    details: str
    lines: List[Dict[str, Any]] = []

def validate_stdout(inference_path: str = "inference.py") -> StdoutMetric:
    """Runs inference.py and validates its stdout format."""
    try:
        # Mocking required environment variables for a dry run if needed
        # But here we assume we run it in a controlled way.
        # To avoid actual LLM calls during a quick format check, 
        # we might need to mock HF_TOKEN if not set, but the requirement is to run it.
        result = subprocess.run(
            [sys.executable, inference_path],
            capture_output=True,
            text=True,
            timeout=300, # 5 minutes max for format check
            env={**dict(sys.stdin.environ), "LIMIT_TASKS": "1"} # Limit to 1 task for speed
        )
        stdout = result.stdout
    except subprocess.TimeoutExpired:
        return StdoutMetric(score=0, passed=False, details="Inference timed out during stdout validation.")
    except Exception as e:
        return StdoutMetric(score=0, passed=False, details=f"Failed to run inference: {str(e)}")

    lines = stdout.splitlines()
    parsed_lines = []
    
    start_pattern = re.compile(r"^\[START\] task=(?P<task>\S+) env=(?P<env>\S+) model=(?P<model>\S+)$")
    step_pattern = re.compile(r"^\[STEP\]\s+step=(?P<step>\d+) action=(?P<action>.+?) reward=(?P<reward>-?\d+\.\d{2}) done=(?P<done>true|false) error=(?P<error>.+)$")
    end_pattern = re.compile(r"^\[END\]\s+success=(?P<success>true|false) steps=(?P<steps>\d+) score=(?P<score>\d+\.\d{3}) rewards=(?P<rewards>[\d\.,-]+)$")

    errors = []
    has_start = False
    has_end = False
    step_count = 0
    malformed_count = 0

    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith("[START]"):
            match = start_pattern.match(line)
            if match:
                has_start = True
                parsed_lines.append({"type": "START", "data": match.groupdict()})
            else:
                errors.append(f"Malformed [START] line: {line}")
                malformed_count += 1
        elif line.startswith("[STEP]"):
            match = step_pattern.match(line)
            if match:
                step_count += 1
                data = match.groupdict()
                # Additional type validation
                try:
                    float(data["reward"])
                except ValueError:
                    errors.append(f"Invalid reward in [STEP]: {line}")
                parsed_lines.append({"type": "STEP", "data": data})
            else:
                errors.append(f"Malformed [STEP] line: {line}")
                malformed_count += 1
        elif line.startswith("[END]"):
            match = end_pattern.match(line)
            if match:
                has_end = True
                data = match.groupdict()
                # Validate rewards list
                rewards = data["rewards"].split(",")
                for r in rewards:
                    try:
                        if r != "null": float(r)
                    except ValueError:
                        errors.append(f"Invalid reward in [END] rewards list: {r}")
                parsed_lines.append({"type": "END", "data": data})
            else:
                errors.append(f"Malformed [END] line: {line}")
                malformed_count += 1

    # Scoring
    score = 100.0
    if not has_start:
        score -= 30
        errors.append("Missing [START] line.")
    if not has_end:
        score -= 30
        errors.append("Missing [END] line.")
    if step_count == 0:
        score -= 20
        errors.append("No [STEP] lines detected.")
    
    if malformed_count > 0:
        penalty = (malformed_count / max(1, len(lines))) * 100
        score -= penalty

    score = max(0, score)
    passed = has_start and has_end and malformed_count == 0 and score > 80

    details = "Stdout format is valid." if passed else "\n".join(errors[:10])
    return StdoutMetric(score=score, passed=passed, details=details, lines=parsed_lines)

if __name__ == "__main__":
    # For independent testing
    import json
    res = validate_stdout()
    print(res.model_dump_json(indent=2))

import subprocess
import os
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DockerMetric(BaseModel):
    score: float
    passed: bool
    details: str
    build_time: float = 0.0

def validate_docker_build(repo_path: str = ".") -> DockerMetric:
    """Runs docker build and reports success/failure."""
    dockerfile_path = os.path.join(repo_path, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        return DockerMetric(score=0, passed=False, details="Dockerfile not found in repo root.")

    start_time = time.time()
    try:
        # Run docker build with a timeout
        result = subprocess.run(
            ["docker", "build", "-t", "genomiq-test-build", repo_path],
            capture_output=True,
            text=True,
            timeout=600 # 10 minutes timeout
        )
        end_time = time.time()
        build_time = end_time - start_time
        
        if result.returncode == 0:
            return DockerMetric(
                score=100.0, 
                passed=True, 
                details=f"Docker build succeeded in {build_time:.2f}s.",
                build_time=build_time
            )
        else:
            # Get last 20 lines of output on failure
            last_lines = "\n".join(result.stdout.splitlines()[-20:] + result.stderr.splitlines()[-20:])
            return DockerMetric(
                score=0, 
                passed=False, 
                details=f"Docker build failed with code {result.returncode}. Last 20 lines of output:\n{last_lines}",
                build_time=build_time
            )
            
    except subprocess.TimeoutExpired:
        return DockerMetric(score=0, passed=False, details="Docker build timed out (600s).")
    except Exception as e:
        return DockerMetric(score=0, passed=False, details=f"Error running docker build: {str(e)}")

if __name__ == "__main__":
    res = validate_docker_build()
    import json
    print(res.model_dump_json(indent=2))

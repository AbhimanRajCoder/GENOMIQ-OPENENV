#!/usr/bin/env python3
"""
validate-phase2.py — Phase 2: Agentic Evaluation Simulator

This script simulates the automated agentic evaluation stage (Phase 2) of the 
OpenEnv submission process. It runs the baseline agent against the core tasks, 
collects logs, and verifies that the task scores adhere to benchmark constraints
(e.g., scores strictly within (0, 1)).
"""

import sys
import os
import subprocess
import time
import requests
import re
from typing import List, Dict

# Color constants
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
NC = "\033[0m"

SERVER_URL = "http://localhost:7860"
TASKS = ["single_regulator", "coexpression_cluster", "interaction_effect"]

def print_header(text: str):
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}{text.center(60)}{NC}")
    print(f"{BOLD}{'='*60}{NC}\n")

def check_server() -> bool:
    """Check if the GenomIQ server is running."""
    try:
        resp = requests.get(f"{SERVER_URL}/health", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_server():
    """Start the FastAPI server in the background."""
    print(f"[{time.strftime('%H:%M:%S')}] Starting GenomIQ server for Phase 2 eval...")
    # Using 'server' script defined in pyproject.toml
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to be ready
    for _ in range(10):
        if check_server():
            print(f"[{time.strftime('%H:%M:%S')}] {GREEN}Server is up and running.{NC}")
            return proc
        time.sleep(2)
    
    print(f"[{time.strftime('%H:%M:%S')}] {RED}Failed to start server.{NC}")
    proc.terminate()
    sys.exit(1)

def run_baseline_agent() -> List[str]:
    """Run inference.py and return the output lines."""
    print(f"[{time.strftime('%H:%M:%S')}] {BOLD}Phase 2: Rerunning Baseline Agent (inference.py)...{NC}")
    try:
        # Run inference.py; it will hit the local server
        result = subprocess.run(
            [sys.executable, "inference.py"],
            capture_output=True,
            text=True,
            env={**os.environ, "SERVER_URL": SERVER_URL, "MODEL_NAME": "heuristic-only"} # use fallback to avoid actual LLM cost/latency during validation if token missing
        )
        return result.stdout.splitlines()
    except Exception as e:
        print(f"{RED}Error running inference.py: {e}{NC}")
        return []

def parse_and_validate_scores(output_lines: List[str]) -> bool:
    """Parse output for [END] lines and validate scores."""
    print_header("Evaluation Results & Score Checks")
    
    score_regex = re.compile(r"\[END\].*success=(true|false).*steps=(\d+).*rewards=([\d.,-]+)")
    # Wait, inference.py log_end doesn't print the score anymore in my version? 
    # Let me check inference.py again. Ah, line 41 says: "# removed score to match strict spec"
    # But it still returns it in the logic. Let's check lines 191 and 240.
    # Line 240: print(f"{status} {r['task']}: score={r['score']:.3f} steps={r['steps']}")
    
    summary_regex = re.compile(r"(✓|✗)\s+(\w+):\s+score=([\d.]+)\s+steps=(\d+)")
    
    results = []
    for line in output_lines:
        match = summary_regex.search(line)
        if match:
            status, task, score, steps = match.groups()
            results.append({
                "task": task,
                "score": float(score),
                "success": status == "✓"
            })

    if not results:
        print(f"{RED}No task results found in inference.py output.{NC}")
        return False

    all_valid = True
    for res in results:
        task = res['task']
        score = res['score']
        
        # PRIMARY CHECK: Strictly between 0 and 1
        is_strictly_between = 0.0 < score < 1.0
        
        status_color = GREEN if is_strictly_between else RED
        status_text = "PASSED" if is_strictly_between else "FAILED"
        
        print(f"Task: {task:<25} | Score: {status_color}{score:.3f}{NC} | Constraint (0,1): {status_color}{status_text}{NC}")
        
        if not is_strictly_between:
            print(f"  {RED}Reason: Score {score} must be > 0.0 AND < 1.0.{NC}")
            all_valid = False

    return all_valid

def main():
    print_header("GenomIQ Phase 2: Agentic Evaluation Simulator")
    
    server_proc = None
    if not check_server():
        server_proc = start_server()
    else:
        print(f"[{time.strftime('%H:%M:%S')}] {YELLOW}Server already running.{NC}")

    try:
        output = run_baseline_agent()
        if not output:
            print(f"{RED}Evaluation failed to produce output.{NC}")
            sys.exit(1)
            
        success = parse_and_validate_scores(output)
        
        if success:
            print(f"\n{GREEN}{BOLD}PHASE 2 VALIDATION COMPLETED SUCCESSFULLY!{NC}")
            print(f"Your submission is ready for actual agentic evaluation.")
        else:
            print(f"\n{RED}{BOLD}PHASE 2 VALIDATION FAILED.{NC}")
            print("Please check your grader logic in `env/graders.py`.")
            sys.exit(1)

    finally:
        if server_proc:
            print(f"\n[{time.strftime('%H:%M:%S')}] Cleaning up server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    main()

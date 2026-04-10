import argparse
import os
import sys
import asyncio
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Add project root to sys.path to allow absolute imports from tests package
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tests.metrics.stdout_format import validate_stdout
from tests.metrics.reward_quality import analyze_rewards
from tests.metrics.task_coverage import scan_tasks
from tests.metrics.grader_integrity import verify_grader
from tests.metrics.env_compliance import validate_env
from tests.metrics.docker_build import validate_docker_build
from tests.metrics.hf_space_ping import validate_hf_space_ping
from tests.metrics.inference_contract import validate_inference_contract
from tests.metrics.runtime_limits import validate_runtime_limits
from tests.report.summary import generate_summary, SummaryMetric

async def run_eval(github_url: str, hf_space_url: str):
    # Strip any extra spaces from input URLs
    github_url = github_url.strip()
    hf_space_url = hf_space_url.strip()
    
    console = Console()
    console.print(f"\n[bold blue]🚀 Starting OpenEnv RL Hackathon Evaluation[/bold blue]")
    console.print(f"GitHub: [cyan]{github_url}[/cyan]")
    console.print(f"HF Space: [cyan]{hf_space_url}[/cyan]\n")

    metrics_results = []
    
    # 1. Clone repo (shallow)
    # Using a temporary directory for repo cloning if github_url is different from current
    # For now, let's assume we are testing the current project if github_url matches
    # If github_url is different, we would need to git clone it.
    # To simplify for the user, let's assume we are testing the current repo
    # but still allow for cloning if github_url is provided.
    
    # Actually, the user asked for:
    # `python tests/run_eval.py --github <GITHUB_REPO_URL> --hf-space <HF_SPACE_URL>`
    # I'll implement cloning to a temp directory.
    
    import tempfile
    import shutil
    import subprocess
    
    repo_path = os.getcwd() # Default to current repo
    temp_dir = None
    
    # Simple check if current repo matches github_url
    # For now, I'll just clone it to a temp dir to be safe.
    try:
        temp_dir = tempfile.mkdtemp()
        console.print(f"Cloning repo to {temp_dir}...")
        subprocess.run(["git", "clone", "--depth", "1", github_url, temp_dir], check=True, capture_output=True)
        repo_path = temp_dir
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] Failed to clone repo: {e}. Testing current directory instead.")
        repo_path = os.getcwd()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # stdout_format (15%)
            t1 = progress.add_task("[cyan]Validating stdout format...", total=100)
            res_stdout = validate_stdout(os.path.join(repo_path, "inference.py"))
            progress.update(t1, completed=100)
            metrics_results.append(SummaryMetric(
                name="stdout_format", weight=0.15, score=res_stdout.score, 
                weighted_score=res_stdout.score * 0.15, passed=res_stdout.passed, 
                details=res_stdout.details
            ))

            # reward_quality (20%)
            t2 = progress.add_task("[cyan]Analyzing reward quality...", total=100)
            res_reward = analyze_rewards(res_stdout.lines)
            progress.update(t2, completed=100)
            metrics_results.append(SummaryMetric(
                name="reward_quality", weight=0.20, score=res_reward.score, 
                weighted_score=res_reward.score * 0.20, passed=res_reward.passed, 
                details=res_reward.details
            ))

            # task_coverage (25%)
            t3 = progress.add_task("[cyan]Checking task coverage and grader integrity...", total=100)
            res_task = scan_tasks(repo_path)
            res_grader = verify_grader(repo_path)
            
            # Combine scores
            task_score = (res_task.score + res_grader.score) / 2
            task_passed = res_task.passed and res_grader.passed
            task_details = f"{res_task.details} | Grader: {res_grader.details}"
            
            progress.update(t3, completed=100)
            metrics_results.append(SummaryMetric(
                name="task_coverage", weight=0.25, score=task_score, 
                weighted_score=task_score * 0.25, passed=task_passed, 
                details=task_details
            ))

            # env_compliance (20%)
            t4 = progress.add_task("[cyan]Validating env compliance...", total=100)
            res_env = await validate_env(repo_path)
            progress.update(t4, completed=100)
            metrics_results.append(SummaryMetric(
                name="env_compliance", weight=0.20, score=res_env.score, 
                weighted_score=res_env.score * 0.20, passed=res_env.passed, 
                details=res_env.details
            ))

            # docker_build (10%)
            t5 = progress.add_task("[cyan]Testing Docker build...", total=100)
            res_docker = validate_docker_build(repo_path)
            progress.update(t5, completed=100)
            metrics_results.append(SummaryMetric(
                name="docker_build", weight=0.10, score=res_docker.score, 
                weighted_score=res_docker.score * 0.10, passed=res_docker.passed, 
                details=res_docker.details
            ))

            # hf_space_ping (5%)
            t6 = progress.add_task("[cyan]Pinging HF Space...", total=100)
            res_ping = validate_hf_space_ping(hf_space_url)
            progress.update(t6, completed=100)
            metrics_results.append(SummaryMetric(
                name="hf_space_ping", weight=0.05, score=res_ping.score, 
                weighted_score=res_ping.score * 0.05, passed=res_ping.passed, 
                details=res_ping.details
            ))

            # inference_contract (5%)
            t7 = progress.add_task("[cyan]Verifying inference contract...", total=100)
            res_contract = validate_inference_contract(repo_path)
            progress.update(t7, completed=100)
            metrics_results.append(SummaryMetric(
                name="inference_contract", weight=0.05, score=res_contract.score, 
                weighted_score=res_contract.score * 0.05, passed=res_contract.passed, 
                details=res_contract.details
            ))

            # runtime_limits (Hard rule, 0% weight in table but blocks submission)
            t8 = progress.add_task("[cyan]Measuring runtime limits...", total=100)
            res_runtime = validate_runtime_limits(os.path.join(repo_path, "inference.py"))
            progress.update(t8, completed=100)
            metrics_results.append(SummaryMetric(
                name="runtime_limits", weight=0.0, score=res_runtime.score, 
                weighted_score=0.0, passed=res_runtime.passed, 
                details=res_runtime.details
            ))

        # Generate final report
        report = generate_summary(metrics_results)
        
        # Exit with correct status code
        if report.is_ready:
            sys.exit(0)
        else:
            sys.exit(1)

    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenEnv RL Hackathon Evaluation Tool")
    parser.add_argument("--github", type=str, required=True, help="GitHub repo URL")
    parser.add_argument("--hf-space", type=str, required=True, help="Hugging Face Space URL")
    
    args = parser.parse_args()
    
    asyncio.run(run_eval(args.github, args.hf_space))

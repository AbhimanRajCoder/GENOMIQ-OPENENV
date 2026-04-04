#!/usr/bin/env python3
"""
GenomIQ baseline inference script.
Uses OpenAI client only. Runs all 3 tasks and logs results.
"""

import json
import os
import sys
import time
from typing import Optional

import requests
from openai import OpenAI

# ── Environment variables ─────────────────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:7860")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# ── Exact logging helpers (DO NOT MODIFY FORMAT) ─────────────────────────────


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ── LLM action selector ──────────────────────────────────────────────────────

ACTION_DESCRIPTIONS = {
    0: "run_experiment_A (cheap, low signal, fast)",
    1: "run_experiment_B (expensive, high signal, slow)",
    2: "refine_hypothesis (update belief from collected data)",
    3: "read_literature (reveal one unknown variable)",
    4: "combine_results (grow knowledge graph)",
    5: "submit_discovery (end episode — only when confident)",
}


def choose_action(observation: dict, task_name: str, step: int) -> int:
    """Ask the LLM to choose an action given the current observation."""
    system_prompt = (
        "You are an AI research scientist in a genomics lab.\n"
        "You must discover hidden gene expression patterns by choosing actions wisely.\n"
        'Respond ONLY with a JSON object: {"action_type": <integer 0-5>, "reason": "<brief reason>"}\n'
        "Do not include any other text."
    )

    user_prompt = (
        f"Task: {task_name}\n"
        f"Current observation:\n"
        f"- Step: {observation.get('step', step)}\n"
        f"- Hypothesis confidence: {observation.get('hypothesis_confidence', 0):.2f}\n"
        f"- Experiments done: {observation.get('experiments_done', 0)}\n"
        f"- Last experiment result: {observation.get('last_result', 0):.2f}\n"
        f"- Knowledge graph nodes: {observation.get('kg_nodes', 0)}\n"
        f"- Unknown variables remaining: {observation.get('unknown_vars', 0)}\n"
        f"- Budget remaining: {observation.get('budget_remaining', 0)}\n"
        f"- Current hypothesis: {observation.get('current_hypothesis', 'None')}\n"
        f"\n"
        f"Available actions:\n"
        f"0 = run_experiment_A (cheap, noisy signal, costs budget)\n"
        f"1 = run_experiment_B (expensive, high signal, costs more budget)\n"
        f"2 = refine_hypothesis (update confidence from data, no direct cost)\n"
        f"3 = read_literature (reveal one unknown variable)\n"
        f"4 = combine_results (grow knowledge graph if experiments done)\n"
        f"5 = submit_discovery (END episode — only if confidence > 0.7)\n"
        f"\n"
        f"Choose the best action. If budget_remaining < 5 and confidence > 0.6, submit.\n"
        f"Respond with JSON only."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=100,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            content = "\n".join(lines).strip()
        parsed = json.loads(content)
        action_type = int(parsed.get("action_type", 2))
        return max(0, min(5, action_type))
    except Exception:
        # Fallback: greedy heuristic strategy
        conf = observation.get("hypothesis_confidence", 0)
        budget = observation.get("budget_remaining", 10)
        if budget <= 3 or conf > 0.8:
            return 5
        elif conf < 0.4:
            return 1
        elif observation.get("unknown_vars", 0) > 0:
            return 3
        else:
            return 2


# ── Episode runner ────────────────────────────────────────────────────────────


def run_episode(task_name: str) -> dict:
    """Run one full episode for a given task. Returns summary dict."""
    rewards: list[float] = []
    steps = 0
    final_score = 0.0
    success = False
    error_msg: str | None = None

    log_start(task=task_name, env="genomiq", model=MODEL_NAME)

    try:
        # Reset environment for this task
        reset_resp = requests.post(
            f"{SERVER_URL}/reset",
            json={"task_name": task_name},
            timeout=30,
        )
        reset_resp.raise_for_status()
        reset_data = reset_resp.json()
        # reset returns the observation dict directly
        obs = reset_data if "task_name" in reset_data else reset_data.get("observation", reset_data)

        done = False
        while not done:
            steps += 1
            action_type = choose_action(obs, task_name, steps)
            action_name = ACTION_DESCRIPTIONS.get(action_type, str(action_type))

            try:
                step_resp = requests.post(
                    f"{SERVER_URL}/step",
                    json={"action_type": action_type},
                    timeout=30,
                )
                step_resp.raise_for_status()
                result = step_resp.json()
            except Exception as e:
                log_step(steps, action_name, 0.0, True, str(e))
                error_msg = str(e)
                break

            reward = float(result.get("reward", 0.0))
            done = bool(result.get("done", False))
            obs = result.get("observation", {})
            info = result.get("info", {})

            rewards.append(reward)
            log_step(steps, action_name, reward, done, None)

            # Extract final score if submitted
            if "final_score" in info:
                final_score = float(info["final_score"])
                success = final_score >= 0.5  # threshold for success

            if done:
                break

        # Compute score from rewards if not already set
        if final_score == 0.0 and rewards:
            total_positive = sum(r for r in rewards if r > 0)
            final_score = max(0.0, min(1.0, total_positive / max(1, len(rewards)) / 20.0))

    except Exception as e:
        error_msg = str(e)
        print(f"Episode error: {e}", file=sys.stderr)

    log_end(success=success, steps=steps, score=final_score, rewards=rewards)

    return {
        "task": task_name,
        "steps": steps,
        "score": final_score,
        "success": success,
        "rewards": rewards,
        "error": error_msg,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    if not HF_TOKEN:
        print("WARNING: HF_TOKEN not set. LLM calls will fail.", file=sys.stderr)

    # Core mandated tasks (always run)
    tasks = ["single_regulator", "coexpression_cluster", "interaction_effect"]
    # Additional tasks can be selected via env var (comma-separated)
    extra = os.getenv("EXTRA_TASKS", "")
    if extra:
        tasks.extend(t.strip() for t in extra.split(",") if t.strip())
    results: list[dict] = []

    # Wait for server to be ready
    for attempt in range(10):
        try:
            r = requests.get(f"{SERVER_URL}/health", timeout=5)
            if r.status_code == 200:
                break
        except Exception:
            pass
        print(f"Waiting for server... attempt {attempt + 1}/10", file=sys.stderr)
        time.sleep(3)

    for task in tasks:
        result = run_episode(task)
        results.append(result)
        time.sleep(1)

    # Summary
    print("\n" + "=" * 50, flush=True)
    print("GENOMIQ BASELINE RESULTS", flush=True)
    print("=" * 50, flush=True)
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"{status} {r['task']}: score={r['score']:.3f} steps={r['steps']}", flush=True)


if __name__ == "__main__":
    main()

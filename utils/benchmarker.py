"""
GenomIQ — Agent Benchmarking System.

Runs the same task with multiple agent strategies and produces
comparative metrics for side-by-side evaluation.
"""

import asyncio
import time
from dataclasses import dataclass
from env.environment import GenomIQEnv
from env.agents import get_agent
from env.models import Action


@dataclass
class BenchmarkResult:
    agent_type: str
    episodes: int
    avg_score: float
    avg_reward: float
    avg_steps: float
    success_rate: float
    min_score: float
    max_score: float
    scores: list[float]
    elapsed: float


async def _run_agent_benchmark(config: dict, agent_type: str,
                                task_name: str, n_episodes: int) -> BenchmarkResult:
    """Run n_episodes with a specific agent and collect metrics."""
    config = dict(config)
    config["agent"] = dict(config.get("agent", {}))
    config["agent"]["type"] = agent_type

    env = GenomIQEnv(config_path="config.yaml", task_name=task_name)
    agent = get_agent(agent_type, config)

    scores, rewards, steps_list = [], [], []
    successes = 0
    start = time.time()

    for ep_idx in range(n_episodes):
        env.episode_count = ep_idx
        obs = await env.reset()
        done = False
        ep_reward = 0
        step = 0

        while not done:
            action_type = agent.choose_action(obs)
            action = Action(action_type=action_type)
            result = await env.step(action)
            obs = result["observation"]
            ep_reward += result["reward"]
            done = result["done"]
            step += 1

            if done:
                final_score = result.get("info", {}).get("final_score", 0.0)
                success = result.get("info", {}).get("success", False)
                scores.append(final_score)
                rewards.append(ep_reward)
                steps_list.append(step)
                if success:
                    successes += 1

    elapsed = round(time.time() - start, 2)
    n = max(1, len(scores))

    return BenchmarkResult(
        agent_type=agent_type,
        episodes=n_episodes,
        avg_score=round(sum(scores) / n, 4),
        avg_reward=round(sum(rewards) / n, 2),
        avg_steps=round(sum(steps_list) / n, 1),
        success_rate=round(successes / n, 3),
        min_score=round(min(scores) if scores else 0, 4),
        max_score=round(max(scores) if scores else 0, 4),
        scores=scores,
        elapsed=elapsed,
    )


async def run_benchmark(config: dict, task_name: str = "single_regulator",
                         agents: list[str] | None = None,
                         episodes_per_agent: int = 5) -> dict:
    """Run a full benchmark comparison across multiple agents.

    Returns a dict mapping agent_type -> BenchmarkResult.__dict__
    """
    if agents is None:
        agents = ["random", "greedy", "ppo"]

    results = {}
    for agent_type in agents:
        result = await _run_agent_benchmark(config, agent_type, task_name, episodes_per_agent)
        results[agent_type] = {
            "agent_type": result.agent_type,
            "episodes": result.episodes,
            "avg_score": result.avg_score,
            "avg_reward": result.avg_reward,
            "avg_steps": result.avg_steps,
            "success_rate": result.success_rate,
            "min_score": result.min_score,
            "max_score": result.max_score,
            "scores": result.scores,
            "elapsed": result.elapsed,
        }

    return results


def run_benchmark_sync(config: dict, task_name: str = "single_regulator",
                        agents: list[str] | None = None,
                        episodes_per_agent: int = 5) -> dict:
    """Synchronous wrapper for run_benchmark."""
    return asyncio.run(run_benchmark(config, task_name, agents, episodes_per_agent))

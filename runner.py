import argparse
import asyncio
import json
import yaml
import time
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from env.environment import GenomIQEnv
from env.agents import get_agent
from env.models import Action
from env.logging_config import setup_logger

logger = setup_logger("Runner")


class SimulationRunner:
    """Orchestrates automated runs across episodes."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.env = GenomIQEnv(config_path)
        self.agent = get_agent(self.config["agent"]["type"], self.config)
        self.num_episodes = self.config["scenario"]["num_episodes"]
        self.results_path = Path("results/latest_run.json")
        self.results_path.parent.mkdir(parents=True, exist_ok=True)

    async def run_episode(self, episode_idx: int) -> dict:
        """Execute a single episode simulation."""
        logger.info(f"═══════════════════════════════════════════")
        logger.info(f"EPISODE {episode_idx + 1}/{self.num_episodes} — START")
        logger.info(f"═══════════════════════════════════════════")

        observation = await self.env.reset()
        done = False
        episode_reward = 0
        steps = 0
        action_history = []

        # Capture episode-level gene info
        true_genes = list(self.env.true_gene_names)
        matrix_shape = list(self.env.expression_matrix.shape)

        while not done:
            action_type = self.agent.choose_action(observation)
            action = Action(action_type=action_type)

            result = await self.env.step(action)
            observation = result["observation"]
            episode_reward += result["reward"]
            done = result["done"]
            steps += 1

            action_history.append({
                "step": steps,
                "action": action_type,
                "reward": round(result["reward"], 2),
                "gene_tested": observation.get("last_gene_tested", "—"),
                "confidence": observation.get("hypothesis_confidence", 0),
            })

            if done:
                final_score = result["info"].get("final_score", 0.0)
                success = result["info"].get("success", False)
                status = "SUCCESS" if success else "FAILED"
                logger.info(f"───────────────────────────────────────────")
                logger.info(f"EPISODE {episode_idx + 1} RESULT: {status} | Steps={steps}, Reward={episode_reward:.2f}, Score={final_score:.3f}")
                logger.info(f"───────────────────────────────────────────")

                # Use submitted_candidates from info (set by grader path) or fallback
                submitted = result["info"].get("submitted_candidates", observation.get("top_candidate_genes", []))
                lit_hint = observation.get("literature_hint", "")

                return {
                    "episode": episode_idx + 1,
                    "reward": round(episode_reward, 2),
                    "steps": steps,
                    "score": round(final_score, 3),
                    "success": success,
                    "final_confidence": observation.get("hypothesis_confidence", 0),
                    "true_targets": true_genes,
                    "submitted_candidates": submitted[:5],
                    "matrix_shape": matrix_shape,
                    "last_hint": lit_hint,
                    "kg_nodes": observation.get("kg_nodes", 0),
                    "experiments_done": observation.get("experiments_done", 0),
                    "action_history": action_history,
                    "hypothesis_history": list(self.env.hypothesis_history),
                    "knowledge_graph": self.env._build_knowledge_graph_data(),
                }
        return {}

    async def run_all(self):
        """Execute the batch of episodes and produce a rich summary."""
        start_time = time.time()
        logger.info(f"--- GenomIQ Automated Simulation ---")
        logger.info(f"Domain: {self.config['scenario']['domain']} | Agent: {self.config['agent']['type']} | Episodes: {self.num_episodes}")

        results = []
        for i in tqdm(range(self.num_episodes)):
            res = await self.run_episode(i)
            results.append(res)

        elapsed = round(time.time() - start_time, 2)

        # ── Aggregate metrics ──
        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]
        rewards = [r["reward"] for r in results]
        scores = [r["score"] for r in results]
        steps_list = [r["steps"] for r in results]
        confidences = [r["final_confidence"] for r in results]

        avg_reward = round(sum(rewards) / len(rewards) if rewards else 0, 2)
        avg_score = round(sum(scores) / len(scores) if scores else 0, 3)
        avg_steps = round(sum(steps_list) / len(steps_list) if steps_list else 0, 1)
        avg_conf = round(sum(confidences) / len(confidences) if confidences else 0, 3)
        max_score = round(max(scores), 3) if scores else 0
        min_score = round(min(scores), 3) if scores else 0
        max_reward = round(max(rewards), 2) if rewards else 0
        min_reward = round(min(rewards), 2) if rewards else 0

        # Best / worst episodes
        best_ep = max(results, key=lambda r: r["score"]) if results else {}
        worst_ep = min(results, key=lambda r: r["score"]) if results else {}

        # Gene frequency analysis
        gene_freq = {}
        for r in results:
            for g in r.get("submitted_candidates", []):
                gene_freq[g] = gene_freq.get(g, 0) + 1
        top_submitted = sorted(gene_freq.items(), key=lambda x: -x[1])[:10]

        summary = {
            "run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": elapsed,
                "domain": self.config["scenario"]["domain"],
                "difficulty": self.config["scenario"]["difficulty"],
                "objective": self.config["scenario"].get("objective", ""),
                "agent_type": self.config["agent"]["type"],
                "num_episodes": self.num_episodes,
                "max_steps": self.config["scenario"]["max_steps"],
                "seed": self.config["scenario"]["seed"],
                "dataset_source": self.config.get("dataset", {}).get("source", "synthetic"),
                "dataset_name": self.config.get("dataset", {}).get("name", ""),
                "noise_level": self.config.get("constraints", {}).get("noise_level", 2.0),
                "cost_tier": self.config.get("constraints", {}).get("cost_tier", "mixed"),
                "prior_knowledge": self.config.get("prior_knowledge", {}),
            },
            "metrics": {
                "success_rate": round(len(successes) / self.num_episodes, 3) if self.num_episodes > 0 else 0,
                "avg_reward": avg_reward,
                "avg_score": avg_score,
                "avg_steps": avg_steps,
                "avg_confidence": avg_conf,
                "max_score": max_score,
                "min_score": min_score,
                "max_reward": max_reward,
                "min_reward": min_reward,
                "total_successes": len(successes),
                "total_failures": len(failures),
            },
            "gene_analysis": {
                "most_submitted_candidates": [{"gene": g, "count": c} for g, c in top_submitted],
            },
            "episodes": results,
            "config": self.config,
        }

        with open(self.results_path, "w") as f:
            json.dump(summary, f, indent=2)

        # ── Console summary ──
        logger.info(f"")
        logger.info(f"╔══════════════════════════════════════════════════════════╗")
        logger.info(f"║           GenomIQ SIMULATION SUMMARY REPORT             ║")
        logger.info(f"╠══════════════════════════════════════════════════════════╣")
        logger.info(f"║  Domain:      {self.config['scenario']['domain']:<42}║")
        logger.info(f"║  Difficulty:  {self.config['scenario']['difficulty']:<42}║")
        logger.info(f"║  Agent:       {self.config['agent']['type']:<42}║")
        logger.info(f"║  Episodes:    {self.num_episodes:<42}║")
        logger.info(f"║  Runtime:     {elapsed}s{' ' * (40 - len(str(elapsed)))}║")
        logger.info(f"╠══════════════════════════════════════════════════════════╣")
        logger.info(f"║  Success Rate:     {len(successes)}/{self.num_episodes} ({len(successes)/max(1,self.num_episodes):.0%}){' ' * 28}║")
        logger.info(f"║  Avg Score:        {avg_score:<38}║")
        logger.info(f"║  Avg Steps:        {avg_steps:<38}║")
        logger.info(f"║  Score Range:      [{min_score} — {max_score}]{' ' * 24}║")
        logger.info(f"╚══════════════════════════════════════════════════════════╝")
        logger.info(f"Results saved to: {self.results_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config.yaml")
    args = parser.parse_args()

    runner = SimulationRunner(args.config)
    asyncio.run(runner.run_all())

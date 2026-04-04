"""
GenomIQ — Agent Architectures.

Agents now leverage richer observations including gene names,
top candidates, and literature hints to make informed decisions.
"""

import numpy as np
from abc import ABC, abstractmethod
from env.logging_config import setup_logger

logger = setup_logger("Agents")

ACTION_NAMES = {
    0: "run_experiment_A (microarray)",
    1: "run_experiment_B (qPCR)",
    2: "refine_hypothesis",
    3: "read_literature",
    4: "combine_results",
    5: "submit_discovery",
}


class BaseAgent(ABC):
    """Abstract base class for GenomIQ agents."""

    @abstractmethod
    def choose_action(self, observation: dict) -> int:
        pass


class RandomAgent(BaseAgent):
    """Uniform random agent (avoids early submission)."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)
        if step < 6:
            action = int(self.rng.integers(0, 5))
        else:
            action = int(self.rng.integers(0, 6))
        logger.info(f"[Random] Step {step} → {ACTION_NAMES[action]}")
        return action


class GreedyAgent(BaseAgent):
    """
    Multi-phase heuristic scientist agent.

    Phase 1 (Scan):     Cheap microarray scans to survey the landscape.
    Phase 2 (Validate): Precise qPCR on top candidates.
    Phase 3 (Refine):   Statistical refinement + literature consultation.
    Phase 4 (Build):    Combine results into knowledge graph.
    Phase 5 (Submit):   Submit when confident.
    """

    def choose_action(self, observation: dict) -> int:
        conf   = observation.get("hypothesis_confidence", 0)
        exp    = observation.get("experiments_done", 0)
        budget = observation.get("budget_remaining", 50)
        step   = observation.get("step", 0)
        kg     = observation.get("kg_nodes", 0)
        cands  = observation.get("top_candidate_genes", [])
        hint   = observation.get("literature_hint", "")

        # ── Emergency submit ──
        if budget <= 3:
            logger.info(f"[Greedy] Step {step} | EMERGENCY — budget={budget}, submitting now")
            return 5

        # ── Confident submit ──
        if conf >= 0.70 and exp >= 4 and kg >= 2:
            logger.info(f"[Greedy] Step {step} | SUBMIT — conf={conf:.2f}, exp={exp}, kg={kg}, candidates={cands[:3]}")
            return 5

        # ── Phase 1: Research-heavy opening (Lit → Scan → Lit → Scan → Lit → Scan) ──
        if step < 9:
            if step % 3 == 0:
                logger.info(f"[Greedy] Step {step} | RESEARCH — consulting literature for targets")
                return 3  # Literature first to get hints
            elif step % 3 == 1:
                logger.info(f"[Greedy] Step {step} | SCAN — microarray #{exp+1} (hint-biased), conf={conf:.2f}")
                return 0  # Scan with oracle bias
            else:
                logger.info(f"[Greedy] Step {step} | SCAN — microarray #{exp+1} (hint-biased), conf={conf:.2f}")
                return 0  # Another scan

        # ── Phase 2: Refine to analyze all collected data ──
        if conf < 0.35:
            logger.info(f"[Greedy] Step {step} | REFINE — analyzing {exp} experiments, conf={conf:.2f}")
            return 2

        # ── Phase 3: Validate top candidates with qPCR ──
        if exp < 8 and cands:
            logger.info(f"[Greedy] Step {step} | VALIDATE — qPCR on {cands[0]}, conf={conf:.2f}")
            return 1

        # ── Phase 4: Build knowledge graph ──
        if kg < 3:
            logger.info(f"[Greedy] Step {step} | COMBINE — building knowledge graph, kg={kg}")
            return 4

        # ── Phase 5: Final refinement ──
        if conf < 0.55:
            logger.info(f"[Greedy] Step {step} | REFINE+ — deep analysis, conf={conf:.2f}")
            return 2

        # ── Phase 6: Confidence push ──
        if conf < 0.70:
            if cands:
                logger.info(f"[Greedy] Step {step} | VALIDATE+ — precision test on {cands[0]}, conf={conf:.2f}")
                return 1
            logger.info(f"[Greedy] Step {step} | REFINE+ — need candidates, conf={conf:.2f}")
            return 2

        logger.info(f"[Greedy] Step {step} | SUBMIT — all criteria met. conf={conf:.2f}, candidates={cands[:3]}")
        return 5


class PPOAgent(BaseAgent):
    """Lightweight softmax policy agent."""

    def __init__(self, lr: float = 0.0003, seed: int = 42):
        self.lr = lr
        self.rng = np.random.default_rng(seed)
        self.weights = self.rng.standard_normal(12)

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)
        features = np.array([
            observation.get("step", 0) / 100,
            observation.get("hypothesis_confidence", 0),
            observation.get("experiments_done", 0) / 10,
            observation.get("last_result", 0) / 50,
            observation.get("kg_nodes", 0) / 20,
            observation.get("unknown_vars", 0) / 100,
            1.0
        ])
        padded = np.zeros(12)
        padded[:len(features)] = features

        logits = np.dot(padded.reshape(6, 2), [1, 1])
        if step < 8:
            logits[5] = -1e9
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)

        action = int(self.rng.choice(len(probs), p=probs))
        logger.info(f"[PPO] Step {step} → {ACTION_NAMES[action]}, conf={observation.get('hypothesis_confidence', 0):.2f}")
        return action


def get_agent(agent_type: str, config: dict) -> BaseAgent:
    """Factory to return the appropriate agent instance."""
    t = agent_type.lower()
    seed = config["scenario"].get("seed", 42)
    lr = config["agent"].get("learning_rate", 0.0003)

    if t == "random":
        return RandomAgent(seed=seed)
    elif t == "greedy":
        return GreedyAgent()
    elif t in ("ppo", "dqn"):
        return PPOAgent(lr=lr, seed=seed)
    elif t == "multi_agent":
        from env.multi_agent import MultiAgentTeam
        max_steps = config["scenario"].get("max_steps", 50)
        return MultiAgentTeam(max_steps=max_steps)
    else:
        return GreedyAgent()

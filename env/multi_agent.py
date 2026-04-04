"""
GenomIQ — Multi-Agent Collaboration System.

Three specialized agents collaborate in a staged research protocol:
  - Explorer: Broad survey (Scans + Literature)
  - Validator: Precision confirmation (qPCR + Refine)
  - Theorist: Knowledge synthesis + Submission (Refine + Combine + Submit)

Inspired by DeepMind multi-agent research architecture.
"""

import numpy as np
from env.agents import BaseAgent
from env.logging_config import setup_logger

logger = setup_logger("MultiAgent")


class ExplorerAgent(BaseAgent):
    """Phase 1 agent: broad-spectrum survey.

    Focuses on scanning many genes and consulting literature
    to build a wide initial view of the expression landscape.
    """

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)
        conf = observation.get("hypothesis_confidence", 0)
        budget = observation.get("budget_remaining", 50)

        # Alternate between literature and microarray scans
        if step % 3 == 0:
            logger.info(f"[Explorer] Step {step} | Literature search")
            return 3  # Literature
        else:
            logger.info(f"[Explorer] Step {step} | Microarray scan")
            return 0  # Scan


class ValidatorAgent(BaseAgent):
    """Phase 2 agent: precision validation.

    Takes the Explorer's initial findings and validates them
    with precise qPCR assays and statistical hypothesis refinement.
    """

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)
        conf = observation.get("hypothesis_confidence", 0)
        exp = observation.get("experiments_done", 0)
        cands = observation.get("top_candidate_genes", [])

        # First refine to analyze explorer's data
        if conf < 0.35:
            logger.info(f"[Validator] Step {step} | Refining hypothesis (conf={conf:.2f})")
            return 2

        # Then validate top candidates with precision
        if cands:
            logger.info(f"[Validator] Step {step} | qPCR validation on {cands[0]}")
            return 1

        # Fallback: more scans if no candidates yet
        logger.info(f"[Validator] Step {step} | Additional scan (no candidates)")
        return 0


class TheoristAgent(BaseAgent):
    """Phase 3 agent: knowledge synthesis and submission.

    Combines all experimental evidence into the knowledge graph,
    performs final refinement, and submits when confident.
    """

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)
        conf = observation.get("hypothesis_confidence", 0)
        kg = observation.get("kg_nodes", 0)
        budget = observation.get("budget_remaining", 50)
        cands = observation.get("top_candidate_genes", [])

        # Emergency submit
        if budget <= 2:
            logger.info(f"[Theorist] Step {step} | EMERGENCY submit (budget={budget})")
            return 5

        # Build knowledge graph
        if kg < 4:
            logger.info(f"[Theorist] Step {step} | Building KG (nodes={kg})")
            return 4

        # Final refinement
        if conf < 0.65:
            logger.info(f"[Theorist] Step {step} | Final refinement (conf={conf:.2f})")
            return 2

        # Confident submit
        if conf >= 0.65 and kg >= 3:
            logger.info(f"[Theorist] Step {step} | SUBMIT (conf={conf:.2f}, kg={kg})")
            return 5

        # One more validation if needed
        if cands:
            logger.info(f"[Theorist] Step {step} | Final qPCR on {cands[0]}")
            return 1

        logger.info(f"[Theorist] Step {step} | Refine more")
        return 2


class MultiAgentTeam(BaseAgent):
    """Orchestrator that hands off control between 3 specialized agents.

    Protocol timeline (for max_steps=50):
      Steps  1-15: Explorer  (broad survey)
      Steps 16-35: Validator (precision confirmation)
      Steps 36-50: Theorist  (synthesis + submission)
    """

    def __init__(self, max_steps: int = 50):
        self.explorer = ExplorerAgent()
        self.validator = ValidatorAgent()
        self.theorist = TheoristAgent()
        self.max_steps = max_steps

        # Phase boundaries (percentage of max_steps)
        self.explore_end = int(max_steps * 0.30)   # 30%
        self.validate_end = int(max_steps * 0.70)   # 70%

    def choose_action(self, observation: dict) -> int:
        step = observation.get("step", 0)

        if step <= self.explore_end:
            agent_name = "Explorer"
            action = self.explorer.choose_action(observation)
        elif step <= self.validate_end:
            agent_name = "Validator"
            action = self.validator.choose_action(observation)
        else:
            agent_name = "Theorist"
            action = self.theorist.choose_action(observation)

        logger.info(f"[MultiAgent] Step {step} → {agent_name} selected action {action}")
        return action

    def get_active_agent_name(self, step: int) -> str:
        """Return the name of the currently active sub-agent."""
        if step <= self.explore_end:
            return "Explorer"
        elif step <= self.validate_end:
            return "Validator"
        return "Theorist"

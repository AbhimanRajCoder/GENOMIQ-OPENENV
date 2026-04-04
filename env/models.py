"""
GenomIQ — Enhanced models with real gene expression matrix support.
"""

from pydantic import BaseModel


class Observation(BaseModel):
    """What the agent can see at each step."""

    task_name: str
    domain: str
    step: int
    hypothesis_confidence: float
    experiments_done: int
    last_result: float
    numeric_signal: float
    kg_nodes: int
    unknown_vars: int
    budget_remaining: int
    current_hypothesis: str
    # New: richer gene-level context
    last_gene_tested: str            # e.g. "TP53"
    top_candidate_genes: list[str]   # current best guesses
    literature_hint: str             # last hint from oracle
    signal_strength: float = 0.0     # numeric signal from last experiment


class Action(BaseModel):
    """What the agent can do at each step.

    action_type values:
        0 = run_experiment_A  (cheap microarray scan — noisy, tests random gene)
        1 = run_experiment_B  (precise qPCR — expensive, tests top candidate)
        2 = refine_hypothesis (statistical analysis of accumulated data)
        3 = read_literature   (LLM oracle call — returns partial hint)
        4 = combine_results   (cross-reference experiments in knowledge graph)
        5 = submit_discovery  (end episode, trigger grader)
    """

    action_type: int  # 0–5


class Reward(BaseModel):
    """Normalized reward used by graders."""

    value: float
    reason: str


class StepResult(BaseModel):
    """Result returned by env.step()."""

    observation: Observation
    reward: float
    done: bool
    info: dict

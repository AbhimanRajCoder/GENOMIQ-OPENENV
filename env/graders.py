"""
GenomIQ — Deterministic graders.

The grade() function evaluates an agent's trajectory and final state,
returning a float in [0.0, 1.0].  It is:
  • deterministic  — same inputs always produce the same output
  • non-constant   — scores vary based on actual performance
  • partial-credit — never binary 0/1

Scoring is based on THREE weighted components:
  1. discovery_score (0.50) — gene name overlap between submitted and truth
  2. efficiency_score (0.30) — how early the agent submitted
  3. hypothesis_score (0.20) — final confidence level
"""


def grade(trajectory: list[dict], final_state: dict, task_name: str) -> float:
    """
    Grade an agent's performance on a GenomIQ task.

    Args:
        trajectory: List of step dicts recorded during the episode.
                    Each dict has: step, action, reward, gene_tested (optional).
        final_state: Dict of the environment's full internal state at episode end.
        task_name: One of "single_regulator", "coexpression_cluster", "interaction_effect".

    Returns:
        Float in [0.0, 1.0]. Always clamped. Deterministic and non-constant.
    """

    # ── COMPONENT 1: Discovery Score (weight 0.50) ──────────────────────────
    submitted = set(final_state.get("submitted_candidates", []))
    truth = set(final_state.get("true_targets", []))

    max_possible = len(truth)
    if max_possible == 0:
        gene_match = 0.0
    else:
        overlap = len(submitted & truth)
        gene_match = overlap / max_possible  # 0.0 if no match, 1.0 if perfect

    # Partial credit: if agent tested a true gene during the episode but
    # didn't submit it, award a 0.2 proximity bonus
    genes_tested = set(
        step.get("gene_tested", "")
        for step in trajectory
        if step.get("gene_tested") not in ("—", "", None)
    )
    proximity_bonus = 0.2 if truth & genes_tested else 0.0

    # proximity_bonus only applies if agent didn't already get a full match
    if gene_match == 0.0:
        discovery_score = min(1.0, gene_match + proximity_bonus)
    else:
        discovery_score = min(1.0, gene_match)

    # ── COMPONENT 2: Efficiency Score (weight 0.30) ─────────────────────────
    steps_used = len(trajectory)
    max_steps = final_state.get("max_steps", 50)
    submitted_flag = final_state.get("submitted", False)

    if not submitted_flag:
        # Budget exhausted without submitting — heavy penalty
        efficiency_score = 0.05
    else:
        efficiency_score = max(0.05, 1.0 - (steps_used / max_steps))

    # ── COMPONENT 3: Hypothesis Score (weight 0.20) ─────────────────────────
    final_conf = float(final_state.get("hypothesis_confidence", 0.0))
    hypothesis_score = min(1.0, final_conf)

    # ── FINAL ───────────────────────────────────────────────────────────────
    raw = (discovery_score * 0.50) + (efficiency_score * 0.30) + (hypothesis_score * 0.20)
    return float(max(0.0, min(1.0, raw)))


# ── Validation scenarios ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("GenomIQ Grader — Validation Scenarios")
    print("=" * 60)

    # Scenario A — Perfect discovery, early submit (step 10 of 50)
    score_a = grade(
        trajectory=[{"step": i, "action": 0, "reward": 0, "gene_tested": "X"} for i in range(10)],
        final_state={
            "submitted_candidates": ["MSH2"],
            "true_targets": ["MSH2"],
            "hypothesis_confidence": 0.9,
            "max_steps": 50,
            "submitted": True,
        },
        task_name="single_regulator",
    )
    print(f"Scenario A — Perfect early submit:   {score_a:.3f}  (expected ~0.92)")
    assert 0.85 <= score_a <= 0.98, f"Scenario A failed: {score_a}"

    # Scenario B — Wrong genes submitted, late (step 45 of 50)
    score_b = grade(
        trajectory=[{"step": i, "action": 0, "reward": 0, "gene_tested": "ERK2"} for i in range(45)],
        final_state={
            "submitted_candidates": ["ERK2", "NOTCH1"],
            "true_targets": ["MSH2"],
            "hypothesis_confidence": 1.0,
            "max_steps": 50,
            "submitted": True,
        },
        task_name="single_regulator",
    )
    print(f"Scenario B — Wrong genes, late:      {score_b:.3f}  (expected ~0.23)")
    assert 0.15 <= score_b <= 0.35, f"Scenario B failed: {score_b}"

    # Scenario C — Budget exhausted, no submit
    score_c = grade(
        trajectory=[{"step": i, "action": 0, "reward": 0, "gene_tested": "X"} for i in range(50)],
        final_state={
            "submitted_candidates": [],
            "true_targets": ["MSH2"],
            "hypothesis_confidence": 1.0,
            "max_steps": 50,
            "submitted": False,
        },
        task_name="single_regulator",
    )
    print(f"Scenario C — Budget exhausted:       {score_c:.3f}  (expected ~0.215)")
    assert 0.15 <= score_c <= 0.30, f"Scenario C failed: {score_c}"

    # Scenario D — Wrong genes but DID test true gene
    score_d = grade(
        trajectory=[
            {"step": 0, "action": 0, "reward": 0, "gene_tested": "ERK2"},
            {"step": 1, "action": 0, "reward": 0, "gene_tested": "ERK2"},
            {"step": 2, "action": 0, "reward": 0, "gene_tested": "PARP1"},  # ← hit
        ] + [{"step": i, "action": 0, "reward": 0, "gene_tested": "X"} for i in range(3, 20)],
        final_state={
            "submitted_candidates": ["ERK2"],
            "true_targets": ["PARP1"],
            "hypothesis_confidence": 0.8,
            "max_steps": 50,
            "submitted": True,
        },
        task_name="single_regulator",
    )
    print(f"Scenario D — Wrong but tested truth: {score_d:.3f}  (expected ~0.44)")
    assert 0.35 <= score_d <= 0.55, f"Scenario D failed: {score_d}"

    print()
    print("✅ All 4 validation scenarios passed!")

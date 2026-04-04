"""
GenomIQ — Explainability Engine.

Computes feature-importance breakdowns for gene selections,
providing interpretable reasoning for every discovery decision.
"""

import numpy as np
from collections import Counter


def explain_gene_selection(gene: str, experiment_log: list[dict],
                            kg_data: dict, episodes: list[dict],
                            literature_hints: list[str] | None = None) -> dict:
    """Generate a full explainability breakdown for a gene.

    Args:
        gene: The gene name to explain.
        experiment_log: List of action_history entries across episodes.
        kg_data: Knowledge graph dict with 'nodes' and 'edges'.
        episodes: Full episode list from results JSON.
        literature_hints: Collected literature hint strings.

    Returns:
        Dict with overall_score and factor breakdown.
    """
    if literature_hints is None:
        literature_hints = []

    # ── Factor 1: Signal Strength ──────────────────────────────────────────
    all_signals = []
    gene_signals = []
    for ep in episodes:
        for act in ep.get("action_history", []):
            g = act.get("gene_tested", "")
            conf = act.get("confidence", 0)
            if g and g != "—":
                all_signals.append(conf)
                if g == gene:
                    gene_signals.append(conf)

    if gene_signals and all_signals:
        mean_gene = np.mean(gene_signals)
        mean_all = np.mean(all_signals) if all_signals else 0.5
        std_all = np.std(all_signals) if len(all_signals) > 1 else 1.0
        sigma_above = (mean_gene - mean_all) / max(std_all, 0.01)
        signal_score = min(1.0, max(0.0, 0.5 + sigma_above * 0.15))
        signal_reason = f"Mean confidence {mean_gene:.2f} ({sigma_above:+.1f}σ vs matrix average {mean_all:.2f})"
    else:
        signal_score = 0.0
        signal_reason = "Gene not tested in any episode"

    # ── Factor 2: Test Frequency ───────────────────────────────────────────
    gene_test_count = 0
    total_tests = 0
    for ep in episodes:
        for act in ep.get("action_history", []):
            g = act.get("gene_tested", "")
            if g and g != "—":
                total_tests += 1
                if g == gene:
                    gene_test_count += 1

    freq_score = min(1.0, gene_test_count / max(total_tests * 0.1, 1))
    freq_reason = f"Tested {gene_test_count}× across {len(episodes)} episodes ({gene_test_count/max(total_tests,1)*100:.0f}% of all tests)"

    # ── Factor 3: Literature Support ───────────────────────────────────────
    lit_mentions = sum(1 for h in literature_hints if gene in h)
    lit_score = min(1.0, lit_mentions / max(len(literature_hints) * 0.2, 1))
    lit_reason = f"{lit_mentions} oracle hint(s) reference this gene" if lit_mentions > 0 else "No literature hints mention this gene"

    # ── Factor 4: Knowledge Graph Centrality ───────────────────────────────
    if kg_data and gene in kg_data.get("nodes", []):
        edges = kg_data.get("edges", [])
        connections = sum(1 for e in edges if e.get("source") == gene or e.get("target") == gene)
        total_nodes = max(len(kg_data.get("nodes", [])), 1)
        kg_score = min(1.0, connections / max(total_nodes * 0.3, 1))
        kg_reason = f"Connected to {connections} gene(s) in the knowledge graph"
    else:
        kg_score = 0.0
        connections = 0
        kg_reason = "Not present in knowledge graph"

    # ── Factor 5: Reproducibility ──────────────────────────────────────────
    episodes_with_gene = 0
    episodes_validated = 0
    for ep in episodes:
        gene_in_ep = any(
            act.get("gene_tested") == gene
            for act in ep.get("action_history", [])
        )
        if gene_in_ep:
            episodes_with_gene += 1
            if ep.get("success") and gene in ep.get("submitted_candidates", []):
                episodes_validated += 1

    repro_score = episodes_validated / max(episodes_with_gene, 1)
    repro_reason = f"Validated in {episodes_validated}/{episodes_with_gene} episodes where tested"

    # ── Weighted combination ───────────────────────────────────────────────
    weights = {"signal_strength": 0.30, "test_frequency": 0.15,
               "literature_support": 0.20, "kg_centrality": 0.15,
               "reproducibility": 0.20}
    scores = {"signal_strength": signal_score, "test_frequency": freq_score,
              "literature_support": lit_score, "kg_centrality": kg_score,
              "reproducibility": repro_score}

    overall = sum(scores[k] * weights[k] for k in weights)

    return {
        "gene": gene,
        "overall_score": round(overall, 3),
        "factors": {
            "signal_strength": {"value": round(signal_score, 3), "weight": weights["signal_strength"], "reason": signal_reason},
            "test_frequency": {"value": round(freq_score, 3), "weight": weights["test_frequency"], "reason": freq_reason},
            "literature_support": {"value": round(lit_score, 3), "weight": weights["literature_support"], "reason": lit_reason},
            "kg_centrality": {"value": round(kg_score, 3), "weight": weights["kg_centrality"], "reason": kg_reason},
            "reproducibility": {"value": round(repro_score, 3), "weight": weights["reproducibility"], "reason": repro_reason},
        },
    }


def explain_all_discoveries(episodes: list[dict]) -> list[dict]:
    """Generate explainability for all confirmed gene discoveries."""
    # Collect all confirmed genes
    confirmed = set()
    for ep in episodes:
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            confirmed |= (sub & truth)

    # Collect literature hints
    hints = []
    for ep in episodes:
        hint = ep.get("last_hint", "")
        if hint:
            hints.append(hint)

    # Build aggregate KG
    nodes = set()
    edge_counts = {}
    for ep in episodes:
        for act in ep.get("action_history", []):
            g = act.get("gene_tested", "")
            if g and g != "—":
                nodes.add(g)

    kg_data = {"nodes": list(nodes), "edges": []}

    results = []
    for gene in sorted(confirmed):
        result = explain_gene_selection(gene, [], kg_data, episodes, hints)
        results.append(result)

    return results

"""
GenomIQ — Knowledge Graph & Hypothesis Timeline (Light theme).

Interactive Plotly network diagrams and timeline charts.
"""

import plotly.graph_objects as go
import numpy as np
from collections import defaultdict

# ── Light palette ──────────────────────────────────────────────────────────────

_BG = "rgba(0,0,0,0)"
_PAPER = "rgba(0,0,0,0)"
_GRID = "var(--border-color-primary)"
_TEXT = "var(--body-text-color-subdued)"  # Legible in both light & dark
_MUTED = "var(--body-text-color-subdued)"
_INDIGO = "#6366f1"
_VIOLET = "#8b5cf6"
_SKY = "#0ea5e9"
_GREEN = "#10b981"
_ROSE = "#f43f5e"


def build_knowledge_graph(episodes: list[dict]) -> go.Figure:
    """Build an interactive knowledge graph from episode data.

    Nodes = genes tested. Edges = consecutive co-tests. Node size = test count.
    True targets are highlighted in green.
    """
    node_counts: dict[str, int] = defaultdict(int)
    edge_counts: dict[tuple[str, str], int] = defaultdict(int)
    true_targets: set[str] = set()

    for ep in episodes:
        for g in ep.get("true_targets", []):
            true_targets.add(g)
        actions = ep.get("action_history", [])
        prev_gene = None
        for act in actions:
            gene = act.get("gene_tested", "")
            if gene and gene != "—":
                node_counts[gene] += 1
                if prev_gene and prev_gene != gene:
                    edge_key = tuple(sorted([prev_gene, gene]))
                    edge_counts[edge_key] += 1
                prev_gene = gene

    if not node_counts:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color=_TEXT),
            annotations=[dict(text="Run a simulation to build the knowledge graph",
                              x=0.5, y=0.5, showarrow=False,
                              font=dict(size=14, color=_MUTED))],
            xaxis=dict(visible=False), yaxis=dict(visible=False), height=520,
        )
        return fig

    genes = list(node_counts.keys())
    n = len(genes)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    radius = 1.0
    x_pos = {g: float(radius * np.cos(angles[i])) for i, g in enumerate(genes)}
    y_pos = {g: float(radius * np.sin(angles[i])) for i, g in enumerate(genes)}

    # Edges
    edge_traces = []
    max_ew = max(edge_counts.values()) if edge_counts else 1
    for (g1, g2), weight in edge_counts.items():
        opacity = 0.15 + 0.6 * (weight / max_ew)
        width = 1 + 3 * (weight / max_ew)
        edge_traces.append(go.Scatter(
            x=[x_pos[g1], x_pos[g2], None],
            y=[y_pos[g1], y_pos[g2], None],
            mode="lines",
            line=dict(width=width, color=f"rgba(79, 70, 229, {opacity})"),
            hoverinfo="text",
            text=f"{g1} ↔ {g2} (co-tested {weight}×)",
            showlegend=False,
        ))

    # Nodes
    max_count = max(node_counts.values())
    node_sizes = [14 + 22 * (node_counts[g] / max_count) for g in genes]
    node_colors = [_GREEN if g in true_targets else _INDIGO for g in genes]
    node_borders = [_GREEN if g in true_targets else _GRID for g in genes]

    hover_texts = []
    for g in genes:
        label = "✓ VALIDATED" if g in true_targets else "Candidate"
        hover_texts.append(f"<b>{g}</b><br>Tested {node_counts[g]}×<br>{label}")

    node_trace = go.Scatter(
        x=[x_pos[g] for g in genes],
        y=[y_pos[g] for g in genes],
        mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(width=2, color=node_borders), opacity=0.9),
        text=genes,
        textposition="top center",
        textfont=dict(size=10, color=_TEXT, family="JetBrains Mono, monospace"),
        hoverinfo="text", hovertext=hover_texts, showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_TEXT, size=12),
        title=dict(text="Gene Co-Investigation Network",
                   font=dict(size=15, weight=700)),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=60, b=20),
        height=520, showlegend=False,
        dragmode="pan",
    )
    return fig


def build_hypothesis_timeline(episode: dict) -> go.Figure:
    """Show hypothesis confidence evolution over episode steps."""
    history = episode.get("hypothesis_history", [])
    if not history:
        actions = episode.get("action_history", [])
        if actions:
            history = [{"step": a["step"], "confidence": a.get("confidence", 0),
                        "hypothesis": ""} for a in actions]

    if not history:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color=_TEXT),
            annotations=[dict(text="No hypothesis data available", x=0.5, y=0.5,
                              showarrow=False, font=dict(size=14, color=_MUTED))],
            xaxis=dict(visible=False), yaxis=dict(visible=False), height=400,
        )
        return fig

    steps = [h["step"] for h in history]
    confs = [h["confidence"] for h in history]
    hover_texts = [
        f"Step {h['step']}<br>Confidence: {h['confidence']:.2%}<br>{h.get('hypothesis', '')[:80]}"
        for h in history
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps, y=confs, mode="lines+markers", fill="tozeroy",
        line=dict(color=_VIOLET, width=2.5, shape="spline"),
        marker=dict(size=9, color=_VIOLET, line=dict(width=1.5, color=_BG)),
        fillcolor="rgba(124, 58, 237, 0.06)",
        hoverinfo="text", hovertext=hover_texts,
        name="Confidence",
    ))
    fig.add_hline(
        y=0.7, line_dash="dash", line_color=_INDIGO, line_width=1,
        annotation_text="Submission threshold (0.7)",
        annotation_font_color=_INDIGO, annotation_position="top left",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_TEXT, size=12),
        title=dict(text=f"Hypothesis Evolution — Episode {episode.get('episode', '?')}",
                   font=dict(size=15, weight=700)),
        xaxis=dict(title="Step", gridcolor=_GRID),
        yaxis=dict(title="Confidence", range=[0, 1.05], gridcolor=_GRID),
        margin=dict(l=50, r=30, t=60, b=50),
        height=400, showlegend=False,
    )
    return fig

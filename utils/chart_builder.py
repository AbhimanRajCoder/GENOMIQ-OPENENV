"""
GenomIQ — Plotly chart builders for the Gradio dashboard.

Laboratory Light palette with clean white backgrounds and vivid accent colours.
"""

import plotly.graph_objects as go
import numpy as np

# ── Light palette ──────────────────────────────────────────────────────────────

def _with_alpha(color: str, opacity: float = 0.15) -> str:
    """Add alpha transparency to a hex or rgb color string."""
    if color.startswith("#"):
        h = color.lstrip("#")
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r}, {g}, {b}, {opacity})"
    elif color.startswith("rgb"):
        if "rgba" in color:
            return color
        return color.replace("rgb", "rgba").replace(")", f", {opacity})")
    return color



_BG = "rgba(0,0,0,0)"
_PAPER = "rgba(0,0,0,0)"
_GRID = "var(--border-color-primary)"  # Slate 400 at low opacity
_TEXT = "var(--body-text-color-subdued)"  # Slate 500 (legible in both)
_MUTED = "var(--body-text-color-subdued)"
_INDIGO = "#6366f1"
_VIOLET = "#8b5cf6"
_SKY = "#0ea5e9"
_AMBER = "#f59e0b"
_SUCCESS = "#6366f1"
_FAIL = "var(--border-color-primary)"
_GREEN = "#10b981"
_ROSE = "#f43f5e"

_LAYOUT = dict(
    plot_bgcolor=_BG,
    paper_bgcolor=_PAPER,
    font=dict(family="Inter, sans-serif", color=_TEXT, size=12),
    margin=dict(l=50, r=30, t=60, b=50),
    xaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
    yaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
    height=400,
)


def _base_layout(**overrides) -> dict:
    layout = dict(_LAYOUT)
    layout.update(overrides)
    return layout


# ── Chart 1: Score per Episode ─────────────────────────────────────────────────

def build_score_chart(episodes: list, target_score: float) -> go.Figure:
    eps = [e["episode"] for e in episodes]
    scores = [e["score"] for e in episodes]
    successes = [e.get("success", False) for e in episodes]
    colors = [_INDIGO if s else _FAIL for s in successes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eps, y=scores, mode="lines+markers",
        marker=dict(size=11, color=colors, line=dict(width=1.5, color=_BG)),
        line=dict(color=_MUTED, width=2),
        name="Precision Score",
        hovertemplate="Episode %{x}: %{y:.4f}<extra></extra>",
    ))
    fig.add_hline(
        y=target_score, line_dash="dash", line_color=_INDIGO, line_width=1.5,
        annotation_text=f"Threshold ({target_score})",
        annotation_font_color=_INDIGO,
        annotation_position="top left",
    )
    fig.update_layout(**_base_layout(
        title=dict(text="Discovery Precision per Episode", font=dict(size=15, weight=700)),
        xaxis_title="Episode", yaxis_title="Score",
        yaxis=dict(range=[0, 1.05], gridcolor=_GRID),
        showlegend=False,
    ))
    return fig


# ── Chart 2: Cumulative Reward ─────────────────────────────────────────────────

def build_reward_chart(episodes: list) -> go.Figure:
    eps = [e["episode"] for e in episodes]
    rewards = [e["reward"] for e in episodes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=eps, y=rewards, mode="lines+markers", fill="tozeroy",
        line=dict(color=_INDIGO, width=2.5),
        marker=dict(size=7, color=_INDIGO, line=dict(width=1, color=_BG)),
        fillcolor="rgba(79, 70, 229, 0.08)",
        name="Reward",
        hovertemplate="Episode %{x}: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Reward Signal Trajectory", font=dict(size=15, weight=700)),
        xaxis_title="Episode", yaxis_title="Reward",
        showlegend=False,
    ))
    return fig


# ── Chart 3: Confidence at Submission ──────────────────────────────────────────

def build_confidence_chart(episodes: list) -> go.Figure:
    eps = [str(e["episode"]) for e in episodes]
    confs = [e.get("final_confidence", 0) for e in episodes]
    successes = [e.get("success", False) for e in episodes]
    colors = [_INDIGO if s else _FAIL for s in successes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=eps, y=confs,
        marker=dict(color=colors, line=dict(color=_BG, width=0.5), opacity=0.9,
                     cornerradius=4),
        hovertemplate="Episode %{x}: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Final Hypothesis Confidence", font=dict(size=15, weight=700)),
        xaxis_title="Episode", yaxis_title="Confidence",
        yaxis=dict(range=[0, 1.05], gridcolor=_GRID),
        showlegend=False,
    ))
    return fig


# ── Chart 4: Budget Utilisation ────────────────────────────────────────────────

def build_budget_chart(episodes: list, max_steps: int) -> go.Figure:
    eps = [f"Ep {e['episode']}" for e in episodes]
    steps = [e["steps"] for e in episodes]
    remaining = [max_steps - e["steps"] for e in episodes]
    successes = [e.get("success", False) for e in episodes]
    bar_colors = [_INDIGO if s else _MUTED for s in successes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=eps, x=steps, orientation="h",
        marker=dict(color=bar_colors, opacity=0.85, cornerradius=3),
        name="Steps Used",
        hovertemplate="%{x} steps<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=eps, x=remaining, orientation="h",
        marker=dict(color="var(--background-fill-secondary)", line=dict(color=_GRID, width=1), cornerradius=3),
        name="Remaining",
        hovertemplate="%{x} remaining<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Resource Allocation", font=dict(size=15, weight=700)),
        xaxis_title="Steps", barmode="stack",
        yaxis=dict(autorange="reversed"),
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
    ))
    return fig


# ── Chart 5: Action Distribution Pie ──────────────────────────────────────────

def build_action_pie(episodes: list) -> go.Figure:
    action_names = ["Microarray", "qPCR", "Refine", "Literature", "Combine", "Submit"]
    action_colors = [_SKY, _VIOLET, _AMBER, _INDIGO, _MUTED, _GREEN]
    counts = [0] * 6

    for ep in episodes:
        for act in ep.get("action_history", []):
            a = act.get("action", 0)
            if 0 <= a <= 5:
                counts[a] += 1

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=action_names, values=counts,
        marker=dict(colors=action_colors, line=dict(color=_BG, width=2)),
        textinfo="percent+label", hoverinfo="label+value", hole=0.5,
        textfont=dict(size=11),
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Protocol Action Distribution", font=dict(size=15, weight=700)),
        showlegend=False,
    ))
    return fig


# ── Chart 6: Reward Heatmap ───────────────────────────────────────────────────

def build_reward_heatmap(episodes: list, max_steps: int) -> go.Figure:
    n_eps = len(episodes)
    matrix = np.full((n_eps, max_steps), np.nan)

    for i, ep in enumerate(episodes):
        for act in ep.get("action_history", []):
            step_idx = act.get("step", 1) - 1
            if 0 <= step_idx < max_steps:
                matrix[i, step_idx] = act.get("reward", 0)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=matrix,
        x=list(range(1, max_steps + 1)),
        y=[f"Ep {e['episode']}" for e in episodes],
        colorscale=[
            [0.0, "#fecaca"],
            [0.3, "#fef3c7"],
            [0.5, "var(--background-fill-secondary)"],
            [0.7, "#c7d2fe"],
            [1.0, "#4f46e5"],
        ],
        zmid=0,
        hovertemplate="Step %{x}, Episode %{y}: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Signal", tickfont=dict(color=_TEXT)),
    ))
    fig.update_layout(**_base_layout(
        title=dict(text="Temporal Reward Gradient", font=dict(size=15, weight=700)),
        xaxis_title="Step",
        yaxis=dict(autorange="reversed"),
    ))
    return fig


# ── Chart 7: Single Episode Confidence Trajectory ─────────────────────────────

def build_confidence_trajectory(episode: dict) -> go.Figure:
    history = episode.get("action_history", [])
    if not history:
        fig = go.Figure()
        fig.update_layout(**_base_layout(title="Awaiting data..."))
        return fig

    steps = [a["step"] for a in history]
    confs = [a.get("confidence", 0) for a in history]
    actions = [a.get("action", 0) for a in history]

    action_colors_map = {
        0: _SKY, 1: _VIOLET, 2: _AMBER, 3: _INDIGO, 4: _MUTED, 5: _GREEN
    }
    action_labels = {
        0: "SCAN", 1: "qPCR", 2: "REFINE", 3: "LIT", 4: "SYNTH", 5: "SUBMIT"
    }
    dot_colors = [action_colors_map.get(a, _MUTED) for a in actions]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps, y=confs, mode="lines+markers",
        line=dict(color=_MUTED, width=2, shape="spline"),
        marker=dict(size=10, color=dot_colors, line=dict(width=1.5, color=_BG)),
        name="Confidence",
        hovertemplate="Step %{x}: %{y:.2f}<extra></extra>",
    ))

    for a in history:
        if a.get("action") == 5:
            fig.add_vline(
                x=a["step"], line_dash="solid", line_color=_GREEN, line_width=1.5,
                annotation_text="SUBMIT",
                annotation_font_color=_GREEN,
                annotation_position="top left",
            )

    fig.update_layout(**_base_layout(
        title=dict(text=f"Episode {episode.get('episode', '?')} — Confidence", font=dict(size=15, weight=700)),
        xaxis_title="Step", yaxis_title="Confidence",
        yaxis=dict(range=[0, 1.05], gridcolor=_GRID),
        showlegend=False,
    ))
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

_AGENT_COLORS = {"random": _MUTED, "greedy": _INDIGO, "ppo": _VIOLET, "multi_agent": _SKY}


def build_benchmark_chart(results: dict) -> go.Figure:
    """Grouped bar chart comparing agent performance across metrics."""
    agents = list(results.keys())
    colors = [_AGENT_COLORS.get(a, _AMBER) for a in agents]

    fig = go.Figure()
    metrics = [
        ("Avg Score", [results[a]["avg_score"] for a in agents]),
        ("Success Rate", [results[a]["success_rate"] for a in agents]),
    ]

    bar_colors = [_INDIGO, _GREEN]
    for i, (name, vals) in enumerate(metrics):
        fig.add_trace(go.Bar(
            x=agents, y=vals, name=name,
            marker_color=bar_colors[i],
            marker_line_width=0,
            text=[f"{v:.2f}" for v in vals],
            textposition="outside",
            textfont=dict(size=12, color=_TEXT),
        ))

    fig.update_layout(**_base_layout(
        title=dict(text="Agent Performance Comparison", font=dict(size=16, weight=700)),
        barmode="group", yaxis=dict(range=[0, 1.15], gridcolor=_GRID),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        height=420,
    ))
    return fig


def build_benchmark_radar(results: dict) -> go.Figure:
    """Radar chart with multi-dimensional agent comparison."""
    categories = ["Score", "Success Rate", "Efficiency", "Consistency"]
    fig = go.Figure()

    for agent, data in results.items():
        scores = data.get("scores", [])
        consistency = 1.0 - (np.std(scores) if len(scores) > 1 else 0.5)
        max_steps = max(data.get("avg_steps", 50), 1)
        efficiency = max(0, 1.0 - data["avg_steps"] / 50)

        values = [data["avg_score"], data["success_rate"], efficiency, max(0, consistency)]
        values.append(values[0])  # close the polygon

        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories + [categories[0]],
            fill="toself", name=agent.capitalize(),
            line=dict(color=_AGENT_COLORS.get(agent, _AMBER), width=2),
            fillcolor=_with_alpha(_AGENT_COLORS.get(agent, _AMBER), 0.15),
        ))

    fig.update_layout(**_base_layout(
        title=dict(text="Agent Capability Radar", font=dict(size=16, weight=700)),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=_GRID),
            bgcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
        height=420,
    ))
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLAINABILITY CHART
# ═══════════════════════════════════════════════════════════════════════════════

_FACTOR_COLORS = {
    "signal_strength": _INDIGO,
    "test_frequency": _SKY,
    "literature_support": _VIOLET,
    "kg_centrality": _AMBER,
    "reproducibility": _GREEN,
}

_FACTOR_LABELS = {
    "signal_strength": "Signal",
    "test_frequency": "Frequency",
    "literature_support": "Literature",
    "kg_centrality": "KG Centrality",
    "reproducibility": "Reproducibility",
}


def build_explainability_chart(explanations: list[dict]) -> go.Figure:
    """Horizontal stacked bar chart showing factor breakdown per gene."""
    if not explanations:
        fig = go.Figure()
        fig.update_layout(**_base_layout(
            annotations=[dict(text="No explainability data", x=0.5, y=0.5,
                              showarrow=False, font=dict(size=14, color=_MUTED))],
            xaxis=dict(visible=False), yaxis=dict(visible=False), height=300,
        ))
        return fig

    genes = [e["gene"] for e in explanations]
    factor_names = list(_FACTOR_COLORS.keys())

    fig = go.Figure()
    for factor in factor_names:
        vals = []
        for e in explanations:
            f = e.get("factors", {}).get(factor, {})
            vals.append(f.get("value", 0) * f.get("weight", 0.2) * 5)  # Scale for visibility
        fig.add_trace(go.Bar(
            y=genes, x=vals, name=_FACTOR_LABELS[factor],
            orientation="h",
            marker_color=_FACTOR_COLORS[factor],
            marker_line_width=0,
            hovertemplate="%{y}: %{x:.2f}<extra>" + _FACTOR_LABELS[factor] + "</extra>",
        ))

    fig.update_layout(**_base_layout(
        title=dict(text="Gene Selection — Factor Breakdown", font=dict(size=16, weight=700)),
        barmode="stack",
        xaxis_title="Weighted Score",
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        height=max(300, len(genes) * 50 + 100),
    ))
    return fig

"""
GenomIQ — Scientific Discovery Lab Dashboard (Gradio)

Professional light-theme research dashboard with:
  - AI Scientist Guidance Layer (recommended actions, warnings)
  - Episode Cycle (narrative timeline of agent journey)
  - Interactive Knowledge Graph with filters
  - All 6 research domains, dataset/objective/constraint/prior controls
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import gradio as gr
import pandas as pd
import yaml

from app_theme import GenomIQTheme
from utils.report_generator import (
    generate_report, generate_discovery_card_html, generate_missed_card_html,
    GENE_BIOLOGY, generate_paper_hypothesis, generate_discovery_card_v2_html,
    build_action_notes,
)
from utils.chart_builder import (build_score_chart, build_reward_chart, build_confidence_chart,
                                  build_budget_chart, build_action_pie, build_reward_heatmap,
                                  build_confidence_trajectory, build_benchmark_chart,
                                  build_benchmark_radar, build_explainability_chart)
from utils.knowledge_graph import build_knowledge_graph, build_hypothesis_timeline
from utils.explainability import explain_all_discoveries, explain_gene_selection
from utils.scientist_chat import ask_scientist, SUGGESTED_QUESTIONS
from utils.benchmarker import run_benchmark_sync
from utils.experiment_panels import (
    build_metrics_bar, build_rl_state_panel, build_progress_html,
    build_thinking_html, build_run_summary_html, build_loading_html,
    build_trace_html,
)

# ── Constants ─────────────────────────────────────────────────────────────────

RESULTS_PATH = "results/latest_run.json"
CONFIG_PATH = "config.yaml"
LOG_PATH = "logs/genomiq.log"

# ── CSS ───────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.gradio-container { max-width: 1440px !important; font-family: 'Inter', sans-serif !important; }

/* Smooth transitions everywhere */
.gradio-container * { transition: all 0.2s ease; }

/* Button hover lift */
button.primary {
    box-shadow: 0 1px 3px rgba(79,70,229,0.2) !important;
}
button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(79,70,229,0.25) !important;
}

/* Tab styling */
.tab-nav button { font-weight: 600 !important; letter-spacing: 0.02em !important; }
.tab-nav button.selected {
    border-bottom: 2.5px solid #4f46e5 !important;
    color: #4f46e5 !important;
}

/* Card hover effects */
.card-hover:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.08); }

/* Accordion styling */
.accordion { border: 1px solid var(--border-color-primary) !important; border-radius: 8px !important; }

/* DataFrame styling */
table { border-radius: 8px !important; overflow: hidden !important; }
thead th { background: var(--background-fill-secondary) !important; color: var(--body-text-color) !important; font-weight: 600 !important; }

/* Subtle pulse animation for live indicators */
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.live-dot { animation: pulse 2s infinite; }

/* Shimmer skeleton loading effect */
@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
.shimmer-loading {
  background: linear-gradient(90deg, var(--background-fill-secondary) 25%, var(--border-color-primary) 50%, var(--background-fill-secondary) 75%) !important;
  background-size: 800px 100% !important;
  animation: shimmer 1.5s infinite linear !important;
}

/* Spinner animation */
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.spinner {
  width: 20px; height: 20px;
  border: 2.5px solid var(--border-color-primary);
  border-top: 2.5px solid #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* Glow pulse for active simulation */
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(99,102,241,0.2); }
  50% { box-shadow: 0 0 20px rgba(99,102,241,0.4); }
}
.sim-active { animation: glow-pulse 2s ease-in-out infinite; }

/* Progress bar animation */
@keyframes progress-stripe {
  0% { background-position: 0 0; }
  100% { background-position: 40px 0; }
}
.progress-animated {
  background-image: linear-gradient(
    45deg, rgba(255,255,255,0.15) 25%, transparent 25%,
    transparent 50%, rgba(255,255,255,0.15) 50%,
    rgba(255,255,255,0.15) 75%, transparent 75%, transparent
  ) !important;
  background-size: 40px 40px !important;
  animation: progress-stripe 1s linear infinite !important;
}
/* Research Terminal Log Styling */
.research-log-container {
  background: var(--background-fill-secondary);
  border: 1px solid var(--border-color-primary);
  border-radius: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11.5px;
  line-height: 1.6;
  height: 380px;
  overflow-y: auto;
  padding: 16px;
  color: var(--body-text-color);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}
.research-log-container::-webkit-scrollbar { width: 6px; }
.research-log-container::-webkit-scrollbar-thumb { background: var(--border-color-primary); border-radius: 10px; }

.log-entry { margin-bottom: 6px; border-left: 2px solid transparent; padding-left: 10px; }
.log-entry.success { border-left-color: #10b981; color: #065f46; background: rgba(16,185,129,0.03); }
.log-entry.failed { border-left-color: #ef4444; color: #991b1b; background: rgba(239,68,68,0.03); }
.log-entry.episode { border-bottom: 1px solid var(--border-color-primary); padding: 12px 0 6px; margin: 12px 0 8px; font-weight: 700; color: #6366f1; }
.log-entry.action { color: #8b5cf6; }

.log-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
  margin-right: 8px;
  letter-spacing: 0.5px;
}
.badge-step { background: var(--border-color-primary); color: var(--body-text-color-subdued); }
.badge-hit { background: #dcfce7; color: #166534; }
.badge-miss { background: #fee2e2; color: #991b1b; }
.badge-submit { background: #eef2ff; color: #4338ca; }
.badge-error { background: #fef2f2; color: #991b1b; border: 1px solid #fee2e2; }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_results() -> dict | None:
    try:
        with open(RESULTS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


def save_config(domain, difficulty, agent, episodes, max_steps, seed,
                use_oracle, disc_bonus, step_pen, exp_pen, ref_bonus,
                objective, dataset_source,
                noise_level, cost_tier, time_limit,
                seed_genes, known_assoc, lit_hints):
    cost_map = {"Low Fidelity (Cheap)": "low_fidelity",
                "High Fidelity (Expensive)": "high_fidelity", "Mixed": "mixed"}
    ds_map = {"Synthetic (Generated)": "synthetic",
              "Cancer Gene Expression (Preloaded)": "preloaded",
              "Rare Disease Panel (Preloaded)": "preloaded",
              "Custom Upload (CSV)": "custom",
              "TCGA-BRCA (Real-World)": "tcga",
              "GEO Lung (Real-World)": "geo"}
    ds_name_map = {"Cancer Gene Expression (Preloaded)": "cancer_gene_expression",
                   "Rare Disease Panel (Preloaded)": "rare_disease_panel",
                   "TCGA-BRCA (Real-World)": "tcga_brca",
                   "GEO Lung (Real-World)": "geo_lung"}

    parsed_seeds = [g.strip() for g in seed_genes.split(",") if g.strip()] if seed_genes else []
    parsed_assoc = [a.strip() for a in known_assoc.split(",") if a.strip()] if known_assoc else []
    parsed_hints = [h.strip() for h in lit_hints.split(";") if h.strip()] if lit_hints else []

    cfg = {
        "agent": {"exploration": "epsilon_greedy", "learning_rate": 0.0003,
                  "type": agent, "use_claude_oracle": use_oracle},
        "rewards": {"discovery_bonus": float(disc_bonus),
                    "hypothesis_improvement_bonus": float(ref_bonus),
                    "step_penalty": float(step_pen),
                    "useless_experiment_penalty": float(exp_pen)},
        "scenario": {"difficulty": difficulty, "domain": domain, "objective": objective,
                     "max_steps": int(max_steps), "num_episodes": int(episodes), "seed": int(seed)},
        "constraints": {"noise_level": float(noise_level),
                        "cost_tier": cost_map.get(cost_tier, "mixed"),
                        "time_limit": int(time_limit)},
        "prior_knowledge": {"seed_genes": parsed_seeds, "associations": parsed_assoc,
                            "literature_hints": parsed_hints},
        "dataset": {"source": ds_map.get(dataset_source, "synthetic"),
                    "name": ds_name_map.get(dataset_source, "")},
        "visualization": {"persistence_path": RESULTS_PATH, "real_time_charts": True, "theme": "light"},
    }
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=True)
    return cfg


def _no_data_html():
    return """
    <div style="text-align:center;padding:60px;color:var(--body-text-color-subdued);font-family:'Inter',sans-serif;">
        <div style="font-size:48px;margin-bottom:16px;opacity:0.3;">◇</div>
        <h3 style="color:var(--body-text-color);font-weight:600;margin:0 0 8px;">No Results Available</h3>
        <p style="margin:0;font-size:14px;">Run a simulation in the <strong>Experiment</strong> tab to generate data.</p>
    </div>
    """


def _target_score(difficulty: str) -> float:
    return {"easy": 0.80, "medium": 0.65, "hard": 0.50}.get(difficulty, 0.65)


# ═══════════════════════════════════════════════════════════════════════════════
# AI SCIENTIST GUIDANCE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def generate_guidance_html(data: dict | None) -> str:
    """Generate AI scientist recommendations based on latest results."""
    if not data:
        return """
        <div style="background:var(--background-fill-secondary);border:1px solid var(--border-color-primary);border-radius:12px;padding:24px;
                    font-family:'Inter',sans-serif;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
                <div style="width:8px;height:8px;border-radius:50%;background:var(--body-text-color-subdued);"></div>
                <span style="font-size:13px;font-weight:600;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
                    AI Scientist — Awaiting Data
                </span>
            </div>
            <p style="color:var(--body-text-color-subdued);font-size:14px;margin:0;">
                Initialize a simulation to receive guided recommendations.
            </p>
        </div>
        """

    episodes = data.get("episodes", [])
    metrics = data.get("metrics", {})
    meta = data.get("run_metadata", {})

    success_rate = metrics.get("success_rate", 0)
    avg_score = metrics.get("avg_score", 0)
    avg_steps = metrics.get("avg_steps", 50)
    max_steps = meta.get("max_steps", 50)

    # Collect gene testing frequency
    gene_freq: dict[str, int] = {}
    true_targets: set[str] = set()
    for ep in episodes:
        for g in ep.get("true_targets", []):
            true_targets.add(g)
        for act in ep.get("action_history", []):
            gene = act.get("gene_tested", "")
            if gene and gene != "—":
                gene_freq[gene] = gene_freq.get(gene, 0) + 1

    # Sort by frequency, find untested targets
    sorted_genes = sorted(gene_freq.items(), key=lambda x: -x[1])
    hot_genes = sorted_genes[:5]
    missed_targets = true_targets - set(gene_freq.keys())

    # Build recommendations
    recs = []

    # 1. Success rate guidance
    if success_rate < 0.3:
        recs.append(("critical", "Low Discovery Rate",
                     f"Only {success_rate:.0%} of episodes succeeded. Consider switching to <b>easy</b> difficulty or enabling the <b>LLM Oracle</b> for literature guidance."))
    elif success_rate < 0.6:
        recs.append(("warning", "Moderate Performance",
                     f"Success rate is {success_rate:.0%}. Try increasing the <b>episode budget</b> or providing <b>seed genes</b> to bias initial exploration."))
    else:
        recs.append(("success", "Strong Discovery Rate",
                     f"Excellent {success_rate:.0%} success rate. The agent is performing well in this configuration."))

    # 2. Efficiency guidance
    efficiency = 1 - (avg_steps / max(max_steps, 1))
    if efficiency < 0.2:
        recs.append(("warning", "Diminishing Returns Detected",
                     f"Agent uses {avg_steps:.0f}/{max_steps} steps on average ({efficiency:.0%} efficiency). Most discoveries happen in the first 60% of steps — consider reducing max budget."))

    # 3. High-value gene recommendations
    if hot_genes:
        gene_chips = " ".join(
            f'<span style="background:{"#dcfce7" if g in true_targets else "var(--background-fill-secondary)"};'
            f'color:{"#166534" if g in true_targets else "var(--body-text-color)"};'
            f'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:500;'
            f'font-family:JetBrains Mono,monospace;">{g} ({c}×)</span>'
            for g, c in hot_genes
        )
        recs.append(("info", "Most Investigated Genes", gene_chips))

    # 4. Missed targets
    if missed_targets:
        missed_chips = " ".join(
            f'<span style="background:#fef2f2;color:#991b1b;padding:3px 10px;border-radius:12px;'
            f'font-size:12px;font-weight:500;font-family:JetBrains Mono,monospace;">{g}</span>'
            for g in list(missed_targets)[:5]
        )
        recs.append(("critical", "Untested True Targets",
                     f"These target genes were never tested: {missed_chips}. Add them as <b>seed genes</b> in Prior Knowledge."))

    # 5. Next experiment suggestion
    if avg_score < 0.5:
        recs.append(("info", "Recommended Next Experiment",
                     "Switch to <b>qPCR-heavy strategy</b> (high-fidelity cost tier) to improve signal precision on candidate genes."))

    # Build HTML
    icon_map = {
        "critical": ("●", "#ef4444", "#fef2f2", "#991b1b"),
        "warning": ("◆", "#f59e0b", "#fffbeb", "#92400e"),
        "success": ("●", "#059669", "#ecfdf5", "#065f46"),
        "info": ("◇", "#4f46e5", "#eef2ff", "#3730a3"),
    }

    cards = ""
    for level, title, body in recs:
        icon, dot_color, bg_light, text_light = icon_map[level]
        # Use a semi-transparent version for theme compatibility
        bg = f"{dot_color}10" 
        cards += f"""
        <div style="background:{bg};border:1px solid {dot_color}25;border-radius:10px;
                    padding:16px 20px;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span style="color:{dot_color};font-size:10px;">{icon}</span>
                <span style="font-size:13px;font-weight:600;color:{dot_color};">{title}</span>
            </div>
            <div style="font-size:13px;color:var(--body-text-color-subdued);line-height:1.6;">{body}</div>
        </div>
        """

    return f"""
    <div style="font-family:'Inter',sans-serif;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
            <div style="width:8px;height:8px;border-radius:50%;background:#4f46e5;"
                 class="live-dot"></div>
            <span style="font-size:13px;font-weight:600;color:#4f46e5;text-transform:uppercase;letter-spacing:1px;">
                AI Scientist Guidance
            </span>
        </div>
        {cards}
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# EPISODE CYCLE — Narrative Timeline
# ═══════════════════════════════════════════════════════════════════════════════

def generate_story_html(data: dict | None, ep_idx: int = 0) -> str:
    """Generate a narrative timeline for a specific episode."""
    if not data:
        return _no_data_html()

    episodes = data.get("episodes", [])
    if ep_idx < 0 or ep_idx >= len(episodes):
        return _no_data_html()

    ep = episodes[ep_idx]
    actions = ep.get("action_history", [])
    true_targets = set(ep.get("true_targets", []))
    success = ep.get("success", False)
    score = ep.get("score", 0)

    action_labels = {0: "Microarray Scan", 1: "qPCR Validation", 2: "Hypothesis Refinement",
                     3: "Literature Review", 4: "Data Synthesis", 5: "Discovery Submission"}
    action_icons = {0: "🔬", 1: "🧬", 2: "💡", 3: "📄", 4: "🔗", 5: "📋"}

    # Build narrative phases
    phases = []
    conf_prev = 0.1

    for act in actions:
        step = act.get("step", 0)
        a_type = act.get("action", 0)
        gene = act.get("gene_tested", "—")
        conf = act.get("confidence", 0)
        reward = act.get("reward", 0)

        # Determine narrative phase
        if conf < 0.3:
            phase_label = "Exploration"
            phase_color = "#0284c7"
        elif conf < 0.6:
            phase_label = "Investigation"
            phase_color = "#7c3aed"
        elif conf < 0.8:
            phase_label = "Validation"
            phase_color = "#059669"
        else:
            phase_label = "Confirmation"
            phase_color = "#4f46e5"

        # Build event text
        is_hit = gene in true_targets
        reasoning = ""
        reward_expl = ""
        
        # Base reasoning on confidence and exploration vs exploitation
        if conf < 0.3:
            reasoning = "Agent exploring search space due to low confidence."
        elif conf < 0.7:
            reasoning = "Agent investigating promising candidate to build confidence."
        else:
            reasoning = "Agent validating strong candidate before final submission."

        if a_type == 0:
            if is_hit:
                narrative = f"Scanned <b>{gene}</b> — <span style='color:#059669;font-weight:600;'>Strong signal detected!</span> This gene shows differential expression.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: {reasoning}</span>"
                reward_expl = f"Positive reward (+{reward:.1f}) for identifying a true target via scan."
            else:
                narrative = f"Scanned <b>{gene}</b> — Weak signal. No significant differential expression observed.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: {reasoning}</span>"
                reward_expl = f"Small penalty ({reward:.1f}) for scanning a non-target to discourage random guessing."
        elif a_type == 1:
            if is_hit:
                narrative = f"qPCR validated <b>{gene}</b> — <span style='color:#059669;font-weight:600;'>Confirmed upregulation.</span> Confidence increased to {conf:.0%}.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: High-fidelity validation requested to confirm signal.</span>"
                reward_expl = f"High positive reward (+{reward:.1f}) for successfully validating a true target."
            else:
                narrative = f"qPCR on <b>{gene}</b> — Expression levels within normal range. Marginal confidence increase.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Attempted validation, but target did not show conclusive evidence.</span>"
                reward_expl = f"Significant penalty ({reward:.1f}) for wasting expensive qPCR resources on a non-target."
        elif a_type == 2:
            if conf > conf_prev:
                narrative = f"Refined hypothesis based on accumulated evidence. Confidence: {conf_prev:.0%} → <b>{conf:.0%}</b>.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Agent synthesized recent findings to update internal target probabilities.</span>"
                reward_expl = f"Reward (+{reward:.1f}) for successfully increasing overall hypothesis confidence."
            else:
                narrative = f"Attempted hypothesis refinement. Insufficient new evidence — confidence unchanged at {conf:.0%}.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Forced model update despite lacking new actionable data.</span>"
                reward_expl = f"Penalty ({reward:.1f}) for redundant processing step without new information."
        elif a_type == 3:
            narrative = f"Reviewed literature for related gene networks. Search space narrowed.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Consulted Oracle to map known associations for current candidate pool.</span>"
            reward_expl = f"Small reward (+{reward:.1f}) for gaining external structural priors."
        elif a_type == 4:
            narrative = f"Synthesized experimental data into knowledge graph. Network connections updated.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Integrating disconnected findings into a unified model.</span>"
            reward_expl = f"Structural reward (+{reward:.1f}) based on increased graph density and connectivity."
        elif a_type == 5:
            if success:
                narrative = f"<span style='color:#059669;font-weight:700;'>Submitted discovery with {conf:.0%} confidence — VALIDATED!</span><br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Confidence threshold met, finalizing episode.</span>"
                reward_expl = f"Massive terminal reward (+{reward:.1f}) for successful final discovery."
            else:
                narrative = f"Submitted discovery with {conf:.0%} confidence — did not meet validation threshold.<br><span style='font-size:11px;color:var(--body-text-color-subdued);'><em>Reasoning</em>: Premature submission or incorrect target selected.</span>"
                reward_expl = f"Terminal penalty ({reward:.1f}) for failing validation."
        else:
            narrative = f"Action {a_type} executed."
            reward_expl = f"Reward delta: {reward:.1f}"

        # Append reward explanation to narrative
        narrative += f"<br><span style='font-size:11px;color:#8b5cf6;'><em>Reward Signal</em>: {reward_expl}</span>"

        phases.append((step, phase_label, phase_color, action_labels.get(a_type, "Unknown"),
                       action_icons.get(a_type, "·"), narrative, reward, conf))
        conf_prev = conf

    # Build timeline HTML
    timeline_items = ""
    for i, (step, phase, pcolor, alabel, icon, narrative, reward, conf) in enumerate(phases):
        is_last = i == len(phases) - 1
        reward_badge = f'<span style="color:{"#059669" if reward > 0 else "#ef4444"};font-size:11px;font-weight:500;">{"+" if reward > 0 else ""}{reward:.1f}</span>'

        timeline_items += f"""
        <div style="display:flex;gap:16px;position:relative;">
            <div style="display:flex;flex-direction:column;align-items:center;min-width:40px;">
                <div style="width:32px;height:32px;background:{pcolor};border-radius:50%;
                            display:flex;align-items:center;justify-content:center;
                            font-size:14px;color:white;font-weight:700;z-index:1;
                            box-shadow:0 2px 8px {pcolor}30;">
                    {step}
                </div>
                {"" if is_last else f'<div style="width:2px;flex:1;background:linear-gradient(to bottom, {pcolor}40, var(--border-color-primary));margin:4px 0;min-height:20px;"></div>'}
            </div>
            <div style="flex:1;padding-bottom:{"0" if is_last else "20"}px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:600;color:{pcolor};text-transform:uppercase;letter-spacing:0.5px;">
                        {phase}
                    </span>
                    <span style="font-size:11px;color:var(--body-text-color-subdued);">•</span>
                    <span style="font-size:12px;color:var(--body-text-color-subdued);">{alabel}</span>
                    <span style="margin-left:auto;">{reward_badge}</span>
                </div>
                <div style="font-size:13px;color:var(--body-text-color);line-height:1.6;">
                    {narrative}
                </div>
            </div>
        </div>
        """

    # Outcome banner
    if success:
        outcome_bg = "#ecfdf5"
        outcome_border = "#059669"
        outcome_text = f"Discovery Validated — Score: {score:.4f}"
        outcome_color = "#065f46"
    else:
        outcome_bg = "#fef2f2"
        outcome_border = "#ef4444"
        outcome_text = f"Discovery Not Validated — Score: {score:.4f}"
        outcome_color = "#991b1b"

    targets_str = ", ".join(true_targets) if true_targets else "—"

    return f"""
    <div style="font-family:'Inter',sans-serif;">
        <div style="background:var(--background-fill-secondary);border:1px solid var(--border-color-primary);border-radius:12px;padding:20px 24px;margin-bottom:20px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h3 style="margin:0;font-size:18px;font-weight:700;color:#6366f1;">
                        Episode {ep.get('episode', '?')} — Discovery Narrative
                    </h3>
                    <p style="margin:4px 0 0;font-size:13px;color:var(--body-text-color-subdued);">
                        Target genes: <span style="font-family:'JetBrains Mono',monospace;color:#6366f1;">{targets_str}</span>
                        · {len(actions)} steps · Final confidence: {ep.get('final_confidence', 0):.0%}
                    </p>
                </div>
                <div style="background:{outcome_bg}20;border:1px solid {outcome_border}40;
                            border-radius:8px;padding:8px 16px;">
                    <span style="font-size:13px;font-weight:600;color:{outcome_border};">{outcome_text}</span>
                </div>
            </div>
        </div>
        <div style="padding:0 8px;">
            {timeline_items}
        </div>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: RUN EXPERIMENT
# ═══════════════════════════════════════════════════════════════════════════════

def run_simulation(domain, difficulty, agent, episodes, max_steps,
                   seed, use_oracle, disc_bonus, step_pen, exp_pen, ref_bonus,
                   objective, dataset_source,
                   noise_level, cost_tier, time_limit,
                   seed_genes, known_assoc, lit_hints):
    import re

    save_config(domain, difficulty, agent, int(episodes), int(max_steps),
                int(seed), use_oracle, disc_bonus, step_pen, exp_pen, ref_bonus,
                objective, dataset_source, noise_level, cost_tier, int(time_limit),
                seed_genes, known_assoc, lit_hints)

    ms = int(max_steps)
    total_eps = int(episodes)

    # ── Tracking state ──
    step_num, conf_val, conf_prev, exp_count = 0, 0.0, 0.0, 0
    cum_reward, cur_reward = 0.0, 0.0
    explore_n, exploit_n = 0, 0
    ep_num = 0
    genes_studied = set()
    kg_nodes = 0
    cur_action = "—"
    cur_gene = "—"
    cur_hit = None
    hypothesis = "No hypothesis formed"
    candidates = []
    thinking_msg = "Initializing simulation environment..."

    # ── Initial trace ──
    trace = f"{'─' * 60}\n"
    trace += f"  GenomIQ Simulation — {domain} | {difficulty} | {agent}\n"
    trace += f"  Objective: {objective}\n"
    trace += f"  Dataset: {dataset_source} | Noise σ={noise_level}\n"
    header_html = f"""
    <div style="font-family:Inter,sans-serif;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border-color-primary);">
      <div style="font-size:14px;font-weight:700;color:var(--body-text-color);">{domain.replace('_',' ').title()} Research Simulation</div>
      <div style="font-size:11px;color:var(--body-text-color-subdued);">
        Agent: <span style="color:#6366f1;font-weight:600;">{agent}</span> &middot; 
        Difficulty: <span style="color:#6366f1;font-weight:600;">{difficulty}</span> &middot; 
        Seed: {int(seed)}
      </div>
    </div>"""
    
    trace_entries = []

    # Initial yield — show loading state
    loading = build_loading_html(domain, agent, total_eps, ms, phase="init")
    yield (build_trace_html(trace_entries, header_html),
           build_run_summary_html(None),
           build_metrics_bar(0, ms, 0, 0, 0, 50),
           loading,
           build_progress_html(0, ms, 0, total_eps),
           generate_guidance_html(None),
           gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
           *([None]*7),
           gr.update(maximum=total_eps, value=1), gr.update(maximum=total_eps, value=1))

    proc = subprocess.Popen(
        [sys.executable, "runner.py"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd(),
    )

    start_time = time.time()

    # Regex patterns for parsing
    step_re = re.compile(r'STEP\s+(\d+)\s*\|')
    action_re = re.compile(r'\|\s*(.+?)\s*→')
    gene_re = re.compile(r'gene=(\w+)')
    hit_re = re.compile(r'hit=(True|False)')
    conf_re = re.compile(r'conf\s+([\d.]+)→([\d.]+)')
    reward_re = re.compile(r'reward=([\d.-]+)')
    ep_start_re = re.compile(r'EPISODE\s+(\d+)/(\d+)\s*—\s*START')
    ep_result_re = re.compile(r'EPISODE\s+(\d+)\s+RESULT.*Steps=(\d+).*Reward=([\d.-]+).*Score=([\d.]+)')
    top_re = re.compile(r'Top:\s*\[([^\]]+)\]')
    kg_re = re.compile(r'kg_nodes\s+(\d+)→(\d+)')

    try:
        for line in iter(proc.stdout.readline, ""):
            if time.time() - start_time > 300:
                proc.kill()
                error_html = '<div class="log-entry failed"><span class="log-badge badge-miss">ERROR</span> Simulation timed out (300s).</div>'
                trace_entries.append(error_html)
                yield (build_trace_html(trace_entries, header_html), build_run_summary_html(None),
                       build_metrics_bar(step_num, ms, conf_val, exp_count, cum_reward,
                                         _explore_pct(explore_n, exploit_n)),
                       build_rl_state_panel(step_num, cur_action, cur_gene, cur_hit,
                                            conf_val, conf_prev, cur_reward, cum_reward,
                                            len(genes_studied), 30, hypothesis, candidates, kg_nodes),
                       build_progress_html(step_num, ms, ep_num, total_eps, explore_n, exploit_n),
                       generate_guidance_html(None),
                       gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                       *([None]*7),
                       gr.update(), gr.update())
                return

            stripped = line.strip()
            if not stripped:
                continue

            # ── Parse episode boundaries ──
            ep_s = ep_start_re.search(stripped)
            if ep_s:
                ep_num = int(ep_s.group(1))
                step_num, conf_val, conf_prev = 0, 0.0, 0.0
                cur_reward, cur_hit = 0.0, None
                cur_action, cur_gene = "—", "—"
                hypothesis = "No hypothesis formed"
                candidates = []
                trace_entries.append(f'<div class="log-entry episode">EPISODE {ep_num}/{total_eps} — DISCOVERY PHASE START</div>')

            # ── Parse step lines ──
            sm = step_re.search(stripped)
            if sm:
                step_num = int(sm.group(1))
                
                cur_st_reward = 0.0
                rem = reward_re.search(stripped)
                if rem:
                    cur_st_reward = float(rem.group(1))

                am = action_re.search(stripped)
                action_name = am.group(1).strip() if am else "—"
                cur_action = action_name

                gm = gene_re.search(stripped)
                target_gene = gm.group(1) if gm else "—"
                if gm:
                    cur_gene = target_gene
                    genes_studied.add(cur_gene)

                hm = hit_re.search(stripped)
                cur_hit = (hm.group(1) == "True") if hm else None

                cm = conf_re.search(stripped)
                if cm:
                    conf_prev = float(cm.group(1))
                    conf_val = float(cm.group(2))

                # Determine explore vs exploit
                if any(k in cur_action for k in ("experiment_A", "microarray", "literature", "read_")):
                    explore_n += 1
                else:
                    exploit_n += 1

                # Count experiments
                if any(k in cur_action for k in ("experiment_A", "experiment_B", "qPCR", "microarray")):
                    exp_count += 1

                # Parse top candidates
                tm = top_re.search(stripped)
                if tm:
                    candidates = [g.strip().strip("'\"") for g in tm.group(1).split(",")]
                    hypothesis = f"Top candidates: {', '.join(candidates[:3])} (conf={conf_val:.0%})"

                # Parse KG nodes
                km = kg_re.search(stripped)
                if km:
                    kg_nodes = int(km.group(2))

                # Log the step as an action
                badge = ""
                badge_type = "badge-step"
                if cur_hit is True: badge_type = "badge-hit"; badge = "HIT "
                elif cur_hit is False: badge_type = "badge-miss"; badge = "MISS "
                elif "submit" in action_name: badge_type = "badge-submit"; badge = "SUBMIT "
                
                at_cls = "action"
                log_msg = f'<div class="log-entry {at_cls}">'
                log_msg += f'<span class="log-badge {badge_type}">S{step_num}</span>'
                log_msg += f'Executed <b>{action_name}</b>'
                if target_gene != "—":
                    log_msg += f' on gene <b>{target_gene}</b> &rarr; <span class="log-badge {badge_type}">{badge or "DONE"}</span>'
                log_msg += f' <span style="color:var(--body-text-color-subdued);font-size:10px;">conf:{conf_val:.3f} rew:{cur_st_reward:+.1f}</span>'
                log_msg += '</div>'
                trace_entries.append(log_msg)

            # ── Parse episode results ──
            er = ep_result_re.search(stripped)
            if er:
                ep_reward = float(er.group(3))
                ep_score = float(er.group(4))
                cum_reward += ep_reward
                cur_reward = ep_reward
                
                res_cls = "success" if ep_score > 0.5 else "failed"
                res_msg = f'<div class="log-entry {res_cls}" style="font-weight:600;padding:8px 10px;margin-top:4px;">'
                res_msg += f'RESULT: {"SUCCESS" if res_cls=="success" else "FAILED"} &middot; '
                res_msg += f'Score: {ep_score:.3f} &middot; Reward: {ep_reward:+.1f}'
                res_msg += '</div>'
                trace_entries.append(res_msg)

            # Limit trace size
            if len(trace_entries) > 100:
                trace_entries = trace_entries[-100:]

            ep = _explore_pct(explore_n, exploit_n)
            yield (
                # Exp (6)
                build_trace_html(trace_entries, header_html),
                build_run_summary_html(None),
                build_metrics_bar(step_num, ms, conf_val, exp_count, cum_reward, ep),
                build_rl_state_panel(step_num, cur_action, cur_gene, cur_hit,
                                     conf_val, conf_prev, cur_reward, cum_reward,
                                     len(genes_studied), 30, hypothesis, candidates, kg_nodes),
                build_progress_html(step_num, ms, ep_num, total_eps, explore_n, exploit_n),
                generate_guidance_html(None),
                # Disc (5) - empty during run
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                # Analytics (7) - empty during run 
                *([None]*7),
                # Sliders
                gr.update(), gr.update()
            )

    except Exception as e:
        error_html = f'<div class="log-entry failed"><span class="log-badge badge-miss">EXCEPTION</span> {str(e)}</div>'
        trace_entries.append(error_html)
        yield (build_trace_html(trace_entries, header_html), build_run_summary_html(None),
               build_metrics_bar(step_num, ms, conf_val, exp_count, cum_reward, 50),
               build_rl_state_panel(), build_progress_html(step_num, ms, ep_num, total_eps),
               generate_guidance_html(None),
               gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
               *([None]*7),
               gr.update(), gr.update())
    finally:
        proc.wait()

    # ── Final yield with loaded results and AUTO-ANALYSIS ──
    data = load_results()
    if data:
        m = data.get("metrics", {})
        final_msg = f'<div class="log-entry episode" style="color:#10b981;border-bottom:none;">'
        final_msg += f'SIMULATION COMPLETE. Success Rate: {m.get("success_rate",0)*100:.1f}% Avg Score: {m.get("avg_score",0):.3f}'
        final_msg += '</div>'
        trace_entries.append(final_msg)
    else:
        trace_entries.append('<div class="log-entry action">Simulation finished, no data recorded.</div>')

    # Show "Finalizing" loader while processing analysis
    yield (
        # Exp (6)
        build_trace_html(trace_entries, header_html),
        build_run_summary_html(data),
        build_metrics_bar(step_num, ms, conf_val, exp_count, cum_reward, 
                          _explore_pct(explore_n, exploit_n)),
        build_loading_html(domain, agent, total_eps, ms, phase="final"),
        build_progress_html(step_num, ms, ep_num, total_eps, explore_n, exploit_n),
        generate_guidance_html(data),
        # Others (5+7)
        *([gr.update()]*5), *([None]*7),
        # Sliders
        gr.update(), gr.update()
    )

    # Trigger logic for other tabs
    disc_data = refresh_disc_logic()
    chart_data = refresh_charts_logic()
    
    ep = _explore_pct(explore_n, exploit_n)
    yield (
        # Experiment Tab (6)
        build_trace_html(trace_entries, header_html),
        build_run_summary_html(data),
        build_metrics_bar(step_num, ms, conf_val, exp_count, cum_reward, ep),
        build_rl_state_panel(step_num, cur_action, cur_gene, cur_hit,
                            conf_val, conf_prev, cur_reward, cum_reward,
                            len(genes_studied), 30, hypothesis, candidates, kg_nodes),
        build_progress_html(step_num, ms, ep_num, total_eps, explore_n, exploit_n),
        generate_guidance_html(data),
        # Discoveries Tab (5)
        *disc_data,
        # Analytics Tab (7)
        *chart_data,
        # Sliders
        gr.update(maximum=total_eps, value=1), gr.update(maximum=total_eps, value=1)
    )
def _explore_pct(explore_n, exploit_n):
    """Calculate exploration percentage."""
    total = explore_n + exploit_n
    return (explore_n / total * 100) if total > 0 else 50.0

def refresh_charts_logic():
    """Helper for Analytics tab logic."""
    data = load_results()
    if not data:
        return [None] * 7
    episodes = data.get("episodes", [])
    meta = data.get("run_metadata", {})
    max_steps = meta.get("max_steps", 50)
    target_score = meta.get("discovery_threshold", 0.7)

    return (
        build_score_chart(episodes, target_score),
        build_reward_chart(episodes),
        build_confidence_chart(episodes),
        build_budget_chart(episodes, max_steps),
        build_action_pie(episodes),
        build_reward_heatmap(episodes, max_steps),
        build_knowledge_graph(episodes),
    )

def refresh_disc_logic():
    """Helper for Discoveries tab logic."""
    data = load_results()
    genes = get_confirmed_genes(data)
    first_gene_card = get_gene_card(genes[0], data) if genes else _no_data_html()
    return (
        get_discovery_summary_html(data),
        generate_final_discovery_card(data) if data else "",
        gr.update(choices=genes, value=genes[0] if genes else None),
        first_gene_card,
        get_missed_html(data),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: DISCOVERIES
# ═══════════════════════════════════════════════════════════════════════════════

def get_discovery_summary_html(data: dict | None) -> str:
    if not data:
        return _no_data_html()

    episodes = data.get("episodes", [])
    metrics = data.get("metrics", {})
    meta = data.get("run_metadata", {})

    confirmed = []
    missed = 0
    for ep in episodes:
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            for gene in sub & truth:
                if gene not in [c[0] for c in confirmed]:
                    confirmed.append((gene, ep))
        else:
            missed += 1

    n_confirmed = len(confirmed)
    success_pct = metrics.get("success_rate", 0) * 100

    return f"""
    <div style="background:var(--background-fill-secondary);border:1px solid var(--border-color-primary);border-radius:12px;padding:28px;
                font-family:'Inter',sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="display:flex;gap:48px;align-items:center;justify-content:center;">
            <div style="text-align:center;">
                <div style="font-size:36px;font-weight:800;color:#6366f1;">{n_confirmed}</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1.5px;font-weight:500;">Confirmed</div>
            </div>
            <div style="width:1px;height:36px;background:var(--border-color-primary);"></div>
            <div style="text-align:center;">
                <div style="font-size:36px;font-weight:800;color:var(--body-text-color-subdued);">{missed}</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1.5px;font-weight:500;">Missed</div>
            </div>
            <div style="width:1px;height:36px;background:var(--border-color-primary);"></div>
            <div style="text-align:center;">
                <div style="font-size:36px;font-weight:800;color:#10b981;">{success_pct:.1f}%</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1.5px;font-weight:500;">Success Rate</div>
            </div>
        </div>
    </div>
    """


def get_confirmed_genes(data: dict | None) -> list[str]:
    if not data:
        return []
    genes = []
    for ep in data.get("episodes", []):
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            for g in sub & truth:
                if g not in genes:
                    genes.append(g)
    return genes


def get_gene_card(gene: str, data: dict | None) -> str:
    if not data or not gene:
        return _no_data_html()
    for ep in data.get("episodes", []):
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            if gene in (sub & truth):
                return generate_discovery_card_html(gene, ep, data.get("episodes", []))
    return f"<p style='color:var(--body-text-color-subdued);padding:20px;font-family:Inter;'>Gene {gene} not found in discoveries.</p>"


def get_missed_html(data: dict | None) -> str:
    if not data:
        return ""
    html = "<h4 style='color:var(--body-text-color-subdued);font-family:Inter,sans-serif;margin:24px 0 12px;font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:1px;'>Non-Validated Targets</h4>"
    for ep in data.get("episodes", []):
        if not ep.get("success"):
            html += generate_missed_card_html(ep)
    if all(ep.get("success") for ep in data.get("episodes", [])):
        html += "<p style='color:#059669;font-family:Inter;font-size:14px;'>All discoveries validated successfully.</p>"
    return html


def generate_final_discovery_card(data: dict) -> str:
    if not data:
        return _no_data_html()

    metrics = data.get("metrics", {})
    episodes = data.get("episodes", [])
    meta = data.get("run_metadata", {})

    all_confirmed = []
    for ep in episodes:
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            all_confirmed.extend(sub & truth)

    unique_genes = list(set(all_confirmed))
    avg_conf = metrics.get("avg_confidence", 0)
    avg_steps = metrics.get("avg_steps", 50)
    max_steps = meta.get("max_steps", 50)
    efficiency = max(0, 1 - avg_steps / max(max_steps, 1))

    gene_chips = " ".join(
        f'<span style="background:#eef2ff;color:#4338ca;padding:4px 12px;border-radius:16px;'
        f'font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;margin:2px;">{g}</span>'
        for g in unique_genes
    ) if unique_genes else '<span style="color:var(--body-text-color-subdued);font-size:13px;">None identified</span>'

    return f"""
    <div style="background:var(--background-fill-secondary);border:1px solid var(--border-color-primary);border-radius:12px;padding:28px;
                font-family:'Inter',sans-serif;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin:16px 0;">
        <h3 style="margin:0 0 20px;font-size:16px;font-weight:700;color:#6366f1;">Discovery Summary</h3>
        <div style="margin-bottom:20px;">{gene_chips}</div>
        <div style="display:flex;gap:40px;">
            <div style="text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#6366f1;">{avg_conf:.2f}</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Avg Confidence</div>
            </div>
            <div style="width:1px;height:40px;background:var(--border-color-primary);"></div>
            <div style="text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#8b5cf6;">{efficiency:.2f}</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Efficiency</div>
            </div>
            <div style="width:1px;height:40px;background:var(--border-color-primary);"></div>
            <div style="text-align:center;">
                <div style="font-size:28px;font-weight:700;color:#10b981;">{len(unique_genes)}</div>
                <div style="color:var(--body-text-color-subdued);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Unique Targets</div>
            </div>
        </div>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def refresh_charts():
    data = load_results()
    if not data:
        import plotly.graph_objects as go
        empty = go.Figure()
        empty.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="var(--body-text-color)"),
            annotations=[dict(text="No data", x=0.5, y=0.5, showarrow=False,
                              font=dict(size=14, color="var(--body-text-color-subdued)"))],
            xaxis=dict(visible=False), yaxis=dict(visible=False), height=360,
        )
        return empty, empty, empty, empty, empty, empty, empty

    episodes = data.get("episodes", [])
    meta = data.get("run_metadata", {})
    difficulty = meta.get("difficulty", "medium")
    max_steps = meta.get("max_steps", 50)
    target = _target_score(difficulty)

    return (
        build_score_chart(episodes, target),
        build_reward_chart(episodes),
        build_confidence_chart(episodes),
        build_budget_chart(episodes, max_steps),
        build_action_pie(episodes),
        build_reward_heatmap(episodes, max_steps),
        build_knowledge_graph(episodes),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: EPISODE AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

def get_episodes_df():
    data = load_results()
    if not data:
        return pd.DataFrame()
    rows = []
    for ep in data.get("episodes", []):
        rows.append({
            "Episode": ep["episode"],
            "Status": "Validated" if ep.get("success") else "Failed",
            "Score": round(ep.get("score", 0), 4),
            "Reward": round(ep.get("reward", 0), 1),
            "Steps": ep.get("steps", 0),
            "Confidence": round(ep.get("final_confidence", 0), 2),
            "Targets": ", ".join(ep.get("true_targets", [])[:3]),
            "Candidates": ", ".join(ep.get("submitted_candidates", [])[:3]),
        })
    return pd.DataFrame(rows)


def get_episode_detail(ep_num):
    data = load_results()
    if not data:
        return "<p style='color:var(--body-text-color-subdued);'>No data.</p>", None, None, pd.DataFrame()

    episodes = data.get("episodes", [])
    ep_idx = int(ep_num) - 1
    if ep_idx < 0 or ep_idx >= len(episodes):
        return "<p style='color:var(--body-text-color-subdued);'>Invalid selection.</p>", None, None, pd.DataFrame()

    ep = episodes[ep_idx]
    success = ep.get("success")
    status = "Validated" if success else "Not Validated"
    color = "#4f46e5" if success else "var(--body-text-color-subdued)"
    bg = "#eef2ff" if success else "var(--background-fill-secondary)"

    header_html = f"""
    <div style="background:var(--background-fill-secondary);border-left:3px solid #6366f1;border-radius:8px;padding:20px 24px;
                font-family:'Inter',sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <h3 style="color:#6366f1;margin:0;font-weight:700;font-size:16px;">Episode {ep['episode']} — {status}</h3>
            <span style="background:transparent;border:1px solid #6366f1;color:#6366f1;padding:4px 14px;
                         border-radius:6px;font-size:12px;font-weight:700;">
                {ep.get('score', 0):.4f}
            </span>
        </div>
        <div style="display:flex;gap:32px;margin-top:12px;color:var(--body-text-color-subdued);font-size:12px;">
            <span>Reward: {ep.get('reward', 0):.1f}</span>
            <span>Steps: {ep.get('steps', 0)}</span>
            <span>Confidence: {ep.get('final_confidence', 0):.2f}</span>
            <span>Targets: {', '.join(ep.get('true_targets', []))}</span>
        </div>
    </div>
    """

    conf_chart = build_confidence_trajectory(ep)
    hyp_chart = build_hypothesis_timeline(ep)

    true_targets = ep.get("true_targets", [])
    rows = []
    prev_conf = 0.1
    for act in ep.get("action_history", []):
        gene = act.get("gene_tested", "—")
        current_conf = act.get("confidence", 0)
        rows.append({
            "Step": act.get("step", 0),
            "Action": ["Scan", "qPCR", "Refine", "Literature", "Combine", "Submit"][act.get("action", 0)],
            "Gene": gene,
            "Signal": act.get("signal", "—"),
            "Conf Before": round(prev_conf, 3),
            "Conf After": round(current_conf, 3),
            "Δ": "↑" if current_conf > prev_conf else ("↓" if current_conf < prev_conf else "—"),
            "Reward": round(act.get("reward", 0), 2),
        })
        prev_conf = current_conf
    return header_html, conf_chart, hyp_chart, pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def get_report():
    data = load_results()
    if not data:
        return "Run a simulation to generate a report."
    return generate_report(data)


def download_report(report_text):
    path = "/tmp/genomiq_report.txt"
    with open(path, "w") as f:
        f.write(report_text)
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def get_config_text():
    try:
        return Path(CONFIG_PATH).read_text()
    except FileNotFoundError:
        return "# not found"


def get_openenv_yaml():
    try:
        with open("openenv.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"error": "not found"}


def get_logs():
    try:
        lines = Path(LOG_PATH).read_text().splitlines()
        return "\n".join(lines[-100:])
    except FileNotFoundError:
        return "No logs recorded."


def clear_logs():
    try:
        Path(LOG_PATH).write_text("")
        return "Logs cleared."
    except Exception:
        return "Failed to clear."


def get_validation_html():
    checks = [
        ("openenv.yaml", os.path.exists("openenv.yaml")),
        ("Dockerfile", os.path.exists("Dockerfile")),
        ("inference.py", os.path.exists("inference.py")),
        ("results/latest_run.json", os.path.exists(RESULTS_PATH)),
        ("config.yaml", os.path.exists(CONFIG_PATH)),
        ("runner.py", os.path.exists("runner.py")),
        ("datasets/", os.path.exists("datasets")),
    ]
    rows = ""
    for name, exists in checks:
        color = "#059669" if exists else "#ef4444"
        bg = "#ecfdf5" if exists else "#fef2f2"
        status = "OK" if exists else "MISSING"
        rows += f"""
        <div style="display:flex;justify-content:space-between;padding:8px 12px;background:{bg};
                    border-radius:6px;margin-bottom:4px;">
            <span style="color:var(--body-text-color);font-size:13px;">{name}</span>
            <span style="color:{color};font-size:11px;font-weight:700;letter-spacing:0.5px;">{status}</span>
        </div>
        """

    return f"""
    <div style="background:var(--block-background-fill);border:1px solid var(--border-color-primary);border-radius:10px;padding:20px;font-family:Inter,sans-serif;">
        <h4 style="color:var(--block-title-text-color);margin:0 0 12px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">
            Deployment Validation
        </h4>
        {rows}
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD THE UI
# ═══════════════════════════════════════════════════════════════════════════════

init_data = load_results()
init_eps = len(init_data.get("episodes", [])) if init_data else 100
init_eps = init_eps if init_eps > 0 else 100
theme = GenomIQTheme()

with gr.Blocks(theme=theme, title="GenomIQ — Scientific Discovery Lab", css=CUSTOM_CSS) as demo:

    # ── Header ────────────────────────────────────────────────────────────
    gr.HTML("""
    <div style="text-align:center;padding:28px 0 8px;font-family:'Inter',sans-serif;">
        <h1 style="font-size:38px;font-weight:800;margin:0;
                    background:linear-gradient(135deg,#4f46e5,#7c3aed);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    letter-spacing:-1px;">
            GENOMIQ
        </h1>
        <p style="color:var(--body-text-color-subdued);font-size:13px;margin:6px 0 0;letter-spacing:3px;text-transform:uppercase;font-weight:500;">
            Scientific Discovery RL Platform
        </p>
    </div>
    """)

    with gr.Tabs():

        # ══ TAB 1: EXPERIMENT ═════════════════════════════════════════════
        with gr.Tab("Experiment"):
            with gr.Row():
                # ── LEFT PANEL: Research-Grade Controls ──
                with gr.Column(scale=1):
                    gr.HTML("""
                    <div style="font-family:'Inter',sans-serif;margin-bottom:8px;">
                      <div style="font-size:12px;font-weight:700;color:#6366f1;text-transform:uppercase;
                                  letter-spacing:1.5px;">Experiment Configuration</div>
                    </div>""")

                    domain_dd = gr.Dropdown(
                        ["gene_expression", "disease_genomics", "drug_target",
                         "gene_regulatory", "epigenomics", "synthetic_biology"],
                        value="gene_expression", label="Research Domain",
                        info="Biological domain for discovery simulation"
                    )
                    difficulty_dd = gr.Dropdown(
                        ["easy", "medium", "hard"], value="medium", label="Difficulty"
                    )
                    objective_dd = gr.Dropdown(
                        ["Identify Key Regulator Genes", "Detect Co-expression Clusters",
                         "Find Gene-Gene Interaction Effects", "Predict Disease-Associated Genes",
                         "Identify Potential Drug Targets"],
                        value="Identify Key Regulator Genes", label="Research Objective"
                    )
                    dataset_dd = gr.Dropdown(
                        ["Synthetic (Generated)", "Cancer Gene Expression (Preloaded)",
                         "Rare Disease Panel (Preloaded)", "Custom Upload (CSV)",
                         "TCGA-BRCA (Real-World)", "GEO Lung (Real-World)"],
                        value="Synthetic (Generated)", label="Dataset Source",
                        info="Real-World sources use published cohort signatures"
                    )
                    upload_csv = gr.File(label="Upload CSV", file_types=[".csv"], visible=False)
                    dataset_dd.change(fn=lambda x: gr.update(visible=(x == "Custom Upload (CSV)")),
                                      inputs=[dataset_dd], outputs=[upload_csv])

                    with gr.Accordion("RL Configuration", open=False):
                        gr.HTML("""<div style="font-size:11px;color:var(--body-text-color-subdued);margin-bottom:8px;font-family:Inter;">
                          Define the reinforcement learning state representation, action space, and reward shaping.
                        </div>""")
                        state_repr_dd = gr.Dropdown(
                            ["Gene Expression Vector", "Confidence + Coverage", "Full Observation"],
                            value="Full Observation", label="State Representation",
                            info="How the agent perceives the environment"
                        )
                        gr.HTML("""<div style="font-family:'Inter',sans-serif;font-size:11px;color:var(--body-text-color-subdued);
                                    padding:10px 12px;background:rgba(99,102,241,0.04);border-radius:8px;
                                    border:1px solid rgba(99,102,241,0.1);margin:6px 0;">
                          <div style="font-weight:600;color:var(--body-text-color);margin-bottom:4px;">Action Space (6 actions)</div>
                          <div>0: Microarray Scan · 1: qPCR Validation · 2: Refine Hypothesis</div>
                          <div>3: Literature Review · 4: Data Synthesis · 5: Submit Discovery</div>
                        </div>""")
                        disc_sl = gr.Slider(0, 50, value=20.0, step=0.5, label="Discovery Bonus (R+)")
                        step_sl = gr.Slider(-1, 0, value=-0.1, step=0.01, label="Step Penalty (R-)")
                        exp_sl = gr.Slider(-5, 0, value=-2.0, step=0.1, label="Redundancy Penalty")
                        ref_sl = gr.Slider(0, 10, value=5.0, step=0.5, label="Refinement Bonus")

                    with gr.Accordion("Agent Configuration", open=False):
                        agent_dd = gr.Dropdown(
                            ["greedy", "dqn", "ppo", "random", "multi_agent"], value="greedy",
                            label="Policy Type",
                            info="multi_agent = Explorer→Validator→Theorist collaboration"
                        )
                        explore_rate_sl = gr.Slider(0.0, 1.0, value=0.3, step=0.05,
                                                     label="Exploration Rate (ε)",
                                                     info="Higher = more random exploration")
                        learning_dd = gr.Dropdown(
                            ["Q-Learning", "Policy Gradient", "Actor-Critic", "Heuristic"],
                            value="Heuristic", label="Learning Method"
                        )

                    with gr.Accordion("Experiment Budget", open=False):
                        episodes_sl = gr.Slider(1, 100, value=10, step=1, label="Episodes")
                        max_steps_sl = gr.Slider(10, 200, value=50, step=5, label="Max Steps/Episode")
                        seed_num = gr.Number(value=42, label="Random Seed", precision=0)
                        oracle_cb = gr.Checkbox(value=False, label="Enable LLM Literature Oracle")

                    with gr.Accordion("Experimental Constraints", open=False):
                        noise_sl = gr.Slider(0.1, 5.0, value=2.0, step=0.1, label="Noise Level (σ)")
                        cost_dd = gr.Dropdown(
                            ["Low Fidelity (Cheap)", "High Fidelity (Expensive)", "Mixed"],
                            value="Mixed", label="Cost Tier")
                        time_sl = gr.Slider(0, 300, value=0, step=10, label="Time Limit (s, 0=∞)")

                    with gr.Accordion("Prior Knowledge", open=False):
                        seed_genes_tb = gr.Textbox(label="Seed Genes", placeholder="TP53, BRCA1, MYC")
                        known_assoc_tb = gr.Textbox(label="Known Associations", placeholder="TP53-MDM2, BRCA1-RAD51")
                        lit_hints_tb = gr.Textbox(label="Literature Hints (;-separated)",
                                                  placeholder="TP53 shows elevated expression in tumor samples")

                    run_btn = gr.Button("Run Simulation", variant="primary", size="lg")

                # ── MAIN PANEL: Live RL Dashboard ──
                with gr.Column(scale=3):
                    # Row 1: Live Metrics Bar
                    metrics_bar = gr.HTML(value=build_metrics_bar())

                    # Row 2: Episode Progress Tracker
                    progress_bar = gr.HTML(value=build_progress_html())

                    # Row 3: RL Loop Panel — State | Action | Reward
                    rl_loop_panel = gr.HTML(value=build_rl_state_panel())

                    # Row 4: Trace — spans full width now
                    trace_area = gr.HTML(value=build_trace_html([]))

                    # Row 5: Run Summary
                    summary_html_out = gr.HTML(value=build_run_summary_html(None))

                    # Row 6: AI Guidance
                    guidance_html = gr.HTML(value=generate_guidance_html(None))
                    guidance_btn = gr.Button("Refresh AI Guidance", size="sm")
                    guidance_btn.click(fn=lambda: generate_guidance_html(load_results()),
                                       outputs=[guidance_html])


        # ══ TAB 2: DISCOVERIES ════════════════════════════════════════════
        with gr.Tab("Discoveries"):
            disc_summary = gr.HTML(value=_no_data_html())
            disc_btn = gr.Button("Sync Results", size="sm")
            final_card = gr.HTML(value="")

            with gr.Row():
                with gr.Column(scale=1):
                    gene_radio = gr.Radio(choices=[], label="Validated Genes", interactive=True)
                with gr.Column(scale=3):
                    gene_card_html = gr.HTML(value=_no_data_html())

            missed_html = gr.HTML(value="")

            def refresh_disc():
                data = load_results()
                genes = get_confirmed_genes(data)
                return (
                    get_discovery_summary_html(data),
                    generate_final_discovery_card(data) if data else "",
                    gr.update(choices=genes, value=genes[0] if genes else None),
                    get_gene_card(genes[0], data) if genes else _no_data_html(),
                    get_missed_html(data),
                )

            disc_btn.click(fn=refresh_disc_logic,
                          outputs=[disc_summary, final_card, gene_radio, gene_card_html, missed_html])
            gene_radio.change(fn=lambda g: get_gene_card(g, load_results()),
                             inputs=[gene_radio], outputs=[gene_card_html])

            # ── Explainability Panel ──
            gr.Markdown("### Gene Selection Explainability")
            explain_btn = gr.Button("Run Explainability Analysis", size="sm")
            explain_chart = gr.Plot(label="Factor Breakdown")
            explain_cards_html = gr.HTML(value="")

            def run_explainability():
                data = load_results()
                if not data:
                    return None, _no_data_html()
                explanations = explain_all_discoveries(data.get("episodes", []))
                chart = build_explainability_chart(explanations)
                # Build Discovery Card 2.0 for each explained gene
                cards_html = ""
                for exp in explanations:
                    cards_html += generate_discovery_card_v2_html(exp["gene"], data, exp)
                if not cards_html:
                    cards_html = '<p style="color:var(--body-text-color-subdued);font-size:13px;">No confirmed discoveries to explain. Run a simulation first.</p>'
                return chart, cards_html

            explain_btn.click(fn=run_explainability, outputs=[explain_chart, explain_cards_html])

        # ══ TAB 3: ANALYTICS ══════════════════════════════════════════════
        with gr.Tab("Analytics"):
            charts_btn = gr.Button("Reload Charts", size="sm")
            with gr.Row():
                score_plot = gr.Plot(label="Discovery Precision")
                reward_plot = gr.Plot(label="Reward Trajectory")
            with gr.Row():
                conf_plot = gr.Plot(label="Hypothesis Confidence")
                budget_plot = gr.Plot(label="Resource Allocation")
            with gr.Row():
                pie_plot = gr.Plot(label="Action Distribution")
                heatmap_plot = gr.Plot(label="Reward Heatmap")

            gr.Markdown("### Gene Co-Investigation Network")
            kg_plot = gr.Plot(label="Knowledge Graph")

            charts_btn.click(fn=refresh_charts_logic,
                            outputs=[score_plot, reward_plot, conf_plot, budget_plot,
                                     pie_plot, heatmap_plot, kg_plot])

        # ══ TAB 4: EPISODE CYCLE ═════════════════════════════════════════════
        with gr.Tab("Episode Cycle"):
            gr.HTML("""
            <div style="font-family:'Inter',sans-serif;padding:8px 0 16px;">
                <h3 style="margin:0;font-weight:700;color:var(--block-title-text-color);font-size:18px;">
                    Discovery Narrative
                </h3>
                <p style="color:var(--body-text-color-subdued);font-size:13px;margin:4px 0 0;">
                    Follow the agent's journey from blank hypothesis to validated discovery.
                    Each step shows the reasoning, evidence, and confidence evolution.
                </p>
            </div>
            """)
            story_ep_sl = gr.Slider(1, init_eps, value=1, step=1, label="Episode")
            init_story_html_val = generate_story_html(init_data, 0) if init_data else _no_data_html()
            story_html = gr.HTML(value=init_story_html_val)

            def refresh_story(ep_num):
                data = load_results()
                return generate_story_html(data, int(ep_num) - 1)

            story_ep_sl.change(fn=refresh_story, inputs=[story_ep_sl], outputs=[story_html])

            story_btn = gr.Button("Load Narrative", size="sm")
            story_btn.click(fn=lambda ep: generate_story_html(load_results(), int(ep) - 1),
                           inputs=[story_ep_sl], outputs=[story_html])

        # ══ TAB 5: EPISODE AUDIT ══════════════════════════════════════════
        with gr.Tab("Episode Audit"):
            ep_btn = gr.Button("Load Episodes", size="sm")
            ep_table = gr.DataFrame(label="Episode Log", interactive=False)
            ep_btn.click(fn=get_episodes_df, outputs=[ep_table])

            gr.Markdown("### Episode Detail View")
            ep_slider = gr.Slider(1, init_eps, value=1, step=1, label="Episode Index")
            init_ep_detail = get_episode_detail(1)
            ep_header = gr.HTML(value=init_ep_detail[0])
            with gr.Row():
                ep_conf = gr.Plot(value=init_ep_detail[1], label="Confidence Trajectory")
                ep_hyp = gr.Plot(value=init_ep_detail[2], label="Hypothesis Timeline")
            ep_actions = gr.DataFrame(value=init_ep_detail[3], label="Lab Notebook", interactive=False)
            ep_slider.change(fn=get_episode_detail, inputs=[ep_slider],
                            outputs=[ep_header, ep_conf, ep_hyp, ep_actions])

        # ══ TAB 6: REPORT ═════════════════════════════════════════════════
        with gr.Tab("Report"):
            with gr.Row():
                report_btn = gr.Button("Generate Full Report & Hypothesis", variant="primary", size="lg")
                report_dl_btn = gr.DownloadButton("Download PDF 📥", size="lg", variant="secondary", visible=False)

            report_md = gr.Markdown(value="*Run a simulation to generate a unified scientific report and publishable hypothesis.*")

            def generate_both_and_pdf():
                from fpdf import FPDF
                import re, os
                
                data = load_results()
                if not data:
                    return "*No data available.*", gr.update(visible=False)
                
                rep = generate_report(data)
                hyp = generate_paper_hypothesis(data)
                full_text = rep + "\n\n---\n\n" + hyp
                
                # Format for PDF (Cleaning unicode)
                pdf_text = full_text.replace('–', '-').replace('—', '-').replace('•', '-')
                pdf_text = pdf_text.encode('latin-1', 'replace').decode('latin-1')

                pdf = FPDF()
                pdf.set_margins(left=20, top=20, right=20)
                pdf.set_auto_page_break(auto=True, margin=20)
                pdf.add_page()
                pdf.set_font("helvetica", size=10)
                
                try:
                    from markdown_it import MarkdownIt
                    md = MarkdownIt().enable('table')
                    html_content = md.render(pdf_text)
                    
                    # Apply inline styling for fpdf2 which does not support <style>
                    html_content = html_content.replace('<h2>', '<h2><font color="#2563eb">')
                    html_content = html_content.replace('</h2>', '</font></h2>')
                    html_content = html_content.replace('<h3>', '<h3><font color="var(--body-text-color)">')
                    html_content = html_content.replace('</h3>', '</font></h3>')
                    
                    # Style tables
                    html_content = html_content.replace('<table>', '<table width="100%" border="1">')
                    html_content = html_content.replace('<th>', '<th bgcolor="var(--border-color-primary)">')
                    
                    header_html = """
                    <h1 align="center"><font color="#1e3a8a">GenomIQ Laboratory Report</font></h1>
                    <p align="center"><i><font color="var(--body-text-color-subdued)">Automated Scientific Discovery & Hypothesis Generation</font></i></p>
                    <hr>
                    <br>
                    """
                    pdf.write_html(header_html + html_content)
                except Exception:
                    plain = re.sub(r'[*_]{1,3}', '', pdf_text)
                    pdf.multi_cell(0, 5, plain)
                    
                path = os.path.join(os.getcwd(), "genomiq_report.pdf")
                pdf.output(path)
                
                return full_text, gr.update(value=path, visible=True)

            report_btn.click(fn=generate_both_and_pdf, outputs=[report_md, report_dl_btn])

        # ══ TAB 7: SYSTEM ═════════════════════════════════════════════════
        with gr.Tab("System"):
            with gr.Row():
                with gr.Column():
                    cfg_btn = gr.Button("Reload Config", size="sm")
                    cfg_code = gr.Code(value=get_config_text(), language="yaml", label="config.yaml")
                    oe_json = gr.JSON(value=get_openenv_yaml(), label="OpenEnv Metadata")
                    cfg_btn.click(fn=lambda: (get_config_text(), get_openenv_yaml()),
                                 outputs=[cfg_code, oe_json])

                with gr.Column():
                    log_btn = gr.Button("Refresh Logs", size="sm")
                    log_clr = gr.Button("Clear Logs", size="sm")
                    log_box = gr.Textbox(value=get_logs(), label="Runtime Logs", lines=24, interactive=False)
                    val_html = gr.HTML(value=get_validation_html())
                    log_btn.click(fn=get_logs, outputs=[log_box])
                    log_clr.click(fn=clear_logs, outputs=[log_box])

        # ══ TAB 8: AI SCIENTIST ═══════════════════════════════════════════
        with gr.Tab("AI Scientist"):
            gr.HTML("""
            <div style="font-family:'Inter',sans-serif;padding:8px 0 16px;">
                <h3 style="margin:0;font-weight:700;color:#6366f1;font-size:18px;">
                    Chat with Your AI Scientist
                </h3>
                <p style="color:var(--body-text-color-subdued);font-size:13px;margin:4px 0 0;">
                    Ask questions about your experiment results. Uses LLM when available,
                    with full deterministic fallback — always works, no API key required.
                </p>
            </div>
            """)

            chatbot = gr.Chatbot(
                label="GenomIQ AI Scientist",
                height=500,
                type="messages",
                bubble_full_width=False,
                avatar_images=(
                    "https://ui-avatars.com/api/?name=U&background=f1f5f9&color=334155&rounded=true&bold=true",
                    "https://ui-avatars.com/api/?name=AI&background=6366f1&color=ffffff&rounded=true&bold=true"
                ),
                show_copy_button=True,
                container=False,
            )
            with gr.Row():
                with gr.Column(scale=8):
                    chat_input = gr.Textbox(
                        placeholder="💭 Ask your AI Scientist a question about the experiment...",
                        show_label=False,
                        container=False,
                        lines=1,
                    )
                with gr.Column(scale=1, min_width=80):
                    chat_send = gr.Button("Send ✨", variant="primary")

            gr.HTML("<p style='color:var(--body-text-color-subdued);font-size:12px;margin:12px 0 6px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;'>Suggested Research Queries:</p>")
            with gr.Row():
                with gr.Column(scale=1):
                    for sq in SUGGESTED_QUESTIONS[:2]:
                        gr.Button(sq, size="sm", variant="secondary").click(
                            fn=lambda q=sq: q, outputs=[chat_input]
                        )
                with gr.Column(scale=1):
                    for sq in SUGGESTED_QUESTIONS[2:]:
                        gr.Button(sq, size="sm", variant="secondary").click(
                            fn=lambda q=sq: q, outputs=[chat_input]
                        )

            def chat_respond(message, history):
                if not message or not message.strip():
                    return history, ""
                data = load_results()
                response = ask_scientist(message, data)
                history = history or []
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": response})
                return history, ""

            chat_send.click(fn=chat_respond, inputs=[chat_input, chatbot],
                          outputs=[chatbot, chat_input])
            chat_input.submit(fn=chat_respond, inputs=[chat_input, chatbot],
                            outputs=[chatbot, chat_input])

        # ── Event Listeners ──
        run_btn.click(
            fn=run_simulation,
            inputs=[domain_dd, difficulty_dd, agent_dd, episodes_sl, max_steps_sl,
                    seed_num, oracle_cb, disc_sl, step_sl, exp_sl, ref_sl,
                    objective_dd, dataset_dd, noise_sl, cost_dd, time_sl,
                    seed_genes_tb, known_assoc_tb, lit_hints_tb],
            outputs=[trace_area, summary_html_out, metrics_bar, rl_loop_panel,
                     progress_bar, guidance_html,
                     disc_summary, final_card, gene_radio, gene_card_html, missed_html,
                     score_plot, reward_plot, conf_plot, budget_plot,
                     pie_plot, heatmap_plot, kg_plot,
                     story_ep_sl, ep_slider],
        ).then(
            fn=refresh_story, inputs=[story_ep_sl], outputs=[story_html]
        ).then(
            fn=get_episode_detail, inputs=[ep_slider],
            outputs=[ep_header, ep_conf, ep_hyp, ep_actions]
        )

        lab_metadata = gr.HTML("""
            <div style="display:flex;justify-content:space-between;padding:12px 18px;
                        background:var(--background-fill-secondary);border-top:1px solid var(--border-color-primary);margin-top:20px;
                        font-family:'Inter',sans-serif;font-size:10px;color:var(--body-text-color-subdued);
                        text-transform:uppercase;letter-spacing:1px;border-radius:0 0 14px 14px;">
              <div>GenomIQ Research OS · v2.4.0 · STABLE_BUILD</div>
              <div style="display:flex;gap:15px;">
                <span>System: AI Research Hub</span>
                <span>Status: Optimal</span>
                <span>Runtime: Darwin/x86_64</span>
              </div>
            </div>
        """)

# ── Launch ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)

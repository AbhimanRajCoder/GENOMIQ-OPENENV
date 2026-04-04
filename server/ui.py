import streamlit as st
import yaml
import json
import subprocess
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# ───────────────────────────────────────────────────────────
# Page Config
# ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GenomIQ — Scientific Discovery Lab",
    page_icon="🧬",
    layout="wide",
)

# ───────────────────────────────────────────────────────────
# Custom Styling
# ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1c24 0%, #21262d 100%);
        padding: 18px 22px; border-radius: 12px;
        border: 1px solid #30363d; text-align: center;
    }
    .metric-card h2 { margin: 0; font-size: 2rem; }
    .metric-card p  { margin: 4px 0 0; color: #8b949e; font-size: 0.85rem; }
    .report-card {
        background: #161b22; border-radius: 10px;
        padding: 22px 26px; border-left: 5px solid #238636;
    }
    .fail-card {
        background: #161b22; border-radius: 10px;
        padding: 22px 26px; border-left: 5px solid #da3633;
    }
    .gene-chip {
        display: inline-block; padding: 3px 10px; margin: 2px;
        background: #238636; color: white; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600;
    }
    .gene-chip-miss {
        display: inline-block; padding: 3px 10px; margin: 2px;
        background: #6e7681; color: white; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────
# Settings
# ───────────────────────────────────────────────────────────
CONFIG_PATH = Path("config.yaml")
RESULTS_PATH = Path("results/latest_run.json")
LOG_FILE = Path("logs/genomiq.log")


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    return {}


def save_config(config_dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False)


def run_simulation_backend():
    with st.spinner("🚀 Running simulation in backend..."):
        try:
            cmd = ["python3", "runner.py", "--config", str(CONFIG_PATH)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                st.toast("Simulation Complete!", icon="✅")
                return True
            else:
                st.error(f"Runner error:\n{result.stderr[-500:]}")
                return False
        except Exception as e:
            st.error(f"Execution failed: {e}")
            return False


# ───────────────────────────────────────────────────────────
# Sidebar Configuration
# ───────────────────────────────────────────────────────────
st.sidebar.title("🧬 GenomIQ Config")
config = load_config()

if config:
    with st.sidebar.expander("🔬 Scenario", expanded=True):
        config["scenario"]["domain"] = st.selectbox(
            "Scientific Domain",
            ["gene_expression", "drug_target", "protein_fold"],
            index=["gene_expression", "drug_target", "protein_fold"].index(config["scenario"]["domain"]),
        )
        config["scenario"]["difficulty"] = st.selectbox(
            "Task Difficulty", ["easy", "medium", "hard"],
            index=["easy", "medium", "hard"].index(config["scenario"]["difficulty"]),
        )
        config["scenario"]["num_episodes"] = st.number_input("Episodes", 1, 1000, value=config["scenario"]["num_episodes"])
        config["scenario"]["max_steps"] = st.number_input("Max Steps", 10, 200, value=config["scenario"]["max_steps"])
        config["scenario"]["seed"] = st.number_input("Seed", value=config["scenario"]["seed"])

    with st.sidebar.expander("🤖 Agent"):
        config["agent"]["type"] = st.selectbox(
            "Agent Type", ["random", "greedy", "ppo", "dqn"],
            index=["random", "greedy", "ppo", "dqn"].index(config["agent"]["type"]),
        )
        config["agent"]["learning_rate"] = st.number_input("Learning Rate", 0.0001, 0.01, value=config["agent"]["learning_rate"], format="%.4f")
        config["agent"]["use_claude_oracle"] = st.checkbox("Use LLM Oracle", value=config["agent"]["use_claude_oracle"])

    with st.sidebar.expander("💰 Rewards"):
        config["rewards"]["discovery_bonus"] = st.number_input("Discovery Bonus", value=config["rewards"]["discovery_bonus"])
        config["rewards"]["useless_experiment_penalty"] = st.number_input("Experiment Penalty", value=config["rewards"]["useless_experiment_penalty"])
        config["rewards"]["hypothesis_improvement_bonus"] = st.number_input("Refinement Bonus", value=config["rewards"]["hypothesis_improvement_bonus"])
        config["rewards"]["step_penalty"] = st.number_input("Step Penalty", value=config["rewards"]["step_penalty"])

    if st.sidebar.button("💾 Save Config", use_container_width=True):
        save_config(config)
        st.toast("Config saved!", icon="💾")

# ───────────────────────────────────────────────────────────
# Main Header
# ───────────────────────────────────────────────────────────
st.title("🔬 GenomIQ — Scientific Discovery Lab")

col_run, col_info = st.columns([1, 3])
with col_run:
    if st.button("▶ RUN SIMULATION", use_container_width=True, type="primary"):
        save_config(config)
        if run_simulation_backend():
            st.rerun()
with col_info:
    domain_label = config.get("scenario", {}).get("domain", "—").replace("_", " ").title()
    st.caption(f"**{domain_label}** · {config.get('scenario', {}).get('difficulty', '—').title()} · Agent: {config.get('agent', {}).get('type', '—').title()}")

# ───────────────────────────────────────────────────────────
# Results Dashboard
# ───────────────────────────────────────────────────────────
if RESULTS_PATH.exists():
    with open(RESULTS_PATH, "r") as f:
        data = json.load(f)

    meta = data.get("run_metadata", {})
    metrics = data.get("metrics", {})
    episodes = data.get("episodes", [])
    gene_analysis = data.get("gene_analysis", {})
    best_ep = data.get("best_episode", {})
    worst_ep = data.get("worst_episode", {})

    # ── Run Banner ──
    st.markdown("---")
    banner_cols = st.columns(4)
    banner_cols[0].markdown(f"**Domain:** `{meta.get('domain', '—')}`")
    banner_cols[1].markdown(f"**Difficulty:** `{meta.get('difficulty', '—')}`")
    banner_cols[2].markdown(f"**Agent:** `{meta.get('agent_type', '—')}`")
    ts = meta.get("timestamp", "")
    banner_cols[3].markdown(f"**Run:** `{ts[:19] if ts else '—'}` ({meta.get('elapsed_seconds', '?')}s)")

    # ── Key Metrics ──
    st.markdown("### 📊 Performance Summary")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    success_pct = metrics.get("success_rate", 0)
    m1.metric("Success Rate", f"{success_pct:.0%}")
    m2.metric("Avg Score", f"{metrics.get('avg_score', 0):.3f}")
    m3.metric("Avg Reward", f"{metrics.get('avg_reward', 0):.1f}")
    m4.metric("Avg Steps", f"{metrics.get('avg_steps', 0):.0f}")
    m5.metric("Avg Confidence", f"{metrics.get('avg_confidence', 0):.2f}")
    m6.metric("Score Range", f"{metrics.get('min_score', 0):.3f}–{metrics.get('max_score', 0):.3f}")

    # ── Tabs ──
    tab_charts, tab_genes, tab_episodes, tab_best_worst, tab_logs = st.tabs([
        "📈 Charts", "🧬 Gene Analysis", "📋 Episode Table", "🏆 Best / Worst", "📟 Console Logs"
    ])

    df = pd.DataFrame(episodes)

    # ── Tab 1: Charts ──
    with tab_charts:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(df, x="episode", y="reward", title="Cumulative Reward per Episode",
                          template="plotly_dark", color_discrete_sequence=["#00d4ff"],
                          markers=True)
            fig.update_layout(xaxis_title="Episode", yaxis_title="Reward")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.line(df, x="episode", y="score", title="Discovery Score per Episode",
                           template="plotly_dark", color_discrete_sequence=["#238636"],
                           markers=True)
            fig2.add_hline(y=0.65, line_dash="dash", line_color="#da3633", annotation_text="Target (medium)")
            fig2.update_layout(xaxis_title="Episode", yaxis_title="Score")
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            if "final_confidence" in df.columns:
                fig3 = px.bar(df, x="episode", y="final_confidence", title="Final Confidence per Episode",
                              template="plotly_dark", color_discrete_sequence=["#a371f7"])
                fig3.update_layout(xaxis_title="Episode", yaxis_title="Confidence")
                st.plotly_chart(fig3, use_container_width=True)
        with c4:
            fig4 = px.histogram(df, x="steps", nbins=15, title="Steps Distribution",
                                template="plotly_dark", color_discrete_sequence=["#f0883e"])
            fig4.update_layout(xaxis_title="Steps", yaxis_title="Count")
            st.plotly_chart(fig4, use_container_width=True)

    # ── Tab 2: Gene Analysis ──
    with tab_genes:
        gene_c1, gene_c2 = st.columns(2)

        with gene_c1:
            st.markdown("#### 🔬 Most Submitted Candidates")
            submitted = gene_analysis.get("most_submitted_candidates", [])
            if submitted:
                sub_df = pd.DataFrame(submitted)
                fig_sub = px.bar(sub_df, x="gene", y="count", title="Gene Submission Frequency",
                                 template="plotly_dark", color_discrete_sequence=["#00d4ff"])
                st.plotly_chart(fig_sub, use_container_width=True)
            else:
                st.info("No candidate data available.")

        with gene_c2:
            st.markdown("#### 🎯 True Target Frequency")
            truths = gene_analysis.get("most_frequent_truths", [])
            if truths:
                truth_df = pd.DataFrame(truths)
                fig_truth = px.bar(truth_df, x="gene", y="count", title="True Target Distribution",
                                   template="plotly_dark", color_discrete_sequence=["#238636"])
                st.plotly_chart(fig_truth, use_container_width=True)
            else:
                st.info("No truth data available.")

        # Overlap analysis
        st.markdown("#### 🔍 Candidate vs Truth Overlap")
        submitted_set = {g["gene"] for g in submitted} if submitted else set()
        truth_set = {g["gene"] for g in truths} if truths else set()
        overlap = submitted_set & truth_set
        if overlap:
            chips = " ".join([f'<span class="gene-chip">{g}</span>' for g in sorted(overlap)])
            st.markdown(f"**Hits:** {chips}", unsafe_allow_html=True)
        missed = truth_set - submitted_set
        if missed:
            chips_miss = " ".join([f'<span class="gene-chip-miss">{g}</span>' for g in sorted(missed)])
            st.markdown(f"**Missed:** {chips_miss}", unsafe_allow_html=True)
        if not overlap and not missed:
            st.info("No gene overlap data to display.")

    # ── Tab 3: Episode Table ──
    with tab_episodes:
        display_cols = ["episode", "success", "score", "reward", "steps", "final_confidence",
                        "experiments_done", "kg_nodes", "true_targets", "submitted_candidates"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[available].style.applymap(
                lambda v: "background-color: #1a3a1a" if v is True else ("background-color: #3a1a1a" if v is False else ""),
                subset=["success"] if "success" in available else []
            ),
            use_container_width=True,
            height=450,
        )

    # ── Tab 4: Best / Worst ──
    with tab_best_worst:
        bw1, bw2 = st.columns(2)
        with bw1:
            st.markdown("#### 🏆 Best Episode")
            if best_ep.get("episode"):
                st.markdown(f"""
<div class="report-card">
    <h3>Episode #{best_ep.get('episode', '?')}</h3>
    <p><b>Score:</b> {best_ep.get('score', 0):.3f} &nbsp;|&nbsp; <b>Reward:</b> {best_ep.get('reward', 0):.1f}</p>
    <p><b>True Targets:</b> {', '.join(best_ep.get('true_targets', []))}</p>
    <p><b>Submitted:</b> {', '.join(best_ep.get('submitted', []))}</p>
</div>
""", unsafe_allow_html=True)
            else:
                st.info("No best episode data.")

        with bw2:
            st.markdown("#### 💀 Worst Episode")
            if worst_ep.get("episode"):
                st.markdown(f"""
<div class="fail-card">
    <h3>Episode #{worst_ep.get('episode', '?')}</h3>
    <p><b>Score:</b> {worst_ep.get('score', 0):.3f} &nbsp;|&nbsp; <b>Reward:</b> {worst_ep.get('reward', 0):.1f}</p>
    <p><b>True Targets:</b> {', '.join(worst_ep.get('true_targets', []))}</p>
    <p><b>Submitted:</b> {', '.join(worst_ep.get('submitted', []))}</p>
</div>
""", unsafe_allow_html=True)
            else:
                st.info("No worst episode data.")

        # Per-episode action timeline for best episode
        if best_ep.get("episode"):
            best_idx = best_ep["episode"] - 1
            if best_idx < len(episodes) and "action_history" in episodes[best_idx]:
                st.markdown("#### 🔬 Best Episode — Action Timeline")
                action_df = pd.DataFrame(episodes[best_idx]["action_history"])
                action_names = {0: "Microarray", 1: "qPCR", 2: "Refine", 3: "Literature", 4: "Combine", 5: "Submit"}
                action_df["action_name"] = action_df["action"].map(action_names)
                fig_timeline = px.scatter(action_df, x="step", y="confidence", color="action_name",
                                          size=[8]*len(action_df),
                                          hover_data=["gene_tested", "reward"],
                                          title="Confidence Trajectory with Actions",
                                          template="plotly_dark")
                fig_timeline.update_layout(xaxis_title="Step", yaxis_title="Confidence")
                st.plotly_chart(fig_timeline, use_container_width=True)

    # ── Tab 5: Console Logs ──
    with tab_logs:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
                recent_logs = "".join(lines[-80:])
            st.code(recent_logs, language="text")
            if st.button("🔄 Refresh Logs"):
                st.rerun()
        else:
            st.info("No logs found. Run a simulation first.")

else:
    st.info("No simulation data found. Configure your scenario in the sidebar and click **▶ RUN SIMULATION**.")

    # Show live logs even without results
    st.markdown("---")
    st.subheader("📟 Console Logs")
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            recent_logs = "".join(lines[-50:])
        st.code(recent_logs, language="text")

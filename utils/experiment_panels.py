"""
GenomIQ — Real-Time Experiment Dashboard Panels

Premium HTML generators for visualizing the full RL loop:
  State → Action → Reward → Learning
"""


def build_trace_html(entries, header_html=None):
    """Terminal-like log container for research trace."""
    if header_html is None:
        header_html = '<div style="font-family:Inter,sans-serif;color:var(--body-text-color-subdued);padding:10px;text-align:center;font-size:12px;">Ready to begin research simulation...</div>'
    return f'<div class="research-log-container" id="terminal-log-scroller">{header_html}{"".join(entries)}</div>'


def build_loading_html(domain="gene_expression", agent="greedy", episodes=10,
                       max_steps=50, phase="init"):
    """Animated loading panel shown during simulation startup."""
    if phase == "init":
        status = "Initializing Environment"
        detail = f"Setting up {domain} simulation with {agent} agent..."
        progress = 10
    elif phase == "running":
        status = "Simulation Active"
        detail = f"Running {episodes} episodes × {max_steps} steps..."
        progress = 50
    else:
        status = "Finalizing Results"
        detail = "Computing metrics and building summary..."
        progress = 90

    return f"""
    <div style="font-family:'Inter',sans-serif;background:rgba(99,102,241,0.04);
                border:1px solid rgba(99,102,241,0.12);border-radius:14px;
                padding:32px 28px;text-align:center;" class="sim-active">
      <!-- Spinner -->
      <div style="margin:0 auto 16px;">
        <div class="spinner" style="width:36px;height:36px;border-width:3px;margin:0 auto;"></div>
      </div>
      <!-- Status -->
      <div style="font-size:16px;font-weight:700;color:#6366f1;margin-bottom:6px;">
        {status}</div>
      <div style="font-size:13px;color:var(--body-text-color-subdued);margin-bottom:20px;">{detail}</div>
      <!-- Progress bar with stripes -->
      <div style="max-width:320px;margin:0 auto;">
        <div style="background:var(--border-color-primary);border-radius:6px;height:8px;overflow:hidden;">
          <div class="progress-animated"
               style="background:linear-gradient(90deg,#6366f1,#8b5cf6);height:100%;
                      width:{progress}%;border-radius:6px;transition:width 0.5s ease;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px;
                    font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
          <span>Init</span>
          <span>Simulate</span>
          <span>Analyze</span>
        </div>
      </div>
      <!-- Skeleton shimmer bars -->
      <div style="margin-top:24px;display:flex;gap:10px;justify-content:center;">
        <div class="shimmer-loading" style="width:80px;height:8px;border-radius:4px;"></div>
        <div class="shimmer-loading" style="width:120px;height:8px;border-radius:4px;"></div>
        <div class="shimmer-loading" style="width:60px;height:8px;border-radius:4px;"></div>
      </div>
    </div>"""


def build_metrics_bar(step=0, max_steps=50, conf=0.0, exp_count=0,
                      cum_reward=0.0, explore_pct=50.0):
    """6-KPI horizontal metrics bar with animated gauges."""
    budget = max(0, max_steps - step)
    conf_pct = min(100, conf * 100)
    rew_sign = "+" if cum_reward >= 0 else ""
    rew_color = "#10b981" if cum_reward >= 0 else "#ef4444"
    if explore_pct > 60:
        phase, pc = "Exploring", "#0ea5e9"
    elif explore_pct > 40:
        phase, pc = "Balanced", "#f59e0b"
    else:
        phase, pc = "Exploiting", "#10b981"

    return f"""
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;font-family:'Inter',sans-serif;">
      <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#6366f1;">{step}</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Step</div>
      </div>
      <div style="background:rgba(100,116,139,0.06);border:1px solid rgba(100,116,139,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:26px;font-weight:800;color:var(--body-text-color);">{budget}</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Budget Left</div>
      </div>
      <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#6366f1;">{conf_pct:.0f}%</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Confidence</div>
        <div style="background:var(--border-color-primary);border-radius:3px;height:3px;margin-top:6px;overflow:hidden;">
          <div style="background:#6366f1;height:100%;width:{conf_pct}%;border-radius:3px;
                      transition:width 0.3s;"></div>
        </div>
      </div>
      <div style="background:rgba(139,92,246,0.06);border:1px solid rgba(139,92,246,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:26px;font-weight:800;color:#8b5cf6;">{exp_count}</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Experiments</div>
      </div>
      <div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:26px;font-weight:800;color:{rew_color};">{rew_sign}{cum_reward:.1f}</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Reward</div>
      </div>
      <div style="background:rgba(14,165,233,0.06);border:1px solid rgba(14,165,233,0.12);
                  border-radius:10px;padding:14px 12px;text-align:center;">
        <div style="font-size:22px;font-weight:800;color:{pc};">{phase}</div>
        <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1.5px;
                    font-weight:600;margin-top:3px;">Strategy</div>
        <div style="background:var(--border-color-primary);border-radius:3px;height:3px;margin-top:6px;overflow:hidden;">
          <div style="background:{pc};height:100%;width:{explore_pct}%;border-radius:3px;
                      transition:width 0.3s;"></div>
        </div>
      </div>
    </div>"""


def build_rl_state_panel(step=0, action_name="—", gene="—", is_hit=None,
                         conf=0.0, conf_prev=0.0, reward=0.0, cum_reward=0.0,
                         genes_count=0, total_genes=30, hypothesis="No hypothesis formed",
                         candidates=None, kg_nodes=0):
    """3-column RL loop panel: STATE | ACTION | REWARD."""
    if candidates is None:
        candidates = []
    conf_pct = conf * 100

    # Candidate gene chips
    cand_chips = " ".join(
        f'<span style="background:#eef2ff;color:#4338ca;padding:2px 8px;border-radius:10px;'
        f'font-size:11px;font-family:JetBrains Mono,monospace;margin:1px;">{g}</span>'
        for g in candidates[:4]
    ) or '<span style="color:var(--body-text-color-subdued);font-size:12px;">None yet</span>'

    # Pretty action name
    adn = (action_name.replace("run_experiment_A (microarray scan)", "Microarray Scan")
           .replace("run_experiment_B (qPCR validation)", "qPCR Validation")
           .replace("refine_hypothesis", "Refine Hypothesis")
           .replace("read_literature (oracle)", "Literature Review")
           .replace("combine_results", "Data Synthesis")
           .replace("submit_discovery", "Submit Discovery").strip()) or "—"

    # Exploration vs exploitation
    is_explore = any(k in action_name for k in ("experiment_A", "microarray", "literature", "read_"))
    at_label = "Exploration" if is_explore else "Exploitation"
    at_color = "#0ea5e9" if is_explore else "#10b981"

    # Reasoning sentence
    reasons = {
        "microarray": "Scanning gene space for differential expression signals",
        "experiment_A": "Scanning gene space for differential expression signals",
        "qPCR": f"Validating {gene} with high-precision measurement",
        "experiment_B": f"Validating {gene} with high-precision measurement",
        "refine": "Ranking accumulated evidence to update hypothesis",
        "literature": "Consulting published research for directional guidance",
        "combine": "Synthesizing experimental data into knowledge graph",
        "submit": f"Submitting discovery at {conf_pct:.0f}% confidence",
    }
    why = "Initializing experiment environment..."
    for k, v in reasons.items():
        if k in action_name:
            why = v
            break

    # Hit badge
    if is_hit is True:
        hb = '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">HIT</span>'
    elif is_hit is False:
        hb = '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">MISS</span>'
    else:
        hb = ""

    # Reward colors
    rc = "#10b981" if reward >= 0 else "#ef4444"
    rs = "+" if reward >= 0 else ""
    cc = "#10b981" if cum_reward >= 0 else "#ef4444"
    cs = "+" if cum_reward >= 0 else ""

    # Confidence delta
    delta = conf - conf_prev
    if delta > 0.001:
        cd = f'<span style="color:#10b981;font-size:12px;font-weight:600;">▲ +{delta:.2f}</span>'
    elif delta < -0.001:
        cd = f'<span style="color:#ef4444;font-size:12px;font-weight:600;">▼ {delta:.2f}</span>'
    else:
        cd = '<span style="color:var(--body-text-color-subdued);font-size:12px;">—</span>'

    coverage = min(100, (genes_count / max(total_genes, 1)) * 100)

    return f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;font-family:'Inter',sans-serif;">
      <!-- STATE -->
      <div style="background:rgba(99,102,241,0.03);border:1px solid rgba(99,102,241,0.12);
                  border-radius:12px;padding:18px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;">
          <div style="width:6px;height:6px;border-radius:50%;background:#6366f1;"></div>
          <span style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;
                       letter-spacing:1.2px;">State</span>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Hypothesis</div>
          <div style="font-size:12px;color:var(--body-text-color);line-height:1.5;min-height:32px;">
            {hypothesis[:120]}</div>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Confidence</div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;font-weight:700;color:#6366f1;">{conf_pct:.0f}%</span>
            {cd}
          </div>
          <div style="background:var(--border-color-primary);border-radius:3px;height:5px;margin-top:4px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);height:100%;
                        width:{conf_pct}%;border-radius:3px;transition:width 0.3s;"></div>
          </div>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Active Candidates</div>
          <div style="display:flex;flex-wrap:wrap;gap:3px;">{cand_chips}</div>
        </div>
        <div style="display:flex;gap:20px;">
          <div>
            <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:0.8px;">
                Coverage</div>
            <div style="font-size:14px;font-weight:700;color:var(--body-text-color);">{coverage:.0f}%</div>
          </div>
          <div>
            <div style="font-size:9px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:0.8px;">
                KG Nodes</div>
            <div style="font-size:14px;font-weight:700;color:var(--body-text-color);">{kg_nodes}</div>
          </div>
        </div>
      </div>

      <!-- ACTION -->
      <div style="background:rgba(139,92,246,0.03);border:1px solid rgba(139,92,246,0.12);
                  border-radius:12px;padding:18px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;">
          <div style="width:6px;height:6px;border-radius:50%;background:#8b5cf6;"></div>
          <span style="font-size:11px;font-weight:700;color:#8b5cf6;text-transform:uppercase;
                       letter-spacing:1.2px;">Action</span>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Chosen Action</div>
          <div style="font-size:15px;font-weight:700;color:var(--body-text-color);">{adn}</div>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Target Gene</div>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:14px;font-weight:600;color:#6366f1;
                         font-family:JetBrains Mono,monospace;">{gene}</span>
            {hb}
          </div>
        </div>
        <div style="margin-bottom:10px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Reasoning</div>
          <div style="font-size:12px;color:var(--body-text-color-subdued);line-height:1.5;">{why}</div>
        </div>
        <div>
          <span style="background:rgba({_at_rgb(at_color)},0.12);color:{at_color};
                       padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;">
            {at_label}</span>
        </div>
      </div>

      <!-- REWARD -->
      <div style="background:rgba(16,185,129,0.03);border:1px solid rgba(16,185,129,0.12);
                  border-radius:12px;padding:18px;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;">
          <div style="width:6px;height:6px;border-radius:50%;background:#10b981;"></div>
          <span style="font-size:11px;font-weight:700;color:#10b981;text-transform:uppercase;
                       letter-spacing:1.2px;">Reward</span>
        </div>
        <div style="margin-bottom:14px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Immediate</div>
          <div style="font-size:30px;font-weight:800;color:{rc};">{rs}{reward:.1f}</div>
        </div>
        <div style="margin-bottom:14px;">
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Cumulative</div>
          <div style="font-size:20px;font-weight:700;color:{cc};">{cs}{cum_reward:.1f}</div>
        </div>
        <div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:6px;">Breakdown</div>
          <div style="display:flex;justify-content:space-between;font-size:11px;margin:3px 0;">
            <span style="color:var(--body-text-color-subdued);">Signal quality</span>
            <span style="color:{rc};font-weight:600;">{rs}{reward + 0.1:.1f}</span>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;margin:3px 0;">
            <span style="color:var(--body-text-color-subdued);">Step cost</span>
            <span style="color:#ef4444;font-weight:600;">−0.1</span>
          </div>
        </div>
      </div>
    </div>"""


def _at_rgb(hex_color):
    """Convert hex to r,g,b string."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def build_progress_html(step=0, max_steps=50, ep_num=0, total_eps=10,
                        explore_count=0, exploit_count=0):
    """Episode progress bar with explore/exploit ratio."""
    # Overall progress based on episodes completed (ep_num is current, so ep_num-1 are done)
    completed = max(0, ep_num - 1)
    step_frac = step / max(max_steps, 1)  # fraction of current episode done
    overall_pct = min(100, ((completed + step_frac) / max(total_eps, 1)) * 100)
    step_pct = min(100, step_frac * 100)
    total = max(explore_count + exploit_count, 1)
    ex_pct = (explore_count / total) * 100

    return f"""
    <div style="font-family:'Inter',sans-serif;background:var(--background-fill-secondary);
                border:1px solid var(--border-color-primary);border-radius:10px;padding:16px 20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="width:7px;height:7px;border-radius:50%;background:#6366f1;" class="live-dot"></div>
          <span style="font-size:12px;font-weight:700;color:var(--body-text-color);">
            Episode {ep_num}/{total_eps}</span>
        </div>
        <span style="font-size:12px;color:var(--body-text-color-subdued);">
          Step {step}/{max_steps} &middot; {overall_pct:.0f}% overall</span>
      </div>
      <div style="background:var(--border-color-primary);border-radius:4px;height:8px;overflow:hidden;margin-bottom:10px;">
        <div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);height:100%;
                    width:{overall_pct}%;border-radius:4px;transition:width 0.3s ease;"></div>
      </div>
      <div style="display:flex;gap:24px;font-size:11px;">
        <div style="display:flex;align-items:center;gap:4px;">
          <div style="width:8px;height:8px;border-radius:2px;background:#0ea5e9;"></div>
          <span style="color:var(--body-text-color-subdued);">Explore {explore_count}</span>
        </div>
        <div style="display:flex;align-items:center;gap:4px;">
          <div style="width:8px;height:8px;border-radius:2px;background:#10b981;"></div>
          <span style="color:var(--body-text-color-subdued);">Exploit {exploit_count}</span>
        </div>
        <div style="flex:1;background:var(--border-color-primary);border-radius:3px;height:6px;overflow:hidden;
                    align-self:center;">
          <div style="background:linear-gradient(90deg,#0ea5e9 0%,#0ea5e9 {ex_pct}%,
                      #10b981 {ex_pct}%,#10b981 100%);height:100%;border-radius:3px;"></div>
        </div>
      </div>
    </div>"""


def build_thinking_html(action_name="—", gene="—", is_hit=None, conf=0.0,
                        message="Preparing simulation environment..."):
    """AI scientist reasoning panel — natural language interpretation."""
    # Auto-generate reasoning if no custom message
    if message == "" or message is None:
        if "submit" in action_name:
            message = f"I've gathered sufficient evidence. Submitting discovery with {conf*100:.0f}% confidence."
        elif is_hit is True:
            message = (f"Strong signal detected on {gene}! This gene shows differential expression "
                       f"consistent with the target pattern. Confidence rising to {conf*100:.0f}%. "
                       f"I should validate this with qPCR to confirm.")
        elif is_hit is False:
            message = (f"Tested {gene} but found no significant signal. This gene is likely not part "
                       f"of the target pattern. I need to explore other candidates.")
        elif "refine" in action_name:
            message = (f"Analyzing all accumulated experimental data to rank gene candidates. "
                       f"Confidence now at {conf*100:.0f}%. The top candidates are becoming clearer.")
        elif "literature" in action_name:
            message = "Consulting published research to narrow the search space and identify promising leads."
        elif "combine" in action_name:
            message = "Synthesizing results into a knowledge graph to identify gene interaction patterns."
        else:
            message = (f"Currently at {conf*100:.0f}% confidence. Continuing systematic exploration "
                       f"of the gene space to identify differential expression patterns.")

    dot_color = "#10b981" if conf > 0.6 else ("#f59e0b" if conf > 0.3 else "#6366f1")

    return f"""
    <div style="font-family:'Inter',sans-serif;background:rgba(99,102,241,0.03);
                border:1px solid rgba(99,102,241,0.1);border-radius:12px;padding:18px 20px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <div style="width:7px;height:7px;border-radius:50%;background:{dot_color};"
             class="live-dot"></div>
        <span style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;
                     letter-spacing:1.2px;">AI Scientist Reasoning</span>
      </div>
      <div style="font-size:13px;color:var(--body-text-color);line-height:1.7;font-style:italic;">
        "{message}"
      </div>
    </div>"""


def build_run_summary_html(data=None):
    """Structured run summary — replaces raw JSON output."""
    if not data:
        return """
        <div style="text-align:center;padding:40px;color:var(--body-text-color-subdued);font-family:'Inter',sans-serif;">
          <div style="font-size:36px;margin-bottom:12px;opacity:0.2;">◇</div>
          <div style="font-size:13px;font-weight:500;">Run a simulation to see structured results</div>
        </div>"""

    m = data.get("metrics", {})
    meta = data.get("run_metadata", {})
    episodes = data.get("episodes", [])
    genes = data.get("gene_analysis", {}).get("most_submitted_candidates", [])

    sr = m.get("success_rate", 0)
    sr_color = "#10b981" if sr >= 0.6 else ("#f59e0b" if sr >= 0.3 else "#ef4444")

    # Find best discovery
    best_ep = max(episodes, key=lambda e: e.get("score", 0)) if episodes else {}
    best_gene = ""
    if best_ep:
        subs = best_ep.get("submitted_candidates", [])
        truths = set(best_ep.get("true_targets", []))
        for g in subs:
            if g in truths:
                best_gene = g
                break
        if not best_gene and subs:
            best_gene = subs[0]

    top_gene = genes[0]["gene"] if genes else "—"

    # Final hypothesis from best episode
    hyp_hist = best_ep.get("hypothesis_history", []) if best_ep else []
    final_hyp = hyp_hist[-1]["hypothesis"] if hyp_hist else "No hypothesis recorded"

    return f"""
    <div style="font-family:'Inter',sans-serif;background:var(--background-fill-secondary);
                border:1px solid var(--border-color-primary);border-radius:12px;padding:20px;">
      <div style="font-size:12px;font-weight:700;color:#6366f1;text-transform:uppercase;
                  letter-spacing:1.2px;margin-bottom:16px;">Run Summary</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:16px;">
        <div style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:{sr_color};">{sr*100:.0f}%</div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
            Success Rate</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:#6366f1;">{m.get('avg_reward', 0):.1f}</div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
            Avg Reward</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:#8b5cf6;">{m.get('avg_score', 0):.3f}</div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
            Avg Score</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:28px;font-weight:800;color:var(--body-text-color);">{m.get('avg_steps', 0):.0f}</div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;">
            Avg Steps</div>
        </div>
      </div>
      <div style="border-top:1px solid rgba(148,163,184,0.15);padding-top:14px;
                  display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Key Discovery</div>
          <span style="background:#eef2ff;color:#4338ca;padding:3px 10px;border-radius:10px;
                       font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">
            {best_gene or '—'}</span>
          <span style="color:var(--body-text-color-subdued);font-size:12px;margin-left:6px;">
            Score: {best_ep.get('score', 0):.3f}</span>
        </div>
        <div>
          <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                      margin-bottom:3px;">Most Investigated</div>
          <span style="background:var(--background-fill-secondary);color:var(--body-text-color);padding:3px 10px;border-radius:10px;
                       font-size:12px;font-weight:600;font-family:JetBrains Mono,monospace;">
            {top_gene}</span>
        </div>
      </div>
      <div style="border-top:1px solid rgba(148,163,184,0.15);padding-top:12px;margin-top:12px;">
        <div style="font-size:10px;color:var(--body-text-color-subdued);text-transform:uppercase;letter-spacing:1px;
                    margin-bottom:4px;">Final Hypothesis</div>
        <div style="font-size:12px;color:var(--body-text-color);line-height:1.5;">{final_hyp[:200]}</div>
      </div>
    </div>"""

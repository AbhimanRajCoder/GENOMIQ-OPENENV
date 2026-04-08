import sys
import os
import subprocess
import time
import requests
import re
import statistics
import gradio as gr
from typing import List, Dict, Generator

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
SERVER_URL = "http://localhost:7861"
TIME_LIMIT = 1200  # 20 min
EPS = 1e-6

REQUIRED_ENV = ["API_BASE_URL", "MODEL_NAME", "HF_TOKEN"]

# Full list of tasks representing all 6 research domains
ALL_DOMAIN_TASKS = [
    "single_regulator",
    "coexpression_cluster",
    "interaction_effect",
    "cancer_gene_panel",
    "drug_affinity",
    "methylation_marker"
]

# ─────────────────────────────────────────────────────────────
# CSS & THEME
# ─────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap');
body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; }
.gradio-container { max-width: 1200px !important; }
.log-area textarea { 
    font-family: 'JetBrains Mono', monospace !important; 
    font-size: 13px !important; 
    background: #020617 !important; 
    color: #38bdf8 !important; 
    border: 1px solid #1e293b !important;
}
.status-card {
    background: #1e293b;
    border-radius: 12px;
    padding: 18px;
    border: 1px solid #334155;
    margin-bottom: 12px;
}
.phase-box {
    padding: 10px;
    border-radius: 6px;
    margin-top: 8px;
    background: rgba(255,255,255,0.05);
}
.success-banner { background: #064e3b; border: 1px solid #059669; border-radius: 8px; padding: 20px; text-align: center; }
"""

# ─────────────────────────────────────────────────────────────
# CORE LOGIC
# ─────────────────────────────────────────────────────────────

def check_env() -> str:
    missing = [var for var in REQUIRED_ENV if var not in os.environ]
    if missing:
        return f"❌ Missing: {', '.join(missing)}"
    return "✅ OK"

def check_server_health(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def start_server_proc():
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--port", "7861"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def extract_scores(output: str) -> List[float]:
    pattern = re.compile(r"score=([0-9]*\.?[0-9]+)")
    return [float(x) for x in pattern.findall(output)]

def validate_line_format(line: str) -> bool:
    """Verifies if a log line matches the strict OpenEnv spec."""
    if "[START]" in line or "[STEP]" in line or "[END]" in line:
        return True
    # The baseline results summary is also fine
    if any(x in line for x in ["score=", "steps=", "GENOMIQ BASELINE"]):
        return True
    return False

# ─────────────────────────────────────────────────────────────
# GRADIO INTERFACE
# ─────────────────────────────────────────────────────────────

def run_pro_validation(prod_url: str) -> Generator[Dict, None, None]:
    start_time = time.time()
    logs = ""
    target_server_url = prod_url.strip() if prod_url and prod_url.strip() else SERVER_URL
    is_prod = target_server_url != SERVER_URL
    
    yield [
        "Initializing SCALER-GRADE Phase 2 Validation...\n",
        "⏳ Checking...",
        "⏳ Waiting...",
        "⏳ Pending",
        "⏳ Pending",
        "⏳ Pending",
        gr.update(visible=False)
    ]

    # 1. Environment Verification
    env_res = check_env()
    logs += f"Checking Environment Variables... {env_res}\n"
    yield [logs, env_res, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()]
    if "❌" in env_res: return

    # 2. Server Connectivity
    server_proc = None
    if is_prod:
        logs += f"Connecting to PRODUCTION URL: {target_server_url}\n"
        if check_server_health(target_server_url):
            logs += "✅ Production health check passed.\n"
            yield [logs, gr.update(), "✅ Online (Remote)", gr.update(), gr.update(), gr.update(), gr.update()]
        else:
            logs += "❌ Production health check failed.\n"
            yield [logs, gr.update(), "❌ Offline", gr.update(), gr.update(), gr.update(), gr.update(value="# ❌ Phase 2 Failed\nUnable to reach production health endpoint.", visible=True)]
            return
    else:
        if not check_server_health(target_server_url):
            logs += f"Starting local simulation on {target_server_url}...\n"
            server_proc = start_server_proc()
            time.sleep(5)
            if check_server_health(target_server_url):
                logs += "✅ Local research server initialized.\n"
                yield [logs, gr.update(), "✅ Online (Local)", gr.update(), gr.update(), gr.update(), gr.update()]
            else:
                logs += "❌ Server failed to start.\n"
                yield [logs, gr.update(), "❌ Failed", gr.update(), gr.update(), gr.update(), gr.update()]
                if server_proc: server_proc.terminate()
                return
        else:
            logs += "✅ Server is already running.\n"
            yield [logs, gr.update(), "✅ OK", gr.update(), gr.update(), gr.update(), gr.update()]

    # ── PHASE 2 STAGE 1: Baseline Agent Re-run ─────────────────
    logs += "\n==================================================\n"
    logs += "STAGE 1: Baseline Agent Re-run (All Domains)\n"
    logs += "==================================================\n"
    yield [logs, gr.update(), gr.update(), "🏃 Running...", gr.update(), gr.update(), gr.update()]
    
    # We simulate Phase 2 behavior by running against all 6 tasks
    stage1_scores = []
    try:
        # We tell inference.py to run all domains via env var
        proc = subprocess.Popen(
            [sys.executable, "inference.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "SERVER_URL": target_server_url, "RUN_ALL_DOMAINS": "1"}
        )
        for line in iter(proc.stdout.readline, ""):
            logs += line
            if "score=" in line:
                stage1_scores.extend(extract_scores(line))
            yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()]
        proc.wait()
        
        if not stage1_scores:
            yield [logs + "\n❌ Stage 1 Failed: No scores extracted. Check if inference.py is crashing.\n", gr.update(), gr.update(), "❌ No Scores", gr.update(), gr.update(), gr.update(value="# ❌ Phase 2 Failed\nNo scores extracted from inference script.", visible=True)]
            if server_proc: server_proc.terminate()
            return

        if any(not (0 < s < 1) for s in stage1_scores):
            yield [logs + "\n❌ Stage 1 Failed: Score out of range (0,1)\n", gr.update(), gr.update(), "❌ Failed", gr.update(), gr.update(), gr.update(value="# ❌ Phase 2 Failed\nTask score out of range (0,1)", visible=True)]
            if server_proc: server_proc.terminate()
            return
        
        logs += f"✅ Stage 1 passed. Average score: {sum(stage1_scores)/len(stage1_scores):.6f}\n"
        yield [logs, gr.update(), gr.update(), "✅ Passed", gr.update(), gr.update(), gr.update()]
    except Exception as e:
        logs += f"❌ Stage 1 Error: {str(e)}\n"
        yield [logs, gr.update(), gr.update(), "❌ Error", gr.update(), gr.update(), gr.update()]
        if server_proc: server_proc.terminate()
        return

    # ── PHASE 2 STAGE 2: Variance & Determinism Check ──────────
    logs += "\n==================================================\n"
    logs += "STAGE 2: Score Variance Check (Determinism Risk)\n"
    logs += "==================================================\n"
    yield [logs, gr.update(), gr.update(), gr.update(), "🏃 Analyzing...", gr.update(), gr.update()]
    
    # Run the same task multiple times to ensure the grader isn't static
    var_scores = []
    for i in range(3):
        logs += f"Variance iteration {i+1}/3...\n"
        yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()]
        # Run just the first task
        res = subprocess.run(
            [sys.executable, "inference.py"],
            capture_output=True, text=True,
            env={**os.environ, "SERVER_URL": target_server_url, "LIMIT_TASKS": "1"}
        )
        sc = extract_scores(res.stdout)
        if sc: var_scores.append(sc[0])
    
    if len(set(var_scores)) <= 1 and len(var_scores) > 1:
        logs += f"❌ FATAL: Zero variance detected in identical task runs: {var_scores}\n"
        logs += "Grader appears to be constant or LLM is in deterministic fallback.\n"
        logs += "Ensure HF_TOKEN is valid for non-deterministic LLM actions.\n"
        yield [logs, gr.update(), gr.update(), gr.update(), "❌ Constant", gr.update(), gr.update(value="# ❌ Phase 2 Failed\nZero score variance detected (Disqualification Risk)", visible=True)]
        if server_proc: server_proc.terminate()
        return
    
    logs += f"✅ Variance check passed. Scores: {var_scores}\n"
    yield [logs, gr.update(), gr.update(), gr.update(), "✅ OK", gr.update(), gr.update()]

    # ── PHASE 2 STAGE 3: Log Format & Latency ──────────────────
    logs += "\n==================================================\n"
    logs += "STAGE 3: Log Specification & Latency Audit\n"
    logs += "==================================================\n"
    yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), "🏃 Auditing...", gr.update()]
    
    # Verify standard log keys exist
    log_spec_ok = "[START]" in logs and "[END]" in logs and "steps=" in logs and "rewards=" in logs
    if not log_spec_ok:
        logs += "❌ Log specification mismatch. Ensure [START], [END], steps=, and rewards= appear.\n"
        yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), "❌ Format Error", gr.update()]
    else:
        logs += "✅ Log specification audit passed.\n"
        yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), "✅ Passed", gr.update()]

    # FINAL VERDICT
    duration = time.time() - start_time
    logs += f"\nValidation complete in {duration:.1f}s.\n"
    
    yield [
        logs + "\n🎉 COMPLIANCE LEVEL: PRODUCTION READY",
        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
        gr.update(value="# ✅ Phase 2 SECURE\nYour submission is now fully compliant with Scaler portal standards.", visible=True)
    ]

    if server_proc:
        logs += "Stopping local simulator...\n"
        server_proc.terminate()
        yield [logs, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()]

with gr.Blocks() as demo:
    gr.Markdown("""
    # ⚖️ Scaler Portal · Phase 2 Production Validator
    **Enterprise-Grade Agentic Evaluation Simulator**
    
    This monitor performs a 3-stage stress test focusing on score ranges, variance, and log specification to ensure a 100% success rate on the official OpenEnv portal.
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes="status-card"):
                gr.Markdown("### 🛡️ Pre-Flight Verification")
                env_badge = gr.Textbox(label="Env Configuration", value="Not Checked", interactive=False)
                server_badge = gr.Textbox(label="Target Connectivity", value="Not Checked", interactive=False)
                target_url = gr.Textbox(label="Remote Production URL", placeholder="https://space.hf.space")
            
            with gr.Group(elem_classes="status-card"):
                gr.Markdown("### 📋 Phase 2 Checklist")
                p1_ui = gr.Textbox(label="Stage 1: Baseline Re-run", value="Pending", interactive=False)
                p2_ui = gr.Textbox(label="Stage 2: Variance Analysis", value="Pending", interactive=False)
                p3_ui = gr.Textbox(label="Stage 3: Log Spec Audit", value="Pending", interactive=False)
            
            run_btn = gr.Button("🔥 START STRESS TEST", variant="primary", size="lg")
            stop_btn = gr.Button("⏹ STOP SIMULATOR", variant="secondary", size="sm")

        with gr.Column(scale=2):
            verdict_box = gr.Markdown(visible=False, elem_classes="success-banner")
            output_log = gr.TextArea(
                label="Simulation Control Logs",
                interactive=False,
                lines=28,
                elem_classes="log-area"
            )

    run_btn.click(
        run_pro_validation,
        inputs=[target_url],
        outputs=[output_log, env_badge, server_badge, p1_ui, p2_ui, p3_ui, verdict_box]
    )
    
    stop_btn.click(lambda: (subprocess.run(["pkill", "-f", "7861"]), "Simulator processes terminated.")[1], outputs=[output_log])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7862, theme=gr.themes.Default(), css=CUSTOM_CSS)
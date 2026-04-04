"""
GenomIQ — AI Scientist Chat Interface.

Hybrid Mode:
  - Mode A (LLM): Rich conversational responses via OpenAI client
  - Mode B (Deterministic): Template-based responses from experiment data

Always works — no external dependency required.
"""

import json
import os
from pathlib import Path
from typing import Optional

# ── Auto-load .env / .env.example if HF_TOKEN not in environment ─────────────
def _load_env_token():
    """Try to load HF_TOKEN from .env or .env.example if not already set."""
    if os.getenv("HF_TOKEN"):
        return
    for env_file in [".env", ".env.example"]:
        p = Path(env_file)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line.startswith("HF_TOKEN=") and not line.startswith("#"):
                    token = line.split("=", 1)[1].strip()
                    if token and not token.startswith("your_"):
                        os.environ["HF_TOKEN"] = token
                        print(f"[AI Scientist] Loaded HF_TOKEN from {env_file}")
                        return
                if line.startswith("API_BASE_URL=") and not os.getenv("API_BASE_URL"):
                    os.environ["API_BASE_URL"] = line.split("=", 1)[1].strip()
                if line.startswith("MODEL_NAME=") and not os.getenv("MODEL_NAME"):
                    os.environ["MODEL_NAME"] = line.split("=", 1)[1].strip()

_load_env_token()


# ── Deterministic response templates ──────────────────────────────────────────

def _build_context_summary(data: dict) -> str:
    """Build a rich experiment summary for LLM context."""
    if not data:
        return "No experiment data available."

    metrics = data.get("metrics", {})
    meta = data.get("run_metadata", {})
    episodes = data.get("episodes", [])

    confirmed = set()
    all_tested = {}
    hints_collected = []
    for ep in episodes:
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            confirmed |= (sub & truth)
        hint = ep.get("last_hint", "")
        if hint:
            hints_collected.append(hint)
        for act in ep.get("action_history", []):
            g = act.get("gene_tested", "")
            if g and g != "—":
                if g not in all_tested:
                    all_tested[g] = {"count": 0, "signals": []}
                all_tested[g]["count"] += 1
                all_tested[g]["signals"].append(act.get("confidence", 0))

    # Top genes by test frequency
    top_genes = sorted(all_tested.items(), key=lambda x: -x[1]["count"])[:10]
    gene_details = ""
    for g, info in top_genes:
        avg_sig = sum(info["signals"]) / max(len(info["signals"]), 1)
        is_confirmed = "CONFIRMED" if g in confirmed else "unconfirmed"
        gene_details += f"  - {g}: tested {info['count']}x, avg confidence {avg_sig:.2f}, status: {is_confirmed}\n"

    # Best episode
    best_ep = max(episodes, key=lambda e: e.get("score", 0)) if episodes else {}
    best_info = ""
    if best_ep:
        best_info = (
            f"\nBest Episode: #{best_ep.get('episode', '?')} - "
            f"Score: {best_ep.get('score', 0):.4f}, "
            f"Steps: {best_ep.get('steps', 0)}, "
            f"Targets: {', '.join(best_ep.get('true_targets', []))}"
        )

    return (
        f"Domain: {meta.get('domain', 'unknown')}\n"
        f"Difficulty: {meta.get('difficulty', 'unknown')}\n"
        f"Agent: {meta.get('agent_type', 'unknown')}\n"
        f"Episodes: {len(episodes)}\n"
        f"Success rate: {metrics.get('success_rate', 0) * 100:.1f}%\n"
        f"Avg score: {metrics.get('avg_score', 0):.4f}\n"
        f"Avg confidence: {metrics.get('avg_confidence', 0):.2f}\n"
        f"Confirmed genes: {', '.join(sorted(confirmed)) or 'None'}\n"
        f"Total unique genes tested: {len(all_tested)}\n"
        f"\nTop investigated genes:\n{gene_details}"
        f"{best_info}\n"
        f"\nLiterature hints collected: {len(hints_collected)}\n"
        + (f"Recent hints: {'; '.join(hints_collected[:3])}" if hints_collected else "")
    )


def _gene_frequency(data: dict) -> dict[str, int]:
    """Count how often each gene was tested."""
    freq = {}
    for ep in data.get("episodes", []):
        for act in ep.get("action_history", []):
            g = act.get("gene_tested", "")
            if g and g != "—":
                freq[g] = freq.get(g, 0) + 1
    return freq


def _gene_avg_signal(data: dict, gene: str) -> float:
    """Get average confidence when a specific gene was tested."""
    signals = []
    for ep in data.get("episodes", []):
        for act in ep.get("action_history", []):
            if act.get("gene_tested") == gene:
                signals.append(act.get("confidence", 0))
    return sum(signals) / max(len(signals), 1)


def _get_confirmed_genes(data: dict) -> set[str]:
    confirmed = set()
    for ep in data.get("episodes", []):
        if ep.get("success"):
            sub = set(ep.get("submitted_candidates", []))
            truth = set(ep.get("true_targets", []))
            confirmed |= (sub & truth)
    return confirmed


def _get_true_targets(data: dict) -> set[str]:
    targets = set()
    for ep in data.get("episodes", []):
        for g in ep.get("true_targets", []):
            targets.add(g)
    return targets


# ── Deterministic Q&A engine ─────────────────────────────────────────────────

def _deterministic_answer(question: str, data: dict) -> str:
    """Answer common questions using experiment statistics."""
    q = question.lower().strip()
    freq = _gene_frequency(data)
    confirmed = _get_confirmed_genes(data)
    targets = _get_true_targets(data)
    metrics = data.get("metrics", {})
    episodes = data.get("episodes", [])

    top_genes = sorted(freq.items(), key=lambda x: -x[1])[:5]

    # Q: Why this gene?
    if "why" in q and any(g in q.upper() for g in freq):
        # Find which gene they're asking about
        asked_gene = None
        for g in freq:
            if g.lower() in q.lower() or g in q:
                asked_gene = g
                break

        if asked_gene:
            count = freq.get(asked_gene, 0)
            avg_sig = _gene_avg_signal(data, asked_gene)
            is_confirmed = asked_gene in confirmed
            is_target = asked_gene in targets

            reason_parts = []
            if is_confirmed:
                reason_parts.append(f"it was successfully VALIDATED as a true target")
            if is_target:
                reason_parts.append(f"it is one of the ground-truth targets embedded in the matrix")
            reason_parts.append(f"it was tested {count} times across episodes")
            reason_parts.append(f"average confidence when tested: {avg_sig:.2f}")

            if count > sum(freq.values()) * 0.1:
                reason_parts.append("it was among the most frequently investigated genes")

            return (
                f"**{asked_gene}** was selected because:\n\n"
                + "\n".join(f"- {r}" for r in reason_parts)
                + f"\n\nOverall, {'this gene was correctly identified' if is_confirmed else 'further validation would be needed'}."
            )

    # Q: What gene / best gene / top gene
    if any(w in q for w in ["best gene", "top gene", "what gene", "which gene", "strongest"]):
        if top_genes:
            best = top_genes[0]
            avg_sig = _gene_avg_signal(data, best[0])
            return (
                f"The most investigated gene is **{best[0]}**, tested {best[1]} times.\n\n"
                f"Average confidence during testing: {avg_sig:.2f}\n"
                f"{'It was confirmed as a validated target.' if best[0] in confirmed else 'It was not validated as a true target.'}\n\n"
                f"Other top candidates: {', '.join(f'{g} ({c}×)' for g, c in top_genes[1:4])}"
            )

    # Q: What-if / knockout
    if any(w in q for w in ["what if", "knock", "remove", "without"]):
        if confirmed:
            gene = list(confirmed)[0]
            others = [g for g, _ in top_genes if g != gene][:3]
            return (
                f"**What-if Analysis: Removing {gene}**\n\n"
                f"If {gene} were knocked out of the expression matrix:\n"
                f"- The next likely candidates would be: {', '.join(others)}\n"
                f"- Predicted confidence drop: ~{metrics.get('avg_score', 0.5) * 0.4:.0%}\n"
                f"- Success rate would likely decrease from "
                f"{metrics.get('success_rate', 0) * 100:.0f}% to ~{max(5, metrics.get('success_rate', 0) * 40):.0f}%\n\n"
                f"This suggests {gene} is {'a critical regulator' if gene in targets else 'an important but non-essential factor'}."
            )

    # Q: Next experiment / suggest
    if any(w in q for w in ["next experiment", "suggest", "recommend", "what should"]):
        sr = metrics.get("success_rate", 0)
        if sr < 0.4:
            return (
                "**Recommended Next Steps:**\n\n"
                "1. Switch to **High Fidelity cost tier** for precise qPCR measurements\n"
                "2. Enable the **Literature Oracle** to guide exploration\n"
                "3. Add **seed genes** from known biology (e.g., TP53, BRCA1)\n"
                "4. Consider increasing the **episode budget** to allow deeper investigation\n\n"
                f"Current success rate ({sr*100:.0f}%) suggests the agent needs more guidance."
            )
        else:
            return (
                "**Recommended Next Steps:**\n\n"
                f"1. Cross-validate discoveries against **TCGA-BRCA** cohort data\n"
                f"2. Run a **multi-agent benchmark** to compare strategy performance\n"
                f"3. Attempt **hard difficulty** to test robustness of findings\n"
                f"4. Generate a **publishable hypothesis** from the Paper Output tab\n\n"
                f"Current success rate ({sr*100:.0f}%) indicates strong performance."
            )

    # Q: Summary / results / performance
    if any(w in q for w in ["summary", "results", "performance", "how did", "overview"]):
        return (
            f"**Experiment Summary**\n\n"
            f"- Domain: {data.get('run_metadata', {}).get('domain', '?')}\n"
            f"- Episodes: {len(episodes)}\n"
            f"- Success rate: {metrics.get('success_rate', 0) * 100:.1f}%\n"
            f"- Avg score: {metrics.get('avg_score', 0):.4f}\n"
            f"- Score range: [{metrics.get('min_score', 0):.4f} — {metrics.get('max_score', 0):.4f}]\n"
            f"- Confirmed discoveries: {', '.join(sorted(confirmed)) or 'None'}\n"
            f"- True targets: {', '.join(sorted(targets))}\n"
        )

    # Q: Confidence / how confident
    if any(w in q for w in ["confident", "confidence", "sure", "certain"]):
        avg_conf = metrics.get("avg_confidence", 0)
        return (
            f"**Confidence Analysis**\n\n"
            f"Average final confidence across episodes: {avg_conf:.2f}\n"
            f"Success rate: {metrics.get('success_rate', 0) * 100:.1f}%\n\n"
            f"{'High confidence — the agent was consistently able to identify targets.' if avg_conf > 0.7 else ''}"
            f"{'Moderate confidence — some targets were identified but with uncertainty.' if 0.4 <= avg_conf <= 0.7 else ''}"
            f"{'Low confidence — the agent struggled to converge on clear targets.' if avg_conf < 0.4 else ''}"
        )

    # Default fallback
    return (
        f"Based on the current experiment data:\n\n"
        f"- {len(episodes)} episodes were run in the **{data.get('run_metadata', {}).get('domain', '?')}** domain\n"
        f"- Success rate: {metrics.get('success_rate', 0) * 100:.1f}%\n"
        f"- Top investigated genes: {', '.join(g for g, _ in top_genes[:3])}\n\n"
        f"I can only answer questions related to our recent experiments and biological findings here. Try asking me:\n"
        f'- "Why was [gene name] selected?"\n'
        f'- "What would happen if we knocked out [gene]?"\n'
        f'- "What experiment should I run next?"\n'
        f'- "Generate a summary of results"'
    )


# ── LLM-powered Q&A engine ───────────────────────────────────────────────────

def _llm_answer(question: str, data: dict) -> Optional[str]:
    """Use LLM for rich conversational responses (requires HF_TOKEN)."""
    hf_token = os.getenv("HF_TOKEN", "")
    if not hf_token:
        print("[AI Scientist] No HF_TOKEN found — using deterministic mode")
        return None

    try:
        from openai import OpenAI

        api_base = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
        model = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
        print(f"[AI Scientist] LLM mode: {model} via {api_base}")
        client = OpenAI(base_url=api_base, api_key=hf_token)

        context = _build_context_summary(data)

        system_prompt = (
            "You are an AI Scientist working in a genomics research laboratory called GenomIQ.\n"
            "You have access to the following experiment results:\n\n"
            f"{context}\n\n"
            "Rules:\n"
            "- Answer the researcher's question based ONLY on this data.\n"
            "- Be scientific, precise, and cite specific numbers from the data.\n"
            "- If the user asks a question unrelated to the experiment, genomics, or these findings, you MUST politely refuse to answer. Say 'I am a specialized AI Scientist for GenomIQ, I can only answer questions related to our experiments.'\n"
            "- If asked 'why' a gene was selected, explain based on test frequency, signal strength, and literature hints.\n"
            "- If asked for next steps, suggest concrete experiments (ChIP-seq, TCGA cross-validation, knockdown).\n"
            "- Use markdown formatting for clarity.\n"
            "- Keep answers concise but thorough (3-8 sentences)."
        )

        response = client.chat.completions.create(
            model=model,
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        answer = response.choices[0].message.content.strip()
        print(f"[AI Scientist] LLM response received ({len(answer)} chars)")
        return answer

    except Exception as e:
        print(f"[AI Scientist] LLM call failed: {e} — falling back to deterministic")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def ask_scientist(question: str, data: dict) -> str:
    """Ask the AI Scientist a question. Hybrid: LLM first, deterministic fallback.

    Args:
        question: The user's question string.
        data: The full results JSON from latest_run.json.

    Returns:
        Markdown-formatted answer string.
    """
    if not data:
        return (
            "I don't have any experiment data to analyze yet.\n\n"
            "Please run a simulation first, then come back and ask me questions about the results."
        )

    # Try LLM first
    llm_response = _llm_answer(question, data)
    if llm_response:
        return "*[LLM Mode]*\n\n" + llm_response

    # Deterministic fallback
    print("[AI Scientist] Using deterministic fallback")
    return "*[Local Analysis Mode]*\n\n" + _deterministic_answer(question, data)


SUGGESTED_QUESTIONS = [
    "What are the top discovered genes and why?",
    "What would happen if we knocked out the primary target?",
    "What experiment should I run next?",
    "How confident are we in these discoveries?",
    "Give me a summary of the results.",
]

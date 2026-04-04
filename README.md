---
title: GenomIQ — Scientific Discovery Lab
emoji: 🔬
colorFrom: indigo
colorTo: slate
sdk: docker
sdk_version: "4.0.0"
app_file: server/app.py
pinned: false
tags:
  - openenv
  - reinforcement-learning
  - genomics
  - scientific-discovery
  - bioinformatics
---

# GenomIQ — Automated Scientific Discovery RL Environment

> An OpenEnv-compliant reinforcement learning environment for automated genomics research. GenomIQ simulates a high-fidelity laboratory where AI agents discover hidden gene expression patterns, identify drug targets, and map regulatory networks.

---

## 1. Environment Description

GenomIQ is a platform for evaluating AI agents in **automated scientific discovery**. Unlike traditional RL environments, GenomIQ models the workflow of a research scientist:
*   **Multi-Domain Engine:** 18 tasks across 6 domains (Genomics, Drug Discovery, Epigenomics, etc.).
*   **Real Data Integration:** Supports synthetic matrices, preloaded cancer panels, and custom user-uploaded CSV matrices.
*   **Experimental Constraints:** Customizable noise levels (σ), cost tiers (Fidelity), and prior knowledge (seed genes).
*   **Knowledge Graph (KG):** Observations are integrated into a persistent memory of gene interactions.
*   **Episode Cycle:** A narrative timeline illustrating the agent's journey from blank hypothesis to validated discovery.

---

## 2. Configuration (`config.yaml`)

The entire laboratory setup is defined in a single, version-controlled YAML file:

```yaml
scenario:
  domain: "gene_expression"      # Options: gene_expression | drug_target | synthetic_biology | etc.
  difficulty: "medium"           # Options: easy | medium | hard
  max_steps: 50                  # Protocol budget per episode
  num_episodes: 100              # Number of simulations to run

agent:
  type: "ppo"                    # random | greedy | ppo | dqn
  use_claude_oracle: true        # Enable AI literature insights (Requires HF_TOKEN)

constraints:
  noise_level: 2.0               # Signal-to-noise ratio control
  cost_tier: "mixed"             # Low (cheap/noisy) vs High (precise) fidelity
  prior_knowledge:
    seed_genes: ["TP53", "MYC"]  # Bias exploration towards known biology
```

---

## 3. Observation Space

The observation space is a Pydantic-typed `Observation` object with 15 fields, providing the agent with both raw signals and high-level context:

| Field | Type | Description |
|-------|------|-------------|
| `task_name` | `str` | Current research task identifier. |
| `domain` | `str` | Active biological domain. |
| `step` | `int` | Current protocol step within the budget. |
| `hypothesis_confidence` | `float` | Agent's internal belief score [0.0, 1.0]. |
| `experiments_done` | `int` | Total number of physical assays performed. |
| `numeric_signal` | `float` | Normalized signal from the last microarray/qPCR. |
| `kg_nodes` | `int` | Current size of the active Knowledge Graph. |
| `unknown_vars` | `int` | Number of targets still hidden in the matrix. |
| `budget_remaining` | `int` | Steps left before budget exhaustion. |
| `current_hypothesis` | `str` | Textual description of the current belief. |
| `last_gene_tested` | `str` | Name of the gene tested in the last step. |
| `top_candidate_genes` | `list[str]` | Current best-guess genes in the KG. |
| `literature_hint` | `str` | Last insight revealed by the literature oracle. |
| `signal_strength` | `float` | Scalar SNR for the last measurement. |

---

## 4. Action Space (6 Discrete Actions)

Agents select one research protocol action per step:

| Code | Action | Simulation Outcome |
|------|--------|---------------------|
| `0` | `Microarray Scan` | Cheap, broad-spectrum scan; noisy signal (Experiments A). |
| `1` | `qPCR Assay` | Expensive, high-SNR targeted measurement (Experiments B). |
| `2` | `Refine Hypothesis` | Statistical analysis of KG data; updates internal confidence. |
| `3` | `Literature Oracle` | Consults AI literature database; reveals hidden parameters. |
| `4` | `Data Synthesis` | Merges experiment signals into the Knowledge Graph nodes. |
| `5` | `Submit Discovery` | Ends episode and triggers the deterministic multi-objective grader. |

---

## 5. Research Domains

1.  **Genomics:** Master regulator and co-expression cluster discovery.
2.  **Disease Genomics:** Clinical panels (Cancer/Rare Disease) to find driver mutations.
3.  **Drug Target:** Compound screening for binding affinity and synergy.
4.  **Gene Regulatory Networks:** Mapping TF binding cascades and feedback loops.
5.  **Epigenomics:** DNA methylation and chromatin accessibility analysis.
6.  **Synthetic Biology:** Optimizing promoter strength and gene circuit modules.

---

## 6. Setup & Execution

### Prerequisites
- Python 3.11+
- `pip install -r requirements.txt`

### 1. Launch Inference Baseline
Ensure `HF_TOKEN` is set to enable the LLM Oracle logic:
```bash
export HF_TOKEN="your_token"
python3 inference.py
```

### 2. Launch Research Dashboard
The dashboard provides real-time guidance and 3D knowledge graph visualization:
```bash
python3 gradio_app.py
```

---

## 7. Baseline Performance (Greedy Agent)

| Domain | Task | Difficulty | Mean Score | Success Rate |
|--------|------|------------|------------|--------------|
| Genomics | Single Regulator | Easy | 0.922 | 88% |
| Genomics | Co-expression Cluster| Medium | 0.651 | 64% |
| Genomics | Interaction Effect | Hard | 0.443 | 41% |
| Disease | Cancer Panel | Easy | 0.895 | 92% |
| Drug | Screening | Medium | 0.582 | 55% |

---

## License
MIT

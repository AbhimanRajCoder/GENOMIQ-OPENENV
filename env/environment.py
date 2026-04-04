"""
GenomIQ — Scientific Discovery RL Environment.

Features:
  - Real gene expression matrices (genes × conditions) generated per episode.
  - Real gene symbols (TP53, BRCA1, MYC, etc.) for authentic flavor.
  - LLM-powered literature oracle for structured partial hints.
  - Domain-specific simulation engines.
  - Full per-step logging.
"""

import os
import numpy as np
import yaml
from pathlib import Path
from env.models import Action, Observation, StepResult
from env.tasks import TASKS, DIFFICULTY_MAP
from env.gene_names import get_gene_names
from env.logging_config import setup_logger
from env.datasets import load_preloaded, load_custom_csv
from env.real_datasets import generate_real_matrix, SIGNATURES

# ── Objective → hidden pattern mapping ────────────────────────────────────────

OBJECTIVE_MAP = {
    "Identify Key Regulator Genes":       {"hidden_pattern": "single",      "target_n": 1},
    "Detect Co-expression Clusters":      {"hidden_pattern": "cluster",     "target_n": 3},
    "Find Gene-Gene Interaction Effects": {"hidden_pattern": "interaction", "target_n": 2},
    "Predict Disease-Associated Genes":   {"hidden_pattern": "cluster",     "target_n": 3},
    "Identify Potential Drug Targets":    {"hidden_pattern": "single",      "target_n": 1},
}

logger = setup_logger("GenomIQEnv")

ACTION_NAMES = {
    0: "run_experiment_A (microarray scan)",
    1: "run_experiment_B (qPCR validation)",
    2: "refine_hypothesis",
    3: "read_literature (oracle)",
    4: "combine_results",
    5: "submit_discovery",
}


class GenomIQEnv:
    """Automated RL environment for scientific discovery across domains."""

    def __init__(self, config_path: str = "config.yaml", task_name: str = None) -> None:
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        domain = self.config["scenario"]["domain"]
        raw_difficulty = task_name or self.config["scenario"]["difficulty"]

        # Domain-aware task resolution (DIFFICULTY_MAP imported from tasks.py)
        if raw_difficulty in TASKS:
            self.task_name = raw_difficulty  # Direct task name given
        elif domain in DIFFICULTY_MAP and raw_difficulty in DIFFICULTY_MAP[domain]:
            self.task_name = DIFFICULTY_MAP[domain][raw_difficulty]
        else:
            self.task_name = "single_regulator"

        if self.task_name not in TASKS:
            self.task_name = "single_regulator"

        self.task = TASKS[self.task_name]
        self.domain = self.config["scenario"]["domain"]
        self.base_seed = self.config["scenario"]["seed"]
        self.rng = np.random.default_rng(seed=self.base_seed)
        self.episode_count = 0
        self.rew_cfg = self.config["rewards"]

        # Configurable experimental constraints
        constraints = self.config.get("constraints", {})
        self.noise_sigma = constraints.get("noise_level", 2.0)
        self.cost_tier = constraints.get("cost_tier", "mixed")

        # Prior knowledge injection
        prior = self.config.get("prior_knowledge", {})
        self.seed_genes = prior.get("seed_genes", [])
        self.known_associations = prior.get("associations", [])
        self.user_literature_hints = list(prior.get("literature_hints", []))

        # Research objective override
        self.objective = self.config["scenario"].get("objective", "")

        logger.info(f"ENV INIT | Domain={self.domain}, Task={self.task_name}, MaxSteps={self.config['scenario']['max_steps']}, Seed={self.base_seed}")
        self._reset_state()

    # ═══════════════════════════════════════════════════════════════════════════
    # STATE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def _reset_state(self) -> None:
        """Reset all internal state for a new episode."""
        self.rng = np.random.default_rng(seed=self.base_seed + self.episode_count)

        self.step_count = 0
        self.experiments_done = 0
        self.kg_nodes = 0
        self.hypothesis_confidence = 0.1
        self.last_result = 0.0
        self.numeric_signal = 0.0
        self.current_hypothesis = "No hypothesis formed yet."
        self.trajectory = []
        self.done = False

        # Gene-level tracking
        self.last_gene_tested = "—"
        self.top_candidates = []
        self.literature_hint = "No literature consulted yet."
        self.experiment_log = []  # stores (gene_name, signal, is_precise)
        self.hinted_genes = list(self.seed_genes)  # Pre-populate from prior knowledge

        # Hypothesis evolution history
        self.hypothesis_history = [{"step": 0, "confidence": 0.1, "hypothesis": "No hypothesis formed yet."}]

        # Ground truth
        self.true_pattern = None
        self.true_gene_names = []
        self.discovered_items = []

        # Stalling penalty tracking (Bug 3)
        self.last_useful_step = 0
        self.genes_tested_set = set()

        # Generate the expression matrix and hidden pattern
        self._build_expression_matrix()

        logger.info(f"ENV RESET | Episode #{self.episode_count}")
        logger.info(f"  Matrix shape: {self.expression_matrix.shape} (genes × conditions)")
        logger.info(f"  Gene count: {len(self.gene_names)}, True target: {self.true_gene_names}")

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPRESSION MATRIX GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_expression_matrix(self) -> None:
        """
        Generate or load a gene expression matrix.

        Supports three modes via config["dataset"]["source"]:
          - synthetic:  procedural log-normal matrix (default)
          - preloaded:  CSV from genomiq/datasets/
          - custom:     user-uploaded CSV

        Matrix: rows = genes, columns = conditions/samples.
        Hidden patterns are baked into the matrix as elevated signals.
        """
        source = self.config.get("dataset", {}).get("source", "synthetic")

        if source == "preloaded":
            name = self.config["dataset"].get("name", "cancer_gene_expression")
            try:
                self.expression_matrix, self.gene_names = load_preloaded(name)
                gc, nc = self.expression_matrix.shape
                self.unknown_vars = gc
                logger.info(f"  Loaded preloaded dataset: {name} ({gc} genes x {nc} conditions)")
            except FileNotFoundError:
                logger.warning(f"  Preloaded dataset '{name}' not found, falling back to synthetic")
                source = "synthetic"  # fallback

        elif source == "custom":
            path = self.config["dataset"].get("path", "")
            if path:
                try:
                    self.expression_matrix, self.gene_names = load_custom_csv(path)
                    gc, nc = self.expression_matrix.shape
                    self.unknown_vars = gc
                    logger.info(f"  Loaded custom dataset: {path} ({gc} genes x {nc} conditions)")
                except Exception as e:
                    logger.warning(f"  Custom dataset load failed ({e}), falling back to synthetic")
                    source = "synthetic"  # fallback
            else:
                logger.warning("  Custom dataset path empty, falling back to synthetic")
                source = "synthetic"  # fallback

        elif source in ("tcga", "geo"):
            sig_key = self.config.get("dataset", {}).get("name", "tcga_brca")
            if sig_key not in SIGNATURES:
                sig_key = "tcga_brca" if source == "tcga" else "geo_lung"
            try:
                nc = self.task.conditions if hasattr(self.task, 'conditions') else 6
                self.expression_matrix, self.gene_names = generate_real_matrix(sig_key, n_samples=nc, rng=self.rng)
                gc = len(self.gene_names)
                self.unknown_vars = gc
                logger.info(f"  Loaded real-world signature: {sig_key} ({gc} genes x {nc} conditions)")
            except Exception as e:
                logger.warning(f"  Real dataset load failed ({e}), falling back to synthetic")
                source = "synthetic"

        if source == "synthetic":
            gc = self.task.gene_count
            nc = self.task.conditions
            self.gene_names = get_gene_names(gc, self.rng)
            self.unknown_vars = gc
            # Base expression: log-normal distributed (realistic for RNA-seq data)
            self.expression_matrix = self.rng.lognormal(mean=3.0, sigma=1.0, size=(gc, nc))

        # Embed hidden pattern on top of the matrix (synthetic or real)
        gc, nc = self.expression_matrix.shape
        if self.domain in ("gene_expression", "disease_genomics"):
            self._embed_gene_expression_pattern(gc, nc)
        elif self.domain == "drug_target":
            self._embed_drug_target_pattern(gc, nc)
        elif self.domain == "gene_regulatory":
            self._embed_regulatory_pattern(gc, nc)
        elif self.domain == "epigenomics":
            self._embed_epigenomics_pattern(gc, nc)
        elif self.domain == "synthetic_biology":
            self._embed_synbio_pattern(gc, nc)
        elif self.domain == "protein_fold":
            self._embed_protein_fold_pattern(gc, nc)

    def _embed_gene_expression_pattern(self, gc: int, nc: int) -> None:
        """Embed hidden patterns into the expression matrix."""
        pattern = self.task.hidden_pattern

        if pattern == "single":
            # One master regulator has elevated expression across ALL conditions
            idx = int(self.rng.integers(0, gc))
            self.true_pattern = idx
            self.true_gene_names = [self.gene_names[idx]]
            # Inject strong upregulation signal
            self.expression_matrix[idx, :] += self.rng.normal(8.0, 0.5, nc)
            logger.info(f"  Hidden pattern: SINGLE regulator → {self.gene_names[idx]} (idx={idx})")

        elif pattern == "cluster":
            # 3 genes share a correlated co-expression signature
            indices = sorted(self.rng.choice(gc, size=3, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            # Shared latent signal — these genes rise and fall together
            shared_signal = self.rng.normal(6.0, 1.0, nc)
            for idx in indices:
                self.expression_matrix[idx, :] += shared_signal + self.rng.normal(0, 0.3, nc)
            logger.info(f"  Hidden pattern: CLUSTER → {self.true_gene_names} (indices={indices})")

        elif pattern == "interaction":
            # 2 genes whose PRODUCT correlates with a hidden phenotype
            indices = sorted(self.rng.choice(gc, size=2, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            # Each gene is moderately elevated, but their interaction is key
            for idx in indices:
                self.expression_matrix[idx, :] += self.rng.normal(4.0, 0.8, nc)
            logger.info(f"  Hidden pattern: INTERACTION pair → {self.true_gene_names} (indices={indices})")

    def _embed_drug_target_pattern(self, gc: int, nc: int) -> None:
        """Drug target: one compound has highest binding affinity."""
        idx = int(self.rng.integers(0, gc))
        self.true_pattern = idx
        self.true_gene_names = [self.gene_names[idx]]
        self.expression_matrix[idx, :] += self.rng.normal(10.0, 0.3, nc)
        logger.info(f"  Hidden target: {self.gene_names[idx]} (idx={idx})")

    def _embed_regulatory_pattern(self, gc: int, nc: int) -> None:
        """Gene Regulatory Networks: embed TF binding / cascade / feedback patterns."""
        pattern = self.task.hidden_pattern
        if pattern == "single":
            idx = int(self.rng.integers(0, gc))
            self.true_pattern = idx
            self.true_gene_names = [self.gene_names[idx]]
            # TF has strong, condition-specific activation
            self.expression_matrix[idx, :] += self.rng.normal(9.0, 0.4, nc)
            logger.info(f"  Hidden TF: {self.gene_names[idx]} (idx={idx})")
        elif pattern == "cluster":
            indices = sorted(self.rng.choice(gc, size=3, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            cascade_signal = self.rng.normal(7.0, 0.8, nc)
            for i, idx in enumerate(indices):
                # Decreasing signal along cascade (TF1 > TF2 > TF3)
                self.expression_matrix[idx, :] += cascade_signal * (1.0 - i * 0.15) + self.rng.normal(0, 0.2, nc)
            logger.info(f"  Hidden cascade: {self.true_gene_names} (indices={indices})")
        elif pattern == "interaction":
            indices = sorted(self.rng.choice(gc, size=2, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            for idx in indices:
                self.expression_matrix[idx, :] += self.rng.normal(5.0, 0.6, nc)
            logger.info(f"  Hidden feedback loop: {self.true_gene_names} (indices={indices})")

    def _embed_epigenomics_pattern(self, gc: int, nc: int) -> None:
        """Epigenomics: embed methylation / chromatin patterns."""
        pattern = self.task.hidden_pattern
        if pattern == "single":
            idx = int(self.rng.integers(0, gc))
            self.true_pattern = idx
            self.true_gene_names = [self.gene_names[idx]]
            # Hypermethylation = suppressed expression (inverted signal)
            self.expression_matrix[idx, :] = self.rng.normal(0.8, 0.2, nc)
            logger.info(f"  Hidden methylation marker: {self.gene_names[idx]} (idx={idx})")
        elif pattern == "cluster":
            indices = sorted(self.rng.choice(gc, size=3, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            # Co-accessible chromatin regions share a signal
            shared = self.rng.normal(6.5, 0.9, nc)
            for idx in indices:
                self.expression_matrix[idx, :] += shared + self.rng.normal(0, 0.4, nc)
            logger.info(f"  Hidden chromatin cluster: {self.true_gene_names} (indices={indices})")
        elif pattern == "interaction":
            indices = sorted(self.rng.choice(gc, size=2, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            for idx in indices:
                self.expression_matrix[idx, :] += self.rng.normal(4.5, 0.7, nc)
            logger.info(f"  Hidden epigenetic interaction: {self.true_gene_names} (indices={indices})")

    def _embed_synbio_pattern(self, gc: int, nc: int) -> None:
        """Synthetic Biology: embed circuit / pathway patterns."""
        pattern = self.task.hidden_pattern
        if pattern == "single":
            idx = int(self.rng.integers(0, gc))
            self.true_pattern = idx
            self.true_gene_names = [self.gene_names[idx]]
            # Strongest promoter has highest expression
            self.expression_matrix[idx, :] += self.rng.normal(12.0, 0.3, nc)
            logger.info(f"  Hidden promoter: {self.gene_names[idx]} (idx={idx})")
        elif pattern == "cluster":
            indices = sorted(self.rng.choice(gc, size=3, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            shared = self.rng.normal(7.0, 1.2, nc)
            for idx in indices:
                self.expression_matrix[idx, :] += shared + self.rng.normal(0, 0.5, nc)
            logger.info(f"  Hidden circuit module: {self.true_gene_names} (indices={indices})")
        elif pattern == "interaction":
            indices = sorted(self.rng.choice(gc, size=2, replace=False).tolist())
            self.true_pattern = indices
            self.true_gene_names = [self.gene_names[i] for i in indices]
            for idx in indices:
                self.expression_matrix[idx, :] += self.rng.normal(5.0, 1.0, nc)
            logger.info(f"  Hidden pathway crosstalk: {self.true_gene_names} (indices={indices})")

    def _embed_protein_fold_pattern(self, gc: int, nc: int) -> None:
        """Protein fold: one configuration has lowest energy."""
        idx = int(self.rng.integers(0, gc))
        self.true_pattern = idx
        self.true_gene_names = [self.gene_names[idx]]
        # Invert: the target has LOWEST expression (energy minimum)
        self.expression_matrix[idx, :] = self.rng.normal(0.5, 0.1, nc)
        logger.info(f"  Hidden native state: {self.gene_names[idx]} (idx={idx})")

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP LOGIC — ACTIONS OPERATE ON THE REAL MATRIX
    # ═══════════════════════════════════════════════════════════════════════════

    async def step(self, action: Action) -> dict:
        if self.done:
            return StepResult(observation=self._get_observation(), reward=0.0, done=True, info={}).model_dump()

        self.step_count += 1
        action_type = action.action_type
        # Cost tier reward shaping (Phase 4)
        cost_tier = self.config.get("constraints", {}).get("cost_tier", "mixed")
        if cost_tier == "low_fidelity":
            scan_cost_adj = 0.05   # cheaper scans
            qpcr_cost_adj = 0.3
        elif cost_tier == "high_fidelity":
            scan_cost_adj = -0.2   # more expensive
            qpcr_cost_adj = -0.5
        else:  # mixed
            scan_cost_adj = 0.0
            qpcr_cost_adj = 0.0

        reward = self.rew_cfg["step_penalty"]
        info = {}
        action_name = ACTION_NAMES.get(action_type, f"unknown({action_type})")

        # ── Action 0: Microarray scan (cheap, noisy, random gene) ──────────
        if action_type == 0:
            self.experiments_done += 1
            # Oracle feedback: if we have hinted genes, 70% chance to test one
            if self.hinted_genes and self.rng.random() < 0.7:
                gene_name = self.hinted_genes[int(self.rng.integers(0, len(self.hinted_genes)))]
                gene_idx = self.gene_names.index(gene_name) if gene_name in self.gene_names else int(self.rng.integers(0, len(self.gene_names)))
                if gene_name not in self.gene_names:
                    gene_name = self.gene_names[gene_idx]
            else:
                gene_idx = int(self.rng.integers(0, len(self.gene_names)))
                gene_name = self.gene_names[gene_idx]
            # Read expression value + noise
            raw_signal = float(np.mean(self.expression_matrix[gene_idx, :]))
            noise = self.rng.normal(0, self.noise_sigma)
            measured = raw_signal + noise
            self.last_result = round(measured, 3)
            self.last_gene_tested = gene_name
            self.numeric_signal = round(raw_signal, 3)
            self.experiment_log.append((gene_name, measured, False))

            # Is this gene part of the answer?
            is_hit = gene_idx in (self.true_pattern if isinstance(self.true_pattern, list) else [self.true_pattern])
            reward += (1.5 + scan_cost_adj) if is_hit else (self.rew_cfg["useless_experiment_penalty"] + scan_cost_adj)

            if self.unknown_vars > 0:
                self.unknown_vars -= 1

            # Stalling tracker: new unique gene tested
            if gene_name not in self.genes_tested_set:
                self.genes_tested_set.add(gene_name)
                self.last_useful_step = self.step_count

            logger.info(f"  STEP {self.step_count} | {action_name} → gene={gene_name}, measured={measured:.2f} (true={raw_signal:.2f}), hit={is_hit}")

        # ── Action 1: qPCR validation (expensive, precise, top candidate) ──
        elif action_type == 1:
            self.experiments_done += 1
            # Target the most suspicious gene: top_candidates > hinted_genes > random
            if self.top_candidates:
                gene_name = self.top_candidates[0]
                gene_idx = self.gene_names.index(gene_name) if gene_name in self.gene_names else int(self.rng.integers(0, len(self.gene_names)))
            elif self.hinted_genes:
                gene_name = self.hinted_genes[0]
                gene_idx = self.gene_names.index(gene_name) if gene_name in self.gene_names else int(self.rng.integers(0, len(self.gene_names)))
                if gene_name not in self.gene_names:
                    gene_name = self.gene_names[gene_idx]
            else:
                gene_idx = int(self.rng.integers(0, len(self.gene_names)))
                gene_name = self.gene_names[gene_idx]

            raw_signal = float(np.mean(self.expression_matrix[gene_idx, :]))
            noise = self.rng.normal(0, self.noise_sigma * 0.15)  # qPCR precision scales with noise config
            measured = raw_signal + noise
            self.last_result = round(measured, 3)
            self.last_gene_tested = gene_name
            self.numeric_signal = round(raw_signal, 3)
            self.experiment_log.append((gene_name, measured, True))

            is_hit = gene_idx in (self.true_pattern if isinstance(self.true_pattern, list) else [self.true_pattern])
            old_conf = self.hypothesis_confidence
            self.hypothesis_confidence = min(1.0, self.hypothesis_confidence + (0.15 if is_hit else 0.05))
            reward += (3.0 + qpcr_cost_adj) if is_hit else (1.0 + qpcr_cost_adj)

            # Track hypothesis evolution on qPCR confidence changes
            if self.hypothesis_confidence != old_conf:
                self.hypothesis_history.append({
                    "step": self.step_count,
                    "confidence": round(self.hypothesis_confidence, 3),
                    "hypothesis": f"qPCR validated {gene_name} (conf={self.hypothesis_confidence:.0%})",
                })

            if self.unknown_vars > 0:
                self.unknown_vars -= 1

            # Stalling tracker: new gene or confidence increase
            if gene_name not in self.genes_tested_set:
                self.genes_tested_set.add(gene_name)
                self.last_useful_step = self.step_count
            if self.hypothesis_confidence > old_conf:
                self.last_useful_step = self.step_count

            logger.info(f"  STEP {self.step_count} | {action_name} → gene={gene_name}, measured={measured:.2f}, hit={is_hit}, conf {old_conf:.2f}→{self.hypothesis_confidence:.2f}")

        # ── Action 2: Refine hypothesis (analyze accumulated data) ──────────
        elif action_type == 2:
            old_conf = self.hypothesis_confidence
            if len(self.experiment_log) >= 2:
                # Statistical analysis: rank genes by measured expression
                gene_scores = {}
                for gname, signal, precise in self.experiment_log:
                    weight = 2.0 if precise else 1.0
                    gene_scores[gname] = gene_scores.get(gname, 0) + signal * weight

                # Boost hinted genes in ranking (oracle feedback integration)
                for hg in self.hinted_genes:
                    if hg in gene_scores:
                        gene_scores[hg] *= 1.5  # 50% score boost for oracle-hinted genes

                # Top candidates = highest scoring genes
                sorted_genes = sorted(gene_scores.items(), key=lambda x: -x[1])
                self.top_candidates = [g for g, _ in sorted_genes[:5]]

                # Confidence boost based on data quality
                improvement = float(self.rng.uniform(0.08, 0.18))
                self.hypothesis_confidence = min(1.0, self.hypothesis_confidence + improvement)
                self.current_hypothesis = f"Top candidates: {', '.join(self.top_candidates[:3])} (conf={self.hypothesis_confidence:.0%})"
                reward += self.rew_cfg["hypothesis_improvement_bonus"]

                # Track hypothesis evolution
                self.hypothesis_history.append({
                    "step": self.step_count,
                    "confidence": round(self.hypothesis_confidence, 3),
                    "hypothesis": self.current_hypothesis,
                })

                # Stalling tracker: confidence increased
                if self.hypothesis_confidence > old_conf:
                    self.last_useful_step = self.step_count

                logger.info(f"  STEP {self.step_count} | {action_name} → refined from {len(self.experiment_log)} experiments. Top: {self.top_candidates[:3]}, conf {old_conf:.2f}→{self.hypothesis_confidence:.2f}")
            else:
                improvement = float(self.rng.uniform(0.02, 0.06))
                self.hypothesis_confidence = min(1.0, self.hypothesis_confidence + improvement)
                reward += 0.5
                if self.hypothesis_confidence > old_conf:
                    self.last_useful_step = self.step_count
                logger.info(f"  STEP {self.step_count} | {action_name} → insufficient data for deep analysis. conf {old_conf:.2f}→{self.hypothesis_confidence:.2f}")

        # ── Action 3: Read literature (LLM oracle or deterministic hint) ────
        elif action_type == 3:
            hint = self._generate_literature_hint()
            self.literature_hint = hint
            old_kg = self.kg_nodes
            self.kg_nodes += 1
            if self.unknown_vars > 0:
                self.unknown_vars -= 1
            reward += 1.5

            # Parse gene name from hint and add to hinted_genes pool
            hinted_gene = self._extract_gene_from_hint(hint)
            if hinted_gene and hinted_gene not in self.hinted_genes:
                self.hinted_genes.append(hinted_gene)
                logger.info(f"  STEP {self.step_count} | ORACLE HINT parsed → gene={hinted_gene} added to hint pool ({len(self.hinted_genes)} total)")

            # Stalling tracker: kg_nodes increased
            if self.kg_nodes > old_kg:
                self.last_useful_step = self.step_count
            logger.info(f"  STEP {self.step_count} | {action_name} → \"{hint}\"")

        # ── Action 4: Combine results (build knowledge graph) ──────────────
        elif action_type == 4:
            if self.experiments_done >= 2:
                old_kg = self.kg_nodes
                self.kg_nodes += 2
                reward += 2.0
                # Stalling tracker: kg_nodes increased
                if self.kg_nodes > old_kg:
                    self.last_useful_step = self.step_count
                logger.info(f"  STEP {self.step_count} | {action_name} → combined data, kg_nodes {old_kg}→{self.kg_nodes}")
            else:
                reward -= 0.5
                logger.info(f"  STEP {self.step_count} | {action_name} → not enough experiments to combine (have {self.experiments_done}, need ≥2)")

        # ── Action 5: Submit discovery ─────────────────────────────────────
        elif action_type == 5:
            self.done = True
            # Build submitted_candidates from experiment_log frequency
            submitted_candidates = self._build_submitted_candidates()
            final_state = self._build_grader_state(submitted_candidates=submitted_candidates, submitted=True)
            from env.graders import grade
            score = grade(self.trajectory, final_state, self.task_name)
            if score >= self.task.target_score:
                reward += self.rew_cfg["discovery_bonus"]
                info["success"] = True
                logger.info(f"  STEP {self.step_count} | {action_name} → ✅ SUCCESS! Score={score:.3f} (target={self.task.target_score})")
                logger.info(f"    Submitted: {submitted_candidates}")
                logger.info(f"    Truth:     {self.true_gene_names}")
            else:
                reward -= 10.0
                info["success"] = False
                logger.warning(f"  STEP {self.step_count} | {action_name} → ❌ FAILED. Score={score:.3f} (target={self.task.target_score})")
                logger.warning(f"    Submitted: {submitted_candidates}")
                logger.warning(f"    Truth:     {self.true_gene_names}")
            info["final_score"] = score
            info["submitted_candidates"] = submitted_candidates

        # ── Stalling penalty (Bug 3) ───────────────────────────────────────
        if action_type != 5:
            consecutive_no_progress = self.step_count - self.last_useful_step
            if consecutive_no_progress >= 10 and self.hypothesis_confidence >= 0.8:
                reward -= 3.0
                info["stalling_critical"] = True
                logger.warning(f"  STEP {self.step_count} | CRITICAL STALL — {consecutive_no_progress} steps without progress, conf={self.hypothesis_confidence:.2f}. Penalty -3.0")
            elif consecutive_no_progress >= 5 and self.hypothesis_confidence >= 0.8:
                reward -= 1.0
                info["stalling"] = True
                logger.warning(f"  STEP {self.step_count} | STALLING — {consecutive_no_progress} steps without progress, conf={self.hypothesis_confidence:.2f}. Penalty -1.0")

        # ── Termination check ──────────────────────────────────────────────
        max_steps = self.config["scenario"]["max_steps"]
        if self.step_count >= max_steps and not self.done:
            self.done = True
            # Budget exhausted — still grade for partial credit
            submitted_candidates = self._build_submitted_candidates()
            final_state = self._build_grader_state(submitted_candidates=submitted_candidates, submitted=False)
            from env.graders import grade
            score = grade(self.trajectory, final_state, self.task_name)
            info["final_score"] = score
            info["success"] = False
            info["submission"] = "budget_exhausted_no_submit"
            info["submitted_candidates"] = submitted_candidates
            logger.warning(f"  STEP {self.step_count} | Budget exhausted (max={max_steps}). Score={score:.3f}")
            logger.warning(f"    Candidates at end: {submitted_candidates}")
            logger.warning(f"    Truth:             {self.true_gene_names}")

        obs = self._get_observation()
        self.trajectory.append({"step": self.step_count, "action": action_type, "reward": reward, "gene_tested": self.last_gene_tested})

        return StepResult(observation=obs, reward=reward, done=self.done, info=info).model_dump()

    # ═══════════════════════════════════════════════════════════════════════════
    # LITERATURE ORACLE
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_literature_hint(self) -> str:
        """
        Generate a partial hint about the hidden pattern.
        Priority: user-provided hints → LLM oracle → deterministic.
        """
        # Priority 1: user-provided literature hints
        if self.user_literature_hints:
            return self.user_literature_hints.pop(0)

        use_oracle = self.config["agent"].get("use_claude_oracle", False)
        hf_token = os.getenv("HF_TOKEN", "")

        if use_oracle and hf_token:
            return self._llm_literature_hint()
        else:
            return self._deterministic_literature_hint()

    def _deterministic_literature_hint(self) -> str:
        """Generate a structured partial hint without LLM."""
        hints_pool = []
        true_indices = self.true_pattern if isinstance(self.true_pattern, list) else [self.true_pattern]

        # Reveal a true gene with some misdirection
        if self.rng.random() < 0.75:
            # Genuine hint about a true target
            idx = self.rng.choice(true_indices)
            gene = self.gene_names[idx]
            mean_expr = float(np.mean(self.expression_matrix[idx, :]))
            hints_pool = [
                f"Literature suggests {gene} shows elevated expression (mean={mean_expr:.1f}) in this pathway.",
                f"Recent study: {gene} may be a key regulator in the observed phenotype.",
                f"Published data indicates correlation between {gene} and the target condition.",
                f"Review article highlights {gene} as a candidate in similar expression profiles.",
            ]
        else:
            # Partial/noisy hint — mentions a non-target gene
            decoy_idx = int(self.rng.integers(0, len(self.gene_names)))
            while decoy_idx in true_indices:
                decoy_idx = int(self.rng.integers(0, len(self.gene_names)))
            gene = self.gene_names[decoy_idx]
            hints_pool = [
                f"Preliminary evidence links {gene} to the pathway, but results are inconclusive.",
                f"Conference abstract mentions {gene}, though replication studies are needed.",
                f"{gene} was identified in a low-powered screen — treat with caution.",
            ]

        return str(self.rng.choice(hints_pool))

    def _llm_literature_hint(self) -> str:
        """Use LLM to generate a structured partial hint. Never reveals the full answer."""
        try:
            from openai import OpenAI
            api_base = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
            model = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
            hf_token = os.getenv("HF_TOKEN", "")

            client = OpenAI(base_url=api_base, api_key=hf_token)

            true_gene = self.rng.choice(self.true_gene_names)
            # Include some decoy genes for misdirection
            decoys = [self.gene_names[int(self.rng.integers(0, len(self.gene_names)))] for _ in range(3)]
            gene_list = [true_gene] + decoys
            self.rng.shuffle(gene_list)

            prompt = (
                f"You are a genomics research assistant. A scientist is studying gene expression patterns.\n"
                f"They are investigating these genes: {', '.join(gene_list)}.\n"
                f"Provide ONE short hint (1-2 sentences) about which gene might be important in this context.\n"
                f"Do NOT reveal the definitive answer. Be suggestive, not conclusive.\n"
                f"Example: 'Gene X shows elevated correlation in condition 3, suggesting regulatory activity.'\n"
                f"Respond with the hint only, no prefixes."
            )

            response = client.chat.completions.create(
                model=model,
                max_tokens=80,
                messages=[{"role": "user", "content": prompt}],
            )
            hint = response.choices[0].message.content.strip()
            return hint[:200]  # Cap length

        except Exception as e:
            logger.warning(f"  LLM oracle failed ({e}), falling back to deterministic hint")
            return self._deterministic_literature_hint()

    def _extract_gene_from_hint(self, hint: str) -> str | None:
        """Extract a gene name from a literature hint string.

        Scans the hint text for any gene name from the current matrix's
        gene list. Returns the first match, or None if no gene found.
        """
        for gene in self.gene_names:
            if gene in hint:
                return gene
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # OBSERVATION & STATE
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_observation(self) -> Observation:
        return Observation(
            task_name=self.task_name,
            domain=self.domain,
            step=self.step_count,
            hypothesis_confidence=round(self.hypothesis_confidence, 3),
            experiments_done=self.experiments_done,
            last_result=self.last_result,
            numeric_signal=self.numeric_signal,
            kg_nodes=self.kg_nodes,
            unknown_vars=self.unknown_vars,
            budget_remaining=self.config["scenario"]["max_steps"] - self.step_count,
            current_hypothesis=self.current_hypothesis,
            last_gene_tested=self.last_gene_tested,
            top_candidate_genes=self.top_candidates[:5],
            literature_hint=self.literature_hint,
            signal_strength=self.numeric_signal,
        )

    def _build_submitted_candidates(self) -> list[str]:
        """Build the list of gene names the agent implicitly submits.

        Priority: hinted genes that were experimentally validated > frequency-ranked.
        N depends on task type: 1 for single, 3 for cluster, 2 for interaction.
        """
        pattern = self.task.hidden_pattern
        if pattern == "single":
            n = 1
        elif pattern == "cluster":
            n = 3
        elif pattern == "interaction":
            n = 2
        else:
            n = 1

        # Count gene test frequency from experiment_log
        freq: dict[str, int] = {}
        for gene_name, _signal, _precise in self.experiment_log:
            freq[gene_name] = freq.get(gene_name, 0) + 1

        if not freq:
            return self.top_candidates[:n]

        # Priority 1: hinted genes that were also tested (experimentally validated hints)
        validated_hints = [g for g in self.hinted_genes if g in freq]
        # Priority 2: remaining slots filled by frequency rank (excluding already-picked)
        used = set(validated_hints)
        freq_ranked = [g for g, _ in sorted(freq.items(), key=lambda x: -x[1]) if g not in used]

        result = validated_hints[:n]
        remaining = n - len(result)
        if remaining > 0:
            result.extend(freq_ranked[:remaining])

        return result[:n]

    def _build_grader_state(self, submitted_candidates: list[str], submitted: bool) -> dict:
        """Build the final_state dict that the grader expects."""
        return {
            "submitted_candidates": submitted_candidates,
            "true_targets": list(self.true_gene_names),
            "hypothesis_confidence": self.hypothesis_confidence,
            "max_steps": self.config["scenario"]["max_steps"],
            "submitted": submitted,
            "steps_used": self.step_count,
            "task_name": self.task.name,
            "expression_matrix_shape": list(self.expression_matrix.shape),
        }

    def _get_final_state(self) -> dict:
        """Full internal state for the /state API endpoint."""
        candidates = self._build_submitted_candidates()
        state = self._get_observation().model_dump()
        state.update({
            "true_targets": list(self.true_gene_names),
            "submitted_candidates": candidates,
            "max_steps": self.config["scenario"]["max_steps"],
            "expression_matrix_shape": list(self.expression_matrix.shape),
            "hypothesis_history": self.hypothesis_history,
            "knowledge_graph": self._build_knowledge_graph_data(),
        })
        return state

    def _build_knowledge_graph_data(self) -> dict:
        """Build serializable knowledge graph from experiment log."""
        nodes = set()
        edges = []
        prev_gene = None
        edge_counts: dict[tuple[str, str], int] = {}

        for gene_name, _signal, _precise in self.experiment_log:
            nodes.add(gene_name)
            if prev_gene and prev_gene != gene_name:
                edge_key = tuple(sorted([prev_gene, gene_name]))
                edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1
            prev_gene = gene_name

        for (g1, g2), weight in edge_counts.items():
            edges.append({"source": g1, "target": g2, "weight": weight})

        return {"nodes": list(nodes), "edges": edges}

    async def reset(self) -> dict:
        self.episode_count += 1
        self._reset_state()
        return self._get_observation().model_dump()

    async def state(self) -> dict:
        return self._get_final_state()

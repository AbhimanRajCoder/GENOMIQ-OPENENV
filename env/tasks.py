"""
GenomIQ — Task definitions.

Defines progressively harder discovery tasks across 6 research domains:
  - gene_expression   (Genomics)
  - disease_genomics  (Cancer / Rare Diseases)
  - drug_target       (Drug Target Discovery)
  - gene_regulatory   (Gene Regulatory Networks)
  - epigenomics       (Epigenomics)
  - synthetic_biology (Synthetic Biology)
"""

from dataclasses import dataclass


@dataclass
class Task:
    """A single GenomIQ task specification."""

    name: str
    description: str
    difficulty: str  # "easy" | "medium" | "hard"
    max_steps: int
    gene_count: int
    conditions: int
    domain: str
    hidden_pattern: str  # "single" | "cluster" | "interaction"
    target_score: float


# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 1: Gene Expression (Genomics)
# ══════════════════════════════════════════════════════════════════════════════

GE_EASY = Task(
    name="single_regulator",
    description="Find 1 master gene controlling expression in a 20-gene matrix.",
    difficulty="easy",
    max_steps=30,
    gene_count=20,
    conditions=1,
    domain="gene_expression",
    hidden_pattern="single",
    target_score=0.80,
)

GE_MEDIUM = Task(
    name="coexpression_cluster",
    description="Identify 3 co-regulated genes across a 50-gene, 3-condition dataset.",
    difficulty="medium",
    max_steps=50,
    gene_count=50,
    conditions=3,
    domain="gene_expression",
    hidden_pattern="cluster",
    target_score=0.65,
)

GE_HARD = Task(
    name="interaction_effect",
    description="Discover a gene pair whose combined activity drives a hidden phenotype.",
    difficulty="hard",
    max_steps=80,
    gene_count=100,
    conditions=5,
    domain="gene_expression",
    hidden_pattern="interaction",
    target_score=0.50,
)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 2: Disease Genomics (Cancer / Rare Diseases)
# ══════════════════════════════════════════════════════════════════════════════

DG_EASY = Task(
    name="cancer_gene_panel",
    description="Identify 1 driver mutation from a 30-gene cancer panel.",
    difficulty="easy",
    max_steps=30,
    gene_count=30,
    conditions=2,
    domain="disease_genomics",
    hidden_pattern="single",
    target_score=0.75,
)

DG_MEDIUM = Task(
    name="rare_disease_cluster",
    description="Find 3 co-dysregulated genes in a rare disease expression profile.",
    difficulty="medium",
    max_steps=50,
    gene_count=60,
    conditions=4,
    domain="disease_genomics",
    hidden_pattern="cluster",
    target_score=0.60,
)

DG_HARD = Task(
    name="polygenic_interaction",
    description="Discover a multi-gene interaction driving a complex disease phenotype.",
    difficulty="hard",
    max_steps=80,
    gene_count=120,
    conditions=6,
    domain="disease_genomics",
    hidden_pattern="interaction",
    target_score=0.45,
)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 3: Drug Target Discovery
# ══════════════════════════════════════════════════════════════════════════════

DT_EASY = Task(
    name="drug_affinity",
    description="Identify the high-affinity binding molecule in a compound library.",
    difficulty="easy",
    max_steps=40,
    gene_count=40,
    conditions=1,
    domain="drug_target",
    hidden_pattern="single",
    target_score=0.70,
)

DT_MEDIUM = Task(
    name="multi_target_screen",
    description="Find 3 candidate drug targets from a 80-compound screen.",
    difficulty="medium",
    max_steps=60,
    gene_count=80,
    conditions=3,
    domain="drug_target",
    hidden_pattern="cluster",
    target_score=0.60,
)

DT_HARD = Task(
    name="synergy_detection",
    description="Discover a synergistic drug pair with combined therapeutic effect.",
    difficulty="hard",
    max_steps=80,
    gene_count=100,
    conditions=4,
    domain="drug_target",
    hidden_pattern="interaction",
    target_score=0.50,
)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 4: Gene Regulatory Networks
# ══════════════════════════════════════════════════════════════════════════════

GR_EASY = Task(
    name="single_tf_binding",
    description="Identify 1 transcription factor regulating a target gene set.",
    difficulty="easy",
    max_steps=30,
    gene_count=25,
    conditions=2,
    domain="gene_regulatory",
    hidden_pattern="single",
    target_score=0.80,
)

GR_MEDIUM = Task(
    name="regulatory_cascade",
    description="Map a 3-gene regulatory cascade from expression data.",
    difficulty="medium",
    max_steps=50,
    gene_count=50,
    conditions=3,
    domain="gene_regulatory",
    hidden_pattern="cluster",
    target_score=0.65,
)

GR_HARD = Task(
    name="feedback_loop",
    description="Discover a feedback loop interaction between 2 regulatory genes.",
    difficulty="hard",
    max_steps=80,
    gene_count=100,
    conditions=5,
    domain="gene_regulatory",
    hidden_pattern="interaction",
    target_score=0.50,
)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 5: Epigenomics
# ══════════════════════════════════════════════════════════════════════════════

EP_EASY = Task(
    name="methylation_marker",
    description="Find 1 differentially methylated gene from a CpG panel.",
    difficulty="easy",
    max_steps=30,
    gene_count=20,
    conditions=2,
    domain="epigenomics",
    hidden_pattern="single",
    target_score=0.80,
)

EP_MEDIUM = Task(
    name="chromatin_cluster",
    description="Identify 3 genes with correlated chromatin accessibility changes.",
    difficulty="medium",
    max_steps=50,
    gene_count=50,
    conditions=3,
    domain="epigenomics",
    hidden_pattern="cluster",
    target_score=0.65,
)

EP_HARD = Task(
    name="epigenetic_interaction",
    description="Discover a gene pair with synergistic epigenetic modification effects.",
    difficulty="hard",
    max_steps=80,
    gene_count=100,
    conditions=5,
    domain="epigenomics",
    hidden_pattern="interaction",
    target_score=0.50,
)

# ══════════════════════════════════════════════════════════════════════════════
# DOMAIN 6: Synthetic Biology
# ══════════════════════════════════════════════════════════════════════════════

SB_EASY = Task(
    name="promoter_strength",
    description="Identify the strongest promoter in a synthetic gene circuit.",
    difficulty="easy",
    max_steps=30,
    gene_count=20,
    conditions=1,
    domain="synthetic_biology",
    hidden_pattern="single",
    target_score=0.80,
)

SB_MEDIUM = Task(
    name="circuit_module",
    description="Find 3 interacting components in a synthetic gene circuit.",
    difficulty="medium",
    max_steps=50,
    gene_count=40,
    conditions=3,
    domain="synthetic_biology",
    hidden_pattern="cluster",
    target_score=0.65,
)

SB_HARD = Task(
    name="pathway_crosstalk",
    description="Discover cross-talk interactions between 2 synthetic pathways.",
    difficulty="hard",
    max_steps=80,
    gene_count=80,
    conditions=5,
    domain="synthetic_biology",
    hidden_pattern="interaction",
    target_score=0.50,
)


# ── Lookup dictionary ─────────────────────────────────────────────────────────

TASKS: dict[str, Task] = {
    # Gene Expression
    "single_regulator": GE_EASY,
    "coexpression_cluster": GE_MEDIUM,
    "interaction_effect": GE_HARD,
    # Disease Genomics
    "cancer_gene_panel": DG_EASY,
    "rare_disease_cluster": DG_MEDIUM,
    "polygenic_interaction": DG_HARD,
    # Drug Target
    "drug_affinity": DT_EASY,
    "multi_target_screen": DT_MEDIUM,
    "synergy_detection": DT_HARD,
    # Gene Regulatory
    "single_tf_binding": GR_EASY,
    "regulatory_cascade": GR_MEDIUM,
    "feedback_loop": GR_HARD,
    # Epigenomics
    "methylation_marker": EP_EASY,
    "chromatin_cluster": EP_MEDIUM,
    "epigenetic_interaction": EP_HARD,
    # Synthetic Biology
    "promoter_strength": SB_EASY,
    "circuit_module": SB_MEDIUM,
    "pathway_crosstalk": SB_HARD,
}


# ── Domain → Difficulty → Task mapping ────────────────────────────────────────

DIFFICULTY_MAP: dict[str, dict[str, str]] = {
    "gene_expression":   {"easy": "single_regulator",   "medium": "coexpression_cluster", "hard": "interaction_effect"},
    "disease_genomics":  {"easy": "cancer_gene_panel",  "medium": "rare_disease_cluster", "hard": "polygenic_interaction"},
    "drug_target":       {"easy": "drug_affinity",      "medium": "multi_target_screen",  "hard": "synergy_detection"},
    "gene_regulatory":   {"easy": "single_tf_binding",  "medium": "regulatory_cascade",   "hard": "feedback_loop"},
    "epigenomics":       {"easy": "methylation_marker", "medium": "chromatin_cluster",     "hard": "epigenetic_interaction"},
    "synthetic_biology": {"easy": "promoter_strength",  "medium": "circuit_module",        "hard": "pathway_crosstalk"},
}

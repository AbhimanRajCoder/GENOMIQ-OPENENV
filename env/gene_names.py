"""
GenomIQ — Curated gene symbol bank for authentic simulation flavor.

200 real human gene symbols from well-known pathways:
  - Oncogenes & tumor suppressors
  - Signal transduction
  - Transcription factors
  - Metabolic enzymes
  - Epigenetic regulators
  - Immune signaling
"""

GENE_SYMBOLS = [
    # ── Oncogenes & tumor suppressors ──
    "TP53", "BRCA1", "BRCA2", "EGFR", "MYC", "KRAS", "BRAF", "PIK3CA",
    "PTEN", "RB1", "APC", "VHL", "NF1", "NF2", "WT1", "CDH1", "SMAD4",
    "CDKN2A", "MLH1", "MSH2", "ATM", "CHEK2", "PALB2", "RAD51", "FANCL",

    # ── Signal transduction ──
    "MAPK1", "MAPK3", "AKT1", "AKT2", "MTOR", "JAK1", "JAK2", "STAT3",
    "SRC", "ABL1", "RAF1", "MEK1", "ERK2", "RHOA", "RAC1", "CDC42",
    "NOTCH1", "NOTCH2", "WNT1", "WNT3A", "FZD1", "DVL1", "GSK3B", "CTNNB1",
    "SHH", "SMO", "PTCH1", "GLI1", "GLI2", "TGFB1", "SMAD2", "SMAD3",

    # ── Transcription factors ──
    "JUN", "FOS", "ETS1", "ETS2", "MYB", "SOX2", "SOX9", "NANOG",
    "OCT4", "KLF4", "GATA1", "GATA3", "RUNX1", "RUNX2", "PAX6", "IRF1",
    "NFE2L2", "HIF1A", "ARNT", "SP1", "CREB1", "ELK1", "FOXO1", "FOXO3",
    "TCF7", "LEF1", "TWIST1", "SNAI1", "ZEB1", "ZEB2", "EZH2", "BMI1",

    # ── Cell cycle & apoptosis ──
    "CDK1", "CDK2", "CDK4", "CDK6", "CCND1", "CCNE1", "CCNB1", "CDC25A",
    "BCL2", "BAX", "BAK1", "BID", "CASP3", "CASP8", "CASP9", "XIAP",
    "BIRC5", "MDM2", "MDM4", "GADD45A", "P21", "P27", "PCNA", "MCM2",

    # ── DNA repair ──
    "BRIP1", "RAD50", "MRE11", "NBN", "XPC", "XPA", "ERCC1", "XRCC1",
    "PARP1", "MGMT", "MUTYH", "POLE", "POLD1", "LIG1", "FEN1", "UNG",

    # ── Epigenetic regulators ──
    "DNMT1", "DNMT3A", "DNMT3B", "TET1", "TET2", "IDH1", "IDH2", "KDM1A",
    "HDAC1", "HDAC2", "HAT1", "KAT5", "SIRT1", "SIRT2", "BRD4", "DOT1L",

    # ── Metabolic enzymes ──
    "HK2", "PKM", "LDHA", "PDK1", "GLUT1", "FASN", "ACLY", "ACC1",
    "CPT1A", "HMGCR", "GLS", "ASNS", "SLC7A11", "GPX4", "NQO1", "G6PD",

    # ── Immune signaling ──
    "CD274", "PDCD1", "CTLA4", "LAG3", "TIM3", "TIGIT", "CD28", "CD80",
    "CD86", "ICOS", "OX40", "CD40", "TNF", "IFNG", "IL2", "IL6",
    "IL10", "IL12A", "IL17A", "CSF2", "CCL2", "CXCL8", "CXCR4", "CCR7",

    # ── Cytoskeletal / structural ──
    "ACTB", "TUBB", "VIMENTIN", "KRT18", "CDH2", "ITGB1", "MMP2", "MMP9",
    "TIMP1", "FN1", "COL1A1", "LAMA5", "PLAU", "SERPINE1", "VEGFA", "FGF2",

    # ── Housekeeping & controls ──
    "GAPDH", "ACTB", "HPRT1", "B2M", "RPLP0", "UBC", "YWHAZ", "SDHA",
]

# Deduplicate while preserving order
_seen = set()
GENE_SYMBOLS_UNIQUE = []
for g in GENE_SYMBOLS:
    if g not in _seen:
        _seen.add(g)
        GENE_SYMBOLS_UNIQUE.append(g)

GENE_SYMBOLS = GENE_SYMBOLS_UNIQUE


def get_gene_names(count: int, rng=None) -> list[str]:
    """Return `count` gene names. Uses real symbols if count <= 200, else generates synthetic ones."""
    if count <= len(GENE_SYMBOLS):
        if rng is not None:
            indices = rng.choice(len(GENE_SYMBOLS), size=count, replace=False)
            return [GENE_SYMBOLS[i] for i in sorted(indices)]
        return GENE_SYMBOLS[:count]
    else:
        # Extend with synthetic gene names
        names = list(GENE_SYMBOLS)
        for i in range(count - len(GENE_SYMBOLS)):
            names.append(f"GEN{i + 1:04d}")
        if rng is not None:
            rng.shuffle(names)
        return names[:count]

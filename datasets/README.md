# GenomIQ — Preloaded Datasets

## Available Datasets

### cancer_gene_expression.csv
- **Genes:** 50 cancer-related genes
- **Conditions:** 4 (Control_1, Control_2, Tumor_1, Tumor_2)
- **Description:** Simulated gene expression values for a cancer panel study. Several genes (TP53, MYC, EGFR, BRCA1) show characteristic tumor upregulation patterns.
- **Source:** Synthetic data modeled on TCGA expression profiles.

### rare_disease_panel.csv
- **Genes:** 30 genes associated with rare diseases
- **Conditions:** 3 (Healthy, Carrier, Affected)
- **Description:** Simulated expression panel for rare disease gene screening. Loss-of-function genes show progressive downregulation from Healthy→Carrier→Affected; gain-of-function genes show upregulation.
- **Source:** Synthetic data modeled on ClinVar pathogenic variant gene lists.

## CSV Format

All datasets follow this format:
- **Index column (column 0):** Gene symbols (e.g., TP53, BRCA1)
- **Data columns:** Condition labels as headers, expression values as floats
- **Values:** Log-transformed expression levels (approximate log2 scale)

## Adding Custom Datasets

Place any CSV file in this directory following the format above. It will automatically appear in the "Dataset Source" dropdown in the Gradio UI.

"""
GenomIQ — Dataset loaders for real-world gene expression data.

Supports three modes:
  - Synthetic: procedural log-normal matrices generated per episode.
  - Preloaded: curated CSV datasets shipped with the platform.
  - Custom:    user-uploaded CSV gene expression matrices.
"""

import numpy as np
import pandas as pd
from pathlib import Path

PRELOADED_DIR = Path(__file__).parent.parent / "datasets"


def load_synthetic(gene_count: int, conditions: int, rng) -> np.ndarray:
    """Generate a synthetic log-normal expression matrix."""
    return rng.lognormal(mean=3.0, sigma=1.0, size=(gene_count, conditions))


def load_preloaded(name: str) -> tuple[np.ndarray, list[str]]:
    """Load a preloaded real-world dataset.

    Args:
        name: Dataset stem name (without .csv extension).

    Returns:
        Tuple of (expression matrix, gene name list).
    """
    path = PRELOADED_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Preloaded dataset not found: {path}")
    df = pd.read_csv(path, index_col=0)
    gene_names = df.index.tolist()
    matrix = df.values.astype(float)
    return matrix, gene_names


def load_custom_csv(file_path: str) -> tuple[np.ndarray, list[str]]:
    """Load a user-uploaded CSV gene expression matrix.

    Expects CSV with gene names as the index column and
    condition/sample labels as column headers.

    Args:
        file_path: Absolute path to the uploaded CSV file.

    Returns:
        Tuple of (expression matrix, gene name list).
    """
    df = pd.read_csv(file_path, index_col=0)
    gene_names = df.index.tolist()
    matrix = df.values.astype(float)
    return matrix, gene_names


def list_preloaded_datasets() -> list[str]:
    """Return a list of available preloaded dataset names."""
    if not PRELOADED_DIR.exists():
        return []
    return [p.stem for p in sorted(PRELOADED_DIR.glob("*.csv"))]

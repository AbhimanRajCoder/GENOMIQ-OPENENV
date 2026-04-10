import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

class SummaryMetric(BaseModel):
    name: str
    weight: float
    score: float
    weighted_score: float
    passed: bool
    details: str

class Report(BaseModel):
    timestamp: str
    metrics: List[SummaryMetric]
    total_score: float
    is_ready: bool

def generate_summary(metrics: List[SummaryMetric]) -> Report:
    """Aggregates all results into a final scored report."""
    total_score = sum(m.weighted_score for m in metrics)
    is_ready = all(m.passed for m in metrics) # All metrics must pass for submission readiness

    report = Report(
        timestamp=datetime.now().isoformat(),
        metrics=metrics,
        total_score=total_score,
        is_ready=is_ready
    )

    # Console output with Rich
    console = Console()
    
    table = Table(title="OpenEnv RL Hackathon Evaluation Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Weight", style="magenta", justify="right")
    table.add_column("Score", style="green", justify="right")
    table.add_column("Weighted", style="bold green", justify="right")
    table.add_column("Status", style="yellow", justify="center")

    for m in metrics:
        status = "[bold green]PASS[/bold green]" if m.passed else "[bold red]FAIL[/bold red]"
        table.add_row(
            m.name,
            f"{m.weight*100:.0f}%",
            f"{m.score:.0f}",
            f"{m.weighted_score:.2f}",
            status
        )
    
    table.add_section()
    table.add_row(
        "TOTAL",
        "100%",
        "",
        f"[bold blue]{total_score:.2f}[/bold blue]",
        "[bold green]READY[/bold green]" if is_ready else "[bold red]FIX NEEDED[/bold red]"
    )

    console.print(table)

    if is_ready:
        console.print("\n[bold green]✅ SUBMISSION READY[/bold green]\n")
    else:
        console.print("\n[bold red]❌ NEEDS FIXES[/bold red]\n")
        # Print details for failed metrics
        for m in metrics:
            if not m.passed:
                console.print(f"[bold red]{m.name}[/bold red]: {m.details}")

    # Write JSON report
    report_dir = "tests/report"
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w") as f:
        f.write(report.model_dump_json(indent=2))
    
    console.print(f"JSON report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    # Test summary report
    dummy_metrics = [
        SummaryMetric(name="stdout_format", weight=0.15, score=92, weighted_score=13.8, passed=True, details="OK"),
        SummaryMetric(name="reward_quality", weight=0.20, score=75, weighted_score=15.0, passed=True, details="OK")
    ]
    generate_summary(dummy_metrics)

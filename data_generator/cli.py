"""CLI for synthetic data generation.

Usage:
    python -m data_generator.cli generate --profile smoke [--seed 20260716]
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_generator.config.profiles import PROFILES
from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, run_generation

app = typer.Typer(help="BOM Guardian AI synthetic ERP data generator")


@app.command()
def generate(
    profile: str = typer.Option("smoke", help=f"One of: {', '.join(PROFILES)}"),
    seed: int = typer.Option(20260716, help="Random seed (stable output per seed)"),
    output: Path = typer.Option(DEFAULT_OUTPUT_ROOT, help="Output root directory"),
) -> None:
    """Generate all synthetic datasets for a profile."""
    if profile not in PROFILES:
        raise typer.BadParameter(f"Unknown profile '{profile}'. Choose from: {list(PROFILES)}")
    manifest = run_generation(profile, seed, output)
    typer.echo(
        f"Generated {manifest['total_records']:,} records across "
        f"{len(manifest['datasets'])} datasets in {manifest['duration_seconds']}s "
        f"-> {output / profile}"
    )


@app.command()
def profiles() -> None:
    """List available data profiles."""
    for name, cfg in PROFILES.items():
        typer.echo(
            f"{name}: parts={cfg.n_parts:,} suppliers={cfg.n_suppliers:,} plants={cfg.n_plants}"
        )


if __name__ == "__main__":
    app()

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console

from .classify import explain
from .registry import Register, fetch_all, read_csv, write_csv

app = typer.Typer(help="Estimate gender from Icelandic names")
console = Console(stderr=True)

REGISTER_HELP = "A register CSV to use instead of the bundled snapshot."


def _register(path: Path | None) -> Register:
    return Register(read_csv(path))


@app.command()
def name(
    full_name: str = typer.Argument(..., help="A full name, e.g. 'Helga Ingimundardóttir'."),
    register: Path | None = typer.Option(None, "--register", help=REGISTER_HELP),
    detail: bool = typer.Option(
        False, "--detail", help="Also show what each part of the name says, and the agreement."
    ),
) -> None:
    """Estimate the gender of one name and say which rule decided."""
    ex = explain(full_name, _register(register))
    est = ex.estimate
    decided_by = f" ({est.given_name})" if est.given_name else ""
    print(f"{est.gender or 'unknown'}\t{est.rule or '-'}{decided_by}")
    if detail:
        for e in ex.evidence:
            print(f"  {e.part}\t{e.source}\t{e.says}")
        print(
            f"  agreement: {ex.agreement} (female {ex.female}, male {ex.male}, "
            f"unisex {ex.unisex}, unknown {ex.unknown})"
        )


@app.command("csv")
def csv_(
    input_path: Path = typer.Argument(..., exists=True, help="CSV with a column of full names."),
    column: str = typer.Option("name", "--column", "-c", help="The column holding the names."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Default: standard output."),
    register: Path | None = typer.Option(None, "--register", help=REGISTER_HELP),
    detail: bool = typer.Option(
        False, "--detail", help="Also add the agreement and the female/male evidence counts."
    ),
) -> None:
    """Add `gender` and `gender_rule` columns to a CSV of names."""
    reg = _register(register)
    with input_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or column not in reader.fieldnames:
            raise typer.BadParameter(f"no column {column!r} in {input_path}")
        rows = list(reader)
        fields = [*reader.fieldnames, "gender", "gender_rule"]
    if detail:
        fields += ["gender_agreement", "gender_female", "gender_male"]

    counts: Counter[str] = Counter()
    out = output.open("w", encoding="utf-8", newline="") if output else sys.stdout
    try:
        w = csv.DictWriter(out, fields)
        w.writeheader()
        for row in rows:
            ex = explain(row[column] or "", reg)
            counts[ex.estimate.gender or "unknown"] += 1
            out_row = {
                **row,
                "gender": ex.estimate.gender or "",
                "gender_rule": ex.estimate.rule or "",
            }
            if detail:
                out_row.update(
                    gender_agreement=ex.agreement, gender_female=ex.female, gender_male=ex.male
                )
            w.writerow(out_row)
    finally:
        if output:
            out.close()
    console.print(f"[green]{len(rows)} names:[/green] {dict(counts)}")


@app.command("registry-fetch")
def registry_fetch(
    output: Path = typer.Option(
        Path("mannanafnaskra.csv"), "--output", "-o", help="Where to write the register."
    ),
) -> None:
    """Fetch the whole register from island.is (about 30 requests, under a minute)."""

    def progress(i: int, n: int, letter: str, count: int) -> None:
        console.print(f"  [{i}/{n}] {letter!r}: {count} unique so far")

    entries = fetch_all(on_progress=progress)
    write_csv(entries, output)
    console.print(f"[green]{len(entries)} entries written to {output}[/green]")

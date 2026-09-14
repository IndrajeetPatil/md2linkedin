"""Compare standalone pytest-codspeed walltime reports without a hosted service."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any

CODSPEED_VERSION = "5.0.3"


def read_report(path: Path) -> dict[str, float]:
    """Validate a CodSpeed report and return per-benchmark median nanoseconds.

    Returns:
        Benchmark IDs mapped to positive median nanoseconds.

    Raises:
        ValueError: If results are missing, incompatible, or invalid.

    """
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("creator", {}).get("version") != CODSPEED_VERSION
        or data.get("instrument", {}).get("type") != "walltime"
        or not isinstance(data.get("benchmarks"), list)
        or not data["benchmarks"]
    ):
        msg = (
            f"{path}: expected nonempty pytest-codspeed "
            f"{CODSPEED_VERSION} walltime results"
        )
        raise ValueError(msg)
    results: dict[str, float] = {}
    for benchmark in data["benchmarks"]:
        uri = benchmark["uri"]
        value = benchmark["stats"]["median_ns"]
        if not isinstance(uri, str) or not uri or uri in results:
            msg = f"{path}: invalid or duplicate benchmark: {uri!r}"
            raise ValueError(msg)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            msg = f"{path}: invalid or duplicate benchmark: {uri!r}"
            raise ValueError(msg)
        results[uri] = float(value)
    return results


def load_results(directory: Path, samples: int) -> dict[str, float]:
    """Aggregate repeated reports, requiring the same benchmarks in every sample.

    Returns:
        The median of the repeated measurements for each benchmark.

    Raises:
        ValueError: If reports are missing or benchmark sets differ.

    """
    paths = sorted(directory.glob("*/results/*.json"))
    if len(paths) != samples:
        msg = f"{directory}: expected {samples} reports, found {len(paths)}"
        raise ValueError(msg)
    reports = [read_report(path) for path in paths]
    if any(report.keys() != reports[0].keys() for report in reports[1:]):
        msg = f"{directory}: benchmark sets differ between samples"
        raise ValueError(msg)
    return {uri: median(report[uri] for report in reports) for uri in reports[0]}


def _format_table(rows: list[tuple[str, ...]]) -> list[str]:
    """Pad Markdown table columns for readable plain-text CI logs.

    Returns:
        Table lines with left-aligned labels and right-aligned numeric columns.

    """
    alignments = ("<", ">", ">", ">", "<")
    widths = [max(map(len, column)) for column in zip(*rows, strict=True)]
    lines = [
        "| "
        + " | ".join(
            f"{cell:{alignment}{width}}"
            for cell, alignment, width in zip(row, alignments, widths, strict=True)
        )
        + " |"
        for row in rows
    ]
    separator = " | ".join(
        "-" * (width - 1) + ":" if alignment == ">" else "-" * width
        for alignment, width in zip(alignments, widths, strict=True)
    )
    lines.insert(1, f"| {separator} |")
    return lines


def compare(
    baseline: dict[str, float],
    candidate: dict[str, float],
    threshold: float,
) -> tuple[str, bool]:
    """Return a Markdown comparison and whether any regression exceeds the limit.

    Returns:
        The report text and a flag indicating a performance regression.

    Raises:
        ValueError: If the two benchmark sets differ or are empty.

    """
    if not baseline or baseline.keys() != candidate.keys():
        msg = "Base and candidate must contain the same nonempty benchmark set"
        raise ValueError(msg)
    lines = [
        "## Standalone CodSpeed benchmarks",
        "",
        f"Fail when median walltime increases by more than {threshold:g}%.",
        "",
    ]
    rows: list[tuple[str, ...]] = [
        ("Benchmark", "Base (ns)", "Candidate (ns)", "Change", "Result"),
    ]
    failed = False
    for uri, before in sorted(baseline.items()):
        after = candidate[uri]
        change = (after / before - 1) * 100
        regression = after > before * (1 + threshold / 100)
        failed |= regression
        verdict = "FAIL" if regression else "PASS"
        name = uri.replace("|", "\\|")
        rows.append((
            f"`{name}`",
            f"{before:,.0f}",
            f"{after:,.0f}",
            f"{change:+.1f}%",
            verdict,
        ))
    lines.extend(_format_table(rows))
    return "\n".join(lines) + "\n", failed


def main(argv: list[str] | None = None) -> int:
    """Write the comparison and return a process exit status.

    Returns:
        Zero on success, 1 for regressions, and 2 for invalid reports.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--threshold", type=float, default=10)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.threshold) or args.threshold < 0 or args.samples < 1:
        parser.error(
            "threshold must be finite and nonnegative; samples must be positive",
        )
    try:
        report, failed = compare(
            load_results(args.baseline, args.samples),
            load_results(args.candidate, args.samples),
            args.threshold,
        )
        args.output.write_text(report, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.stderr.write(f"Invalid benchmark results: {error}\n")
        return 2
    sys.stdout.write(report)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())

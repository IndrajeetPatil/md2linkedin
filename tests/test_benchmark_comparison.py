"""Regression-gate contract tests using representative CodSpeed JSON reports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts.compare_benchmarks import compare, load_results, main, read_report

if TYPE_CHECKING:
    from pathlib import Path


def write_report(directory: Path, sample: int, value: float = 100) -> Path:
    path = directory / str(sample) / "results" / "123.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "creator": {"name": "pytest-codspeed", "version": "5.0.3"},
            "instrument": {"type": "walltime"},
            "benchmarks": [
                {
                    "uri": "tests/benchmarks/test_example.py::test_example",
                    "stats": {"median_ns": value},
                },
            ],
        }),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(("value", "failed"), [(80, False), (130, False), (131, True)])
def test_threshold(value: float, *, failed: bool) -> None:
    report, actual = compare({"example": 100}, {"example": value}, 30)
    assert actual is failed
    assert ("FAIL" if failed else "PASS") in report


def test_repeated_samples_resist_one_outlier(tmp_path: Path) -> None:
    for sample, value in enumerate([100, 101, 900], start=1):
        write_report(tmp_path, sample, value)
    assert list(load_results(tmp_path, 3).values()) == [101]


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "slow"])
def test_invalid_measurements(tmp_path: Path, value: object) -> None:
    path = write_report(tmp_path, 1)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["benchmarks"][0]["stats"]["median_ns"] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid or duplicate"):
        read_report(path)


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "mode", "version"])
def test_incompatible_reports(tmp_path: Path, mutation: str) -> None:
    path = write_report(tmp_path, 1)
    data = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "empty":
        data["benchmarks"] = []
    elif mutation == "duplicate":
        data["benchmarks"] *= 2
    elif mutation == "mode":
        data["instrument"]["type"] = "simulation"
    else:
        data["creator"]["version"] = "0.0.0"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"expected nonempty|invalid or duplicate"):
        read_report(path)


def test_missing_samples(tmp_path: Path) -> None:
    write_report(tmp_path, 1)
    with pytest.raises(ValueError, match="expected 3 reports, found 1"):
        load_results(tmp_path, 3)


def test_changed_sample_set(tmp_path: Path) -> None:
    write_report(tmp_path, 1)
    path = write_report(tmp_path, 2)
    path.write_text(
        path.read_text(encoding="utf-8").replace("test_example", "test_other"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="benchmark sets differ"):
        load_results(tmp_path, 2)


@pytest.mark.parametrize("candidate", [{}, {"other": 100}])
def test_missing_or_renamed_benchmarks(candidate: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="same nonempty benchmark set"):
        compare({"example": 100}, candidate, 30)


@pytest.mark.parametrize(("value", "exit_code"), [(100, 0), (300, 1)])
def test_cli_exit_status(tmp_path: Path, value: float, exit_code: int) -> None:
    for sample in range(1, 4):
        write_report(tmp_path / "base", sample)
        write_report(tmp_path / "candidate", sample, value)
    output = tmp_path / "comparison.md"
    assert (
        main([
            str(tmp_path / "base"),
            str(tmp_path / "candidate"),
            "--output",
            str(output),
        ])
        == exit_code
    )
    assert "Standalone CodSpeed" in output.read_text(encoding="utf-8")


def test_cli_fails_closed_on_missing_reports(tmp_path: Path) -> None:
    assert (
        main([
            str(tmp_path / "base"),
            str(tmp_path / "candidate"),
            "--output",
            str(tmp_path / "comparison.md"),
        ])
        == 2
    )

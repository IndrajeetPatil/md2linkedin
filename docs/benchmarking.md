# Benchmarking

Benchmarks use the MIT-licensed [pytest-codspeed package](https://github.com/CodSpeedHQ/pytest-codspeed)
in standalone **walltime** mode. No CodSpeed account, token, GitHub App,
hosted dashboard, CodSpeed action, or paid runner is required. The package
measures elapsed time and writes JSON locally; GitHub Actions stores the reports
as ordinary workflow artifacts. Nothing is uploaded to CodSpeed.

## Run locally

Use Python 3.14, matching CI:

```sh
uv sync --locked
make benchmark
```

Results appear in `.codspeed/local/results/`. The benchmark fixtures also run
once, with correctness assertions and without timing, during `make check-package`.

## CI regression gate

The `Benchmarks` workflow runs on pull requests, pushes to `main`, and manual
dispatch. It checks out the exact PR head and base commits (previous commit for a
push; first parent for a manual run). It runs the candidate's benchmark suite
against each source tree in the **same locked candidate environment** on one
Ubuntu runner. The import path is checked before each run. This isolates source
changes; dependency-only regressions are outside the comparison.

New runs for the same PR replace older runs. Push and manual runs each have a
unique concurrency group, so a later push cannot cancel or replace a pending
comparison and hide a regression in an earlier commit.

Each revision gets three independent runs, alternating which revision runs
first. CodSpeed warms each benchmark for one second and measures it for up to
three seconds per run. The comparator takes the median of the three
`stats.median_ns` measurements for each benchmark and fails if the candidate is
**more than 30% slower** than the base. Exactly 30% passes.

Missing reports, empty results, invalid timings, incompatible CodSpeed versions,
duplicate benchmark IDs, or mismatched benchmark sets fail the gate rather than
silently passing. The CodSpeed dependency is pinned because the comparator reads
its JSON format; validate the schema and gate tests when upgrading.

The job summary contains the measured commit SHAs and comparison table.
The `standalone-codspeed-results` artifact retains raw JSON, the comparison,
and commit SHAs for 14 days, including on regression failures.
The job uses read-only repository permissions and no secrets.

Wall-clock measurements on shared runners have noise. Three runs and the 30%
margin target substantial regressions; this does not provide CodSpeed's
instruction-count simulation or guarantee detection of small slowdowns.
Investigate the raw timings and rerun noisy results before changing the limit.
Repository branch protection must require the
`Standalone CodSpeed regression check` status if it should block merging.

## Compare revisions locally

Create a separate checkout of the baseline, then run from the candidate checkout:

```sh
git worktree add --detach ../benchmark-base origin/main
uv sync --locked
for sample in 1 2 3; do
  make benchmark BENCHMARK_SOURCE="$(cd ../benchmark-base && pwd)/src" \
    BENCHMARK_OUTPUT="$PWD/benchmark-results/base/$sample"
  make benchmark BENCHMARK_OUTPUT="$PWD/benchmark-results/candidate/$sample"
done
make benchmark-compare
```

Use an empty `benchmark-results/` directory for each comparison. Extra or stale
reports are rejected. `BENCHMARK_THRESHOLD=30` controls the allowed slowdown
percentage for `make benchmark-compare`.

To validate failure detection, temporarily add expensive work or a delay inside
a benchmarked source function on a draft PR. The benchmark assertions should
still pass, while the comparison step fails with a measured slowdown. Revert
the temporary change and require a successful run on the final PR head before
marking it ready for review.

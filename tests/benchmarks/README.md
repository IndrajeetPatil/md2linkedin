# Benchmarking

This guide is for contributors maintaining the performance regression checks.

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
**more than 5% slower** than the base. Exactly 5% passes.

Missing reports, empty results, invalid timings, incompatible CodSpeed versions,
duplicate benchmark IDs, or mismatched benchmark sets fail the gate rather than
silently passing. The CodSpeed dependency is pinned because the comparator reads
its JSON format; validate the schema and gate tests when upgrading.

The job summary contains the measured commit SHAs and comparison table.
Table columns are padded so the Markdown report also aligns in raw CI logs.
The `standalone-codspeed-results` artifact retains raw JSON, the comparison,
and commit SHAs for 14 days, including on regression failures.
The job uses read-only repository permissions and no secrets.

### Choosing the margin

The margin exists to absorb runner jitter, **not** to budget for absolute
performance. Both revisions are measured in the same job on the same runner, so
making the library faster is not in itself a reason to tighten the limit — and
it can even work against you, because a shorter measurement window averages
away less jitter.

To size the margin, measure noise rather than speed. Two sources give it
directly:

- Commits that touch only CI config or dependencies leave `src/` unchanged, so
  the whole comparison for those runs is noise. Across five such runs the worst
  reported delta was **2.7%** and the remaining nineteen were all within 1.2%.
- In any run that leaves a module alone, that module's benchmarks are a noise
  reading on real CI hardware. `test_unicode_mapping` came in at -0.1% on two
  separate runs whose changes were confined to `_converter.py`.

The 5% limit is therefore a little under twice the worst noise observed. Raw
per-sample spread within one revision can still reach 5–7% on an unlucky runner
draw; taking the median of three samples is what collapses that into the deltas
above, so do not reduce the sample count to save CI minutes.

Note that the noisiest benchmark is `test_unicode_mapping`, not the very short
`test_convert_document[post]`. The fastest benchmark is the quietest, because
auto-calibration gives it far more iterations per round. Relative noise tracks
work per measurement, not wall-clock duration.

A change that deliberately alters how conversion works can exceed the margin
without the margin being wrong. The gate compares against the base branch, so
such a pull request reports the full one-off cost of the change and then goes
quiet once it lands and the base carries the new implementation. Widening the
margin to accommodate it would hide runner jitter in every later pull request
to buy nothing in this one.

Label such a pull request `benchmark-baseline-reset` instead. The comparison
still runs and the table still reports every measured change, but the step is
allowed to fail without failing the job, so the accepted cost does not sit on
the pull request as an unexplained red cross. Record in the pull request body
what the new cost is and why it is worth paying. Reach for the label only when
the cost is the point of the change: a regression that is merely unexplained
is the gate working, not the gate misfiring.

Such a change is measured twice. The commit that lands it is compared, as a
push, against the last commit before it — which still holds the old
implementation, so it reports the same cost a second time. The push run
therefore looks the label up on the pull request the commit came from, and
honours it there too. Only that one commit is covered: the next push to `main`
compares against a base that already carries the new implementation, and a
commit pushed straight to `main` belongs to no pull request and stays gated.

On a pull request the label is read from the event payload when the run starts,
so apply it before the run you want it to affect. Re-running an existing run
replays the original payload and will not see a label added afterwards; push a
commit, or close and reopen the pull request, to get a run that does.

Note also that `test_convert_document[post]` is short enough for fixed
per-document cost to dominate it: setting up a parser and handing the document
to it does not get cheaper with a 250-byte input, so a change in that cost
shows up there several times larger than in `[long-document]`. Read the two
together before concluding where a regression comes from.

This does not provide CodSpeed's instruction-count simulation or guarantee
detection of small slowdowns. Investigate the raw timings and rerun noisy
results before changing the limit.
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
reports are rejected. `BENCHMARK_THRESHOLD=5` controls the allowed slowdown
percentage for `make benchmark-compare`.

To validate failure detection, temporarily add expensive work or a delay inside
a benchmarked source function on a draft PR. The benchmark assertions should
still pass, while the comparison step fails with a measured slowdown. Revert
the temporary change and require a successful run on the final PR head before
marking it ready for review.

# Benchmarking

The benchmarks in `tests/benchmarks/` use
[pytest-codspeed](https://github.com/CodSpeedHQ/pytest-codspeed). GitHub Actions
runs them once through the official [CodSpeed action](https://github.com/CodSpeedHQ/action)
in **CPU simulation** mode, then uploads measurements and profiles to the
[repository dashboard](https://app.codspeed.io/IndrajeetPatil/md2linkedin).

CPU simulation measures user-space CPU work, including cache and memory effects;
it does not measure elapsed time spent waiting on I/O or sleeping. These
benchmarks exercise CPU-bound operations, so they use ordinary GitHub-hosted
Ubuntu runners rather than CodSpeed's metered macro runners. See
[CodSpeed's instruments](https://codspeed.io/docs/instruments/cpu) and
[Free plan](https://codspeed.io/pricing).

## Run locally

Use Python 3.15 and uv 0.13.0 or newer, matching CI:

```sh
UV_PYTHON=3.15 uv sync --locked --dev
make benchmark
```

- Local runs check benchmark correctness without uploading results or collecting
  simulation measurements; no CodSpeed account or token is needed locally.
- The same benchmark assertions also run during `make check-package`.
- Keep parameter IDs stable so CodSpeed can match benchmarks across commits.

## CI and reports

The `Benchmarks` workflow installs the checkout's locked dependencies and calls
`make benchmark` through `CodSpeedHQ/action`. The action selects simulation mode
and uploads the results; CodSpeed handles historical baselines, comparisons,
profiles, PR comments, and performance checks.

| Trigger | Purpose |
| --- | --- |
| Pull request to `main` | Measure the PR checkout and report against the available base-branch baseline |
| Push to `main` | Record default-branch measurements for future comparisons |
| Manual dispatch | Run on the selected ref, including CodSpeed backtests |

PR runs use GitHub's default merge checkout, so they test the proposed merge
with the base branch. New runs replace older runs for the same PR; push and
manual runs keep independent concurrency groups.

Each revision is measured with its own benchmark suite and locked environment.
Changes to dependencies therefore participate in the measurements. New or
renamed benchmarks need a matching baseline before CodSpeed can compare them.
The first default-branch run establishes the initial simulation baseline; the
old standalone walltime JSON reports are not compatible baselines.

## Repository setup and authentication

1. Import this repository into CodSpeed using its
   [GitHub App](https://codspeed.io/docs/integrations/providers/github).
2. Keep both `push` and `pull_request` triggers enabled so PRs have default-branch
   measurements to compare against.
3. Inspect the workflow log for a successful upload and follow the CodSpeed
   report linked from the PR.

Authentication uses GitHub's short-lived **OIDC tokens**, generated automatically
for each benchmark job by `id-token: write`. There is no stored `CODSPEED_TOKEN`
secret to generate or rotate. The job otherwise has only `contents: read`, and
checkout does not persist Git credentials. Public fork runs can use CodSpeed's
supported tokenless upload path when OIDC is unavailable. See
[CodSpeed authentication](https://codspeed.io/docs/integrations/ci/github-actions/configuration#authentication).

## Regression policy

- Configure regression thresholds in the CodSpeed repository settings. The old
  local elapsed-time gate used a 5% slowdown margin; simulation uses a
  different metric, so review its threshold against the new baseline.
- The `Run CodSpeed benchmarks` Actions job verifies execution and upload.
  CodSpeed's separate **CodSpeed Performance Analysis** check reports regressions.
- To enforce performance before merging, require both checks in branch
  protection, replacing any required `Standalone CodSpeed regression check`.
  See [CodSpeed's performance-check setup](https://codspeed.io/docs/features/performance-checks).
- For an intentional slowdown, record the measured cost and rationale in the PR
  and acknowledge the affected benchmarks in CodSpeed. Unexplained regressions
  should be investigated rather than acknowledged to make a check pass.

The previous comparator, repeated base/candidate timing loops, local JSON
artifacts, and `make benchmark-compare` have been removed.
The `benchmark-baseline-reset` label no longer changes CI behavior; use
CodSpeed acknowledgements for intentional regressions.

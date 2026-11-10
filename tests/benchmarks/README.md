# Benchmarking

The benchmarks in `tests/benchmarks/` use
[pytest-codspeed](https://github.com/CodSpeedHQ/pytest-codspeed). GitHub Actions
runs them through the official [CodSpeed action](https://github.com/CodSpeedHQ/action)
in **CPU simulation** mode and uploads measurements and profiles to the
[repository dashboard](https://app.codspeed.io/IndrajeetPatil/md2linkedin).

CPU simulation measures user-space CPU work, including cache and memory effects,
but not time spent waiting on I/O or sleeping. The benchmarks are CPU-bound, so
they run on ordinary GitHub-hosted Ubuntu runners rather than CodSpeed's metered
macro runners. See [CodSpeed's instruments](https://codspeed.io/docs/instruments/cpu)
and [Free plan](https://codspeed.io/pricing).

## Run locally

Use Python 3.15 and uv 0.13.0 or newer, matching CI:

```sh
uv python install 3.15
UV_PYTHON=3.15 uv sync --locked --dev
make benchmark
```

- Local runs check benchmark correctness only: they collect no simulation
  measurements, upload nothing and need no CodSpeed account or token.
- The same benchmark assertions also run during `make check-package`.
- Keep parameter IDs stable so CodSpeed can match benchmarks across commits.

## CI and reports

The `Benchmarks` workflow installs Python 3.15 with `uv python install`, syncs
the locked dependencies, and runs `make benchmark` through `CodSpeedHQ/action`
in simulation mode. CodSpeed handles baselines, comparisons, profiles, PR
comments and performance checks.

| Trigger | Purpose |
| --- | --- |
| Pull request to `main` | Measure the PR's merge checkout against the base-branch baseline |
| Push to `main` | Record default-branch measurements for future comparisons |
| Manual dispatch | Run on the selected ref, including CodSpeed backtests |

- A new PR run cancels the older run for the same PR; push and manual runs
  never cancel each other.
- Each revision runs its own benchmark suite in its own locked environment, so
  dependency changes show up in the measurements.
- New or renamed benchmarks need a default-branch baseline before CodSpeed can
  compare them.

## Repository setup and authentication

1. Import this repository into CodSpeed using its
   [GitHub App](https://codspeed.io/docs/integrations/providers/github).
2. Keep both `push` and `pull_request` triggers enabled so PRs have default-branch
   measurements to compare against.
3. Check the workflow log for a successful upload and follow the CodSpeed
   report linked from the PR.

Authentication uses GitHub's short-lived **OIDC tokens**, issued to the
benchmark job through `id-token: write`, so there is no `CODSPEED_TOKEN` secret
to store or rotate. The job otherwise has only `contents: read`, and checkout
does not persist Git credentials. Public fork runs can fall back to CodSpeed's
tokenless upload when OIDC is unavailable. See
[CodSpeed authentication](https://codspeed.io/docs/integrations/ci/github-actions/configuration#authentication).

## Regression policy

- Regression thresholds live in the CodSpeed repository settings.
- The `Run CodSpeed benchmarks` Actions job verifies execution and upload;
  CodSpeed's separate **CodSpeed Performance Analysis** check reports
  regressions. To enforce performance before merging, require both checks in
  branch protection. See
  [CodSpeed's performance-check setup](https://codspeed.io/docs/features/performance-checks).
- For an intentional slowdown, record the measured cost and rationale in the PR
  and acknowledge the affected benchmarks in CodSpeed. Investigate unexplained
  regressions instead of acknowledging them to make the check pass.

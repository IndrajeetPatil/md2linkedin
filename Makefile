.PHONY: update-deps upgrade-deps format lint typecheck typecoverage audit qa hooks test-coverage mutation-test benchmark benchmark-compare build test-package check-package build-docs serve-docs help

# ANSI color codes
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
NC = \033[0m

# --------------------------------------
# Dependencies
# --------------------------------------

update-deps:
	uv lock --upgrade
	uv sync
	prek update --freeze

upgrade-deps: update-deps

# --------------------------------------
# Code Quality
# --------------------------------------

format:
	uv run add-trailing-comma --exit-zero-even-if-changed $$(git ls-files '*.py')
	uv run ruff format

lint:
	uv run ruff check --fix

typecheck:
	uv run ty check

typecoverage:
	uv run pyrefly coverage check --fail-under 100

audit:
	uv audit --no-dev --preview-features audit && uv run deptry src

qa: format lint typecheck typecoverage audit

hooks:
	prek run --all-files

# --------------------------------------
# Package Testing
# --------------------------------------

test-coverage:
	# No path argument: a path overrides ``testpaths`` and walks the whole
	# tree, which collects mutmut's copy of the suite under ``mutants/``.
	uv run coverage run -m pytest
	uv run coverage report
	uv run coverage html

# Each revision is measured in the locked environment of its own checkout, so
# a dependency change is measured along with the source that needs it.
BENCHMARK_PROJECT ?= $(CURDIR)
BENCHMARK_SOURCE ?= $(BENCHMARK_PROJECT)/src
BENCHMARK_OUTPUT ?= $(CURDIR)/.codspeed/local
BENCHMARK_THRESHOLD ?= 5

# Runs a command with the chosen source tree importable, in its environment.
BENCHMARK_RUN = PYTHONPATH="$(BENCHMARK_SOURCE)" \
	uv run --no-sync --project "$(BENCHMARK_PROJECT)"
# Guards against measuring an installed copy instead of the chosen source.
BENCHMARK_SOURCE_CHECK = import md2linkedin, pathlib; \
	path = pathlib.Path(md2linkedin.__file__).resolve().parent; \
	print("Benchmark source:", path); \
	assert path == pathlib.Path("$(BENCHMARK_SOURCE)").resolve() / "md2linkedin"

benchmark:
	$(BENCHMARK_RUN) python -c '$(BENCHMARK_SOURCE_CHECK)'
	PYTHONHASHSEED=0 CODSPEED_PROFILE_FOLDER="$(BENCHMARK_OUTPUT)" \
		$(BENCHMARK_RUN) pytest tests/benchmarks \
		--codspeed --codspeed-mode=walltime --random-order-bucket=none

benchmark-compare:
	uv run --no-sync python scripts/compare_benchmarks.py \
		benchmark-results/base benchmark-results/candidate \
		--threshold "$(BENCHMARK_THRESHOLD)" --output benchmark-results/comparison.md

mutation-test:
	rm -rf mutants/
	uv run mutmut run
	uv run mutmut results
	uv run mutmut export-cicd-stats
	@survived=$$(uv run python -c "import json, sys; sys.stdout.write(str(json.load(open('mutants/mutmut-cicd-stats.json'))['survived']))"); \
	echo "Surviving mutants: $$survived"; \
	if [ "$$survived" != "0" ]; then \
		printf "$(RED)Mutation testing failed: $$survived mutant(s) survived.$(NC)\n"; \
		exit 1; \
	fi

build:
	uv build

test-package: test-coverage

check-package: test-package qa build

# --------------------------------------
# Documentation
# --------------------------------------

build-docs:
	cp CHANGELOG.md docs/changelog.md
	uv run zensical build --strict

serve-docs: build-docs
	uv run zensical serve --strict

# --------------------------------------
# Help
# --------------------------------------

help:
	@printf "$(BLUE)Usage: make [target]$(NC)\n\n"
	@printf "$(YELLOW)Available Targets:$(NC)\n"
	@printf "$(GREEN) Dependencies:$(NC)\n"
	@printf "    $(RED)update-deps$(NC)    - Update and sync dependencies\n"
	@printf "    $(RED)upgrade-deps$(NC)   - Alias for update-deps\n\n"
	@printf "$(GREEN) Code Quality:$(NC)\n"
	@printf "    $(RED)format$(NC)        - Format code using add-trailing-comma and ruff\n"
	@printf "    $(RED)lint$(NC)          - Lint code with ruff and fix issues\n"
	@printf "    $(RED)typecheck$(NC)     - Run type checking with ty\n"
	@printf "    $(RED)typecoverage$(NC)  - Enforce 100%% type coverage with pyrefly\n"
	@printf "    $(RED)audit$(NC)         - Audit prod dependencies for vulnerabilities\n"
	@printf "    $(RED)qa$(NC)            - Run all quality checks (format, lint, typecheck, typecoverage, audit)\n"
	@printf "    $(RED)hooks$(NC)         - Run all prek pre-commit hooks\n\n"
	@printf "$(GREEN) Testing and Packaging:$(NC)\n"
	@printf "    $(RED)test-coverage$(NC) - Run tests and generate coverage report\n"
	@printf "    $(RED)mutation-test$(NC) - Run mutmut mutation testing on the source\n"
	@printf "    $(RED)benchmark$(NC)     - Run standalone CodSpeed walltime benchmarks\n"
	@printf "    $(RED)benchmark-compare$(NC) - Compare three base/candidate benchmark runs\n"
	@printf "    $(RED)build$(NC)         - Build the package\n"
	@printf "    $(RED)test-package$(NC)  - Run tests and coverage\n"
	@printf "    $(RED)check-package$(NC) - Full package check (tests, QA, build)\n\n"
	@printf "$(GREEN) Documentation:$(NC)\n"
	@printf "    $(RED)build-docs$(NC)    - Build documentation with strict validation\n"
	@printf "    $(RED)serve-docs$(NC)    - Build and serve documentation\n\n"
	@printf "$(YELLOW)Examples:$(NC)\n"
	@printf "    make $(RED)test-coverage$(NC)  # Run tests and coverage\n"
	@printf "    make $(RED)qa$(NC)             # Run all quality checks\n"
	@printf "    make $(RED)check-package$(NC)  # Run full package validation\n"
	@printf "    make $(RED)serve-docs$(NC)     # Serve documentation locally\n"

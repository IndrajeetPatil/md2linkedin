.PHONY: update-deps upgrade-deps format lint typecheck audit qa hooks test-coverage build test-package check-package serve-docs help

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
	prek auto-update

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

audit:
	uv audit --no-dev --preview-features audit

qa: format lint typecheck audit

hooks:
	prek run --all-files

# --------------------------------------
# Package Testing
# --------------------------------------

test-coverage:
	uv run coverage run -m pytest .
	uv run coverage report
	uv run coverage html

build:
	uv build

test-package: test-coverage

check-package: test-package qa build

# --------------------------------------
# Documentation
# --------------------------------------

serve-docs:
	uv run quarto render README.qmd
	cp README.md docs/index.md
	cp CHANGELOG.md docs/changelog.md
	uv run python scripts/generate_llmstxt.py
	uv run zensical build --strict
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
	@printf "    $(RED)audit$(NC)         - Audit prod dependencies for vulnerabilities\n"
	@printf "    $(RED)qa$(NC)            - Run all quality checks (format, lint, typecheck)\n"
	@printf "    $(RED)hooks$(NC)         - Run all prek pre-commit hooks\n\n"
	@printf "$(GREEN) Testing and Packaging:$(NC)\n"
	@printf "    $(RED)test-coverage$(NC) - Run tests and generate coverage report\n"
	@printf "    $(RED)build$(NC)         - Build the package\n"
	@printf "    $(RED)test-package$(NC)  - Run tests and coverage\n"
	@printf "    $(RED)check-package$(NC) - Full package check (tests, QA, build)\n\n"
	@printf "$(GREEN) Documentation:$(NC)\n"
	@printf "    $(RED)serve-docs$(NC)    - Build and serve documentation\n\n"
	@printf "$(YELLOW)Examples:$(NC)\n"
	@printf "    make $(RED)test-coverage$(NC)  # Run tests and coverage\n"
	@printf "    make $(RED)qa$(NC)             # Run all quality checks\n"
	@printf "    make $(RED)check-package$(NC)  # Run full package validation\n"
	@printf "    make $(RED)serve-docs$(NC)     # Serve documentation locally\n"

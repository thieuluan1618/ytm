# Makefile for YTM CLI project

.PHONY: help install test test-quick test-unit test-integration test-coverage clean lint format check

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies and setup development environment"
	@echo "  test          - Run full test suite with coverage"
	@echo "  test-quick    - Run tests without coverage (faster for development)"
	@echo "  test-unit     - Run only unit tests"
	@echo "  test-integration - Run only integration tests"
	@echo "  test-coverage - Generate and open coverage report"
	@echo "  lint          - Run linting with ruff"
	@echo "  format        - Format code with ruff"
	@echo "  check         - Run all checks (lint + test)"
	@echo "  clean         - Clean up generated files"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock ruff

# Run full test suite
test:
	python tests/test_runner.py full

# Run quick tests (no coverage)
test-quick:
	python tests/test_runner.py quick

# Run unit tests only
test-unit:
	python tests/test_runner.py unit

# Run integration tests only
test-integration:
	python tests/test_runner.py integration

# Generate coverage report and open it
test-coverage: test
	@echo "Opening coverage report..."
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "Coverage report generated in htmlcov/index.html"; \
	fi

# Lint code
lint:
	ruff check ytm_cli/ tests/

# Format code
format:
	ruff format ytm_cli/ tests/

# Run all checks
check: lint test

# Clean up generated files
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

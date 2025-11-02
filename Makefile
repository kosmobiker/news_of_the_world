# Simple Makefile for common dev tasks

.PHONY: fmt test

fmt:
	ruff format .

test:
	@echo "Running tests..."
	uv run python -m coverage run -m unittest discover -s tests
	uv run python -m coverage report -m

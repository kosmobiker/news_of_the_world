# Simple Makefile for common dev tasks

.PHONY: init fmt

init:
	# Set PYTHONPATH for current shell; on Windows (PowerShell) run:
	#   $env:PYTHONPATH = "."
	@echo "On Windows PowerShell run: $env:PYTHONPATH = '.'"
	@echo "Or add to your profile: $env:PYTHONPATH = '.'"

fmt:
	ruff format .

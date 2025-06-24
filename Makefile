.PHONY: help setup analyze search test build

help:
	@echo "  make setup    - Initial setup"
	@echo "  make analyze  - Analyze current directory"
	@echo "  make search   - Search code (QUERY='...')"
	@echo "  make test     - Run tests"
	@echo "  make build    - Build package"

setup:
	hatch env create

analyze:
	hatch run analyze . --save

search:
	hatch run search "$(QUERY)"

search:
	hatch run summary

test:
	hatch run test

build:
	hatch build

.PHONY: help test data

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

test: ## run all tests
	uv run pytest -q

data: ## download pinned dataset to data/raw/
	uv run python -m shellguard.data

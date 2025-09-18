# Battery Cost Forecast Makefile

.PHONY: help install run fetch build streamlit clean

help: ## Show this help message
	@echo "Battery Cost Forecast - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

fetch: ## Fetch price data from TradingEconomics
	python scripts/fetch_prices_te.py

build: ## Build forecasts and compute chemistry costs
	python scripts/build_forecasts.py

streamlit: ## Launch Streamlit dashboard
	streamlit run app/app.py

run: fetch build streamlit ## Run full pipeline: fetch -> build -> streamlit

clean: ## Clean generated files
	rm -rf processed/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete


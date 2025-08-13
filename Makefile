# Makefile for Legal Research Assistant Verification

.PHONY: verify setup install-deps generate-docs clean help

# Default target
help:
	@echo "Legal Research Assistant Verification"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  verify        - Run full verification suite"
	@echo "  setup         - Set up verification environment"
	@echo "  install-deps  - Install verification dependencies"
	@echo "  generate-docs - Generate sample documents only"
	@echo "  clean         - Clean up generated files"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make verify                    # Run with default settings"
	@echo "  make verify APP_URL=http://localhost:8502"
	@echo "  make setup && make verify      # Full setup and verification"

# Configuration
APP_URL ?= http://localhost:8501
DOCS_PATH ?= verification/sample_docs
VENV_PATH ?= venv
PYTHON ?= python

# Install verification dependencies
install-deps:
	@echo "📦 Installing verification dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install pytest pyyaml requests python-docx fpdf2 rapidfuzz
	@echo "✅ Dependencies installed"

# Generate sample documents
generate-docs:
	@echo "📄 Generating sample legal documents..."
	$(PYTHON) verification/scripts/generate_docs.py $(DOCS_PATH)
	@echo "✅ Sample documents generated"

# Set up verification environment
setup: install-deps generate-docs
	@echo "🔧 Setting up verification environment..."
	@mkdir -p verification/sample_docs
	@mkdir -p logs
	@echo "✅ Environment setup complete"

# Run verification suite
verify: setup
	@echo "🧪 Running Legal Research Assistant verification..."
	@echo "📍 App URL: $(APP_URL)"
	@echo "📁 Docs path: $(DOCS_PATH)"
	@echo ""
	$(PYTHON) verification/scripts/verify_assignment.py \
		--app-url $(APP_URL) \
		--docs $(DOCS_PATH) \
		--out verification/REPORT.md \
		--json verification/report.json
	@echo ""
	@echo "📊 Verification complete! Check verification/REPORT.md for results."

# Quick verification (skip heavy tests)
verify-quick: setup
	@echo "🚀 Running quick verification (lightweight tests only)..."
	$(PYTHON) verification/scripts/verify_assignment.py \
		--app-url $(APP_URL) \
		--docs $(DOCS_PATH) \
		--out verification/REPORT.md \
		--json verification/report.json \
		--quick
	@echo "📊 Quick verification complete!"

# Run specific test categories
test-smoke:
	$(PYTHON) -m pytest verification/tests/test_app_smoke.py -v

test-retrieval:
	$(PYTHON) -m pytest verification/tests/test_retrieval_metrics.py -v

test-citations:
	$(PYTHON) -m pytest verification/tests/test_citations_and_conflicts.py -v

test-latency:
	$(PYTHON) -m pytest verification/tests/test_latency.py -v

test-dataset:
	$(PYTHON) -m pytest verification/tests/test_dataset.py -v

# Clean up generated files
clean:
	@echo "🧹 Cleaning up verification files..."
	@rm -rf verification/sample_docs/*.pdf
	@rm -rf verification/sample_docs/*.docx
	@rm -rf verification/sample_docs/*.txt
	@rm -f verification/REPORT.md
	@rm -f verification/report.json
	@rm -rf verification/__pycache__
	@rm -rf verification/tests/__pycache__
	@rm -rf verification/scripts/__pycache__
	@echo "✅ Cleanup complete"

# Development targets
dev-setup: setup
	$(PYTHON) -m pip install pytest-watch black flake8
	@echo "✅ Development environment ready"

watch-tests:
	$(PYTHON) -m pytest_watch verification/tests/ --runner "python -m pytest" --patterns="*.py"

format:
	black verification/
	@echo "✅ Code formatted"

lint:
	flake8 verification/ --max-line-length=100 --ignore=E203,W503
	@echo "✅ Linting complete"

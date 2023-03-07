# Common commands for easier development

# Default: Do nothing
.PHONY: all
all:

# Make docs and serve it as a webpage
.PHONY: doc
doc:
	(cd docs && make html && make serve)

# For quickly cleaning up files
.PHONY: clean
clean:
	rm -rf .mjolnir*
	rm -rf kvs_dump*
	rm -rf debugging/
	(cd docs && make clean)

# Clean everything
.PHONY: purge
purge: clean
	rm -rf db/

# Runs formatters
.PHONY: format
format:
	@echo "=========="
	@echo "Formatting"
	@echo "=========="
	isort .
	black .
	@echo ""

# Runs linters
.PHONY: lint
lint:
	@echo "======="
	@echo "Linting"
	@echo "======="
	flake8 .
	pylint *.py tests src/resonaate docs
	@echo ""

# Runs unit tests
.PHONY: test
test:
	@echo "=========="
	@echo "Unit Tests"
	@echo "=========="
	pytest -ra -m "not (regression or integration)"
	@echo ""

# Runs coverage with unit tests
.PHONY: coverage
coverage:
	@echo "=================="
	@echo "Unit Test Coverage"
	@echo "=================="
	pytest --cov -ra -m "not (regression or integration)"
	@echo ""

# Runs integration tests
.PHONY: test_integration
test_integration:
	@echo "================="
	@echo "Integration Tests"
	@echo "================="
	pytest -ra -m "integration"
	@echo ""

# Runs regression tests
.PHONY: test_regression
test_regression:
	@echo "================"
	@echo "Regression Tests"
	@echo "================"
	pytest -ra -m "regression"
	@echo ""

# Runs all tests
.PHONY: test_all
test_all: test test_integration test_regression

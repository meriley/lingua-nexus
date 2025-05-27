# Lingua Nexus - Single-Model Architecture Build System
# Auto-discovery and pattern-based build automation for translation models

.PHONY: help build\% docker\% dist\% test\% clean\% list-models validate-model install-deps

# Configuration
VERSION ?= latest
REGISTRY ?= lingua-nexus
PYTHON ?= python3
PIP ?= pip3

# Auto-discover available models (exclude base, template, and cache directories)
MODELS := $(shell find models/ -maxdepth 1 -type d -name '*' ! -name 'base' ! -name 'template' ! -name 'models' ! -name '__pycache__' | sed 's|models/||' | sort)

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# Default target
.DEFAULT_GOAL := help

## Display help information
help:
	@echo "$(BLUE)Lingua Nexus - Single-Model Build System$(RESET)"
	@echo ""
	@echo "$(YELLOW)Available Commands:$(RESET)"
	@echo "  $(GREEN)build:<model>$(RESET)      - Build model dependencies and validate loading"
	@echo "  $(GREEN)docker:<model>$(RESET)     - Build Docker image for model (CPU variant)"
	@echo "  $(GREEN)docker-gpu:<model>$(RESET) - Build GPU-optimized Docker image"
	@echo "  $(GREEN)docker-rocm:<model>$(RESET)- Build ROCm-optimized Docker image (AMD GPUs)"
	@echo "  $(GREEN)docker-all:<model>$(RESET) - Build all Docker variants (CPU/GPU/ROCm)"
	@echo "  $(GREEN)dist:<model>$(RESET)       - Create distribution package for model"
	@echo "  $(GREEN)test:<model>$(RESET)       - Run tests for specific model"
	@echo "  $(GREEN)test-integration$(RESET)   - Run all integration tests"
	@echo "  $(GREEN)test-integration:<model>$(RESET) - Run integration tests for specific model"
	@echo "  $(GREEN)clean:<model>$(RESET)      - Clean artifacts for model"
	@echo "  $(GREEN)list-models$(RESET)        - List all available models"
	@echo "  $(GREEN)validate-model$(RESET)     - Validate model structure"
	@echo ""
	@echo "$(YELLOW)Available Models:$(RESET)"
	@if [ "$(MODELS)" = "" ]; then \
		echo "  $(RED)No models found in models/ directory$(RESET)"; \
	else \
		for model in $(MODELS); do \
			echo "  - $$model"; \
		done; \
	fi
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make build:aya-expanse-8b"
	@echo "  make docker:nllb"
	@echo "  make docker-gpu:aya-expanse-8b"
	@echo "  make docker-all:nllb"
	@echo "  make test:all"
	@echo "  make test-integration"
	@echo "  make test-integration:aya-expanse-8b"
	@echo "  make clean:aya-expanse-8b"
	@echo ""

## List all available models
list-models:
	@echo "$(BLUE)Available Models:$(RESET)"
	@if [ "$(MODELS)" = "" ]; then \
		echo "$(RED)No models found$(RESET)"; \
		exit 1; \
	else \
		for model in $(MODELS); do \
			if [ -f "models/$$model/model.py" ]; then \
				echo "  $(GREEN)✓$(RESET) $$model"; \
			else \
				echo "  $(RED)✗$(RESET) $$model (incomplete)"; \
			fi; \
		done; \
	fi

## Build model dependencies and validate loading
build\:%:
	@model=$*; \
	echo "$(BLUE)Building model: $$model$(RESET)"; \
	if [ ! -d "models/$$model" ]; then \
		echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
		exit 1; \
	fi; \
	if [ ! -f "models/$$model/requirements.txt" ]; then \
		echo "$(RED)Error: requirements.txt not found for $$model$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Installing dependencies...$(RESET)"; \
	cd models/$$model && $(PIP) install -r requirements.txt; \
	echo "$(YELLOW)Validating model loading...$(RESET)"; \
	cd server && $(PYTHON) -c "import sys; sys.path.append('..'); import importlib; mod = importlib.import_module('models.$$model'); print('$(GREEN)✓ Model loads successfully$(RESET)')"; \
	echo "$(GREEN)Build completed for $$model$(RESET)"

## Build Docker image for model (default: CPU variant)
docker\:%:
	@model=$*; \
	echo "$(BLUE)Building Docker image for model: $$model (CPU variant)$(RESET)"; \
	if [ ! -d "models/$$model" ]; then \
		echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
		exit 1; \
	fi; \
	if [ ! -f "models/$$model/Dockerfile" ]; then \
		echo "$(RED)Error: Dockerfile not found for $$model$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Building Docker image with CPU support...$(RESET)"; \
	docker build -f models/$$model/Dockerfile \
		--build-arg VARIANT=cpu \
		-t $(REGISTRY)-$$model:$(VERSION) \
		-t $(REGISTRY)-$$model:latest \
		-t $(REGISTRY)-$$model:cpu .; \
	echo "$(GREEN)Docker image built: $(REGISTRY)-$$model:$(VERSION)$(RESET)"

## Build GPU-optimized Docker image for model
docker-gpu\:%:
	@model=$*; \
	echo "$(BLUE)Building GPU Docker image for model: $$model$(RESET)"; \
	if [ ! -d "models/$$model" ]; then \
		echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
		exit 1; \
	fi; \
	if [ ! -f "models/$$model/Dockerfile" ]; then \
		echo "$(RED)Error: Dockerfile not found for $$model$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Building Docker image with GPU support...$(RESET)"; \
	docker build -f models/$$model/Dockerfile \
		--build-arg VARIANT=gpu \
		-t $(REGISTRY)-$$model:$(VERSION)-gpu \
		-t $(REGISTRY)-$$model:gpu .; \
	echo "$(GREEN)GPU Docker image built: $(REGISTRY)-$$model:$(VERSION)-gpu$(RESET)"

## Build ROCm-optimized Docker image for model (AMD GPUs)
docker-rocm\:%:
	@model=$*; \
	echo "$(BLUE)Building ROCm Docker image for model: $$model$(RESET)"; \
	if [ ! -d "models/$$model" ]; then \
		echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
		exit 1; \
	fi; \
	if [ ! -f "models/$$model/Dockerfile" ]; then \
		echo "$(RED)Error: Dockerfile not found for $$model$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Building Docker image with ROCm support...$(RESET)"; \
	docker build -f models/$$model/Dockerfile \
		--build-arg VARIANT=rocm \
		-t $(REGISTRY)-$$model:$(VERSION)-rocm \
		-t $(REGISTRY)-$$model:rocm .; \
	echo "$(GREEN)ROCm Docker image built: $(REGISTRY)-$$model:$(VERSION)-rocm$(RESET)"

## Build all Docker variants for model
docker-all\:%:
	@model=$*; \
	echo "$(BLUE)Building all Docker variants for model: $$model$(RESET)"; \
	$(MAKE) docker:$$model; \
	$(MAKE) docker-gpu:$$model; \
	$(MAKE) docker-rocm:$$model; \
	echo "$(GREEN)All Docker variants built for $$model$(RESET)"

## Create distribution package for model
dist\:%:
	@model=$*; \
	echo "$(BLUE)Creating distribution for model: $$model$(RESET)"; \
	if [ ! -d "models/$$model" ]; then \
		echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Creating distribution directory...$(RESET)"; \
	mkdir -p dist/$$model; \
	echo "$(YELLOW)Copying model files...$(RESET)"; \
	cp -r models/$$model dist/$$model/model; \
	cp -r server dist/$$model/; \
	cp -r models/base dist/$$model/models/; \
	echo "$(YELLOW)Creating tarball...$(RESET)"; \
	cd dist/$$model && tar -czf ../lingua-nexus-$$model-$(VERSION).tar.gz .; \
	echo "$(GREEN)Distribution created: dist/lingua-nexus-$$model-$(VERSION).tar.gz$(RESET)"

## Run tests for specific model
test\:%:
	@model=$*; \
	if [ "$$model" = "all" ]; then \
		echo "$(BLUE)Running tests for all models$(RESET)"; \
		echo "$(YELLOW)Running base interface tests$(RESET)"; \
		cd server && $(PYTHON) -m pytest tests/unit/models/test_base_interface.py -v; \
		for m in $(MODELS); do \
			test_file=""; \
			if [ "$$m" = "aya-expanse-8b" ]; then \
				test_file="test_aya_expanse_8b.py"; \
			elif [ "$$m" = "nllb" ]; then \
				test_file="test_nllb.py"; \
			fi; \
			if [ -n "$$test_file" ] && [ -f "server/tests/unit/models/$$test_file" ]; then \
				echo "$(YELLOW)Testing model: $$m$(RESET)"; \
				cd server && $(PYTHON) -m pytest tests/unit/models/$$test_file -v; \
			else \
				echo "$(YELLOW)No unit tests found for $$m$(RESET)"; \
			fi; \
		done; \
		echo "$(YELLOW)Running adaptive component tests$(RESET)"; \
		cd server && $(PYTHON) -m pytest tests/unit/adaptive/ -v; \
	else \
		echo "$(BLUE)Testing model: $$model$(RESET)"; \
		if [ ! -d "models/$$model" ]; then \
			echo "$(RED)Error: Model directory models/$$model not found$(RESET)"; \
			exit 1; \
		fi; \
		test_file=""; \
		if [ "$$model" = "aya-expanse-8b" ]; then \
			test_file="test_aya_expanse_8b.py"; \
		elif [ "$$model" = "nllb" ]; then \
			test_file="test_nllb.py"; \
		fi; \
		if [ -n "$$test_file" ] && [ -f "server/tests/unit/models/$$test_file" ]; then \
			echo "$(YELLOW)Running unit tests for $$model$(RESET)"; \
			cd server && $(PYTHON) -m pytest tests/unit/models/$$test_file -v; \
		else \
			echo "$(YELLOW)No unit tests found for $$model$(RESET)"; \
		fi; \
		integration_test_file=""; \
		if [ "$$model" = "aya-expanse-8b" ]; then \
			integration_test_file="test_aya_expanse_8b_integration.py"; \
		elif [ "$$model" = "nllb" ]; then \
			integration_test_file="test_nllb_integration.py"; \
		fi; \
		if [ -n "$$integration_test_file" ] && [ -f "server/tests/integration/$$integration_test_file" ]; then \
			echo "$(YELLOW)Running integration tests for $$model$(RESET)"; \
			cd server && $(PYTHON) -m pytest tests/integration/$$integration_test_file -v; \
		else \
			echo "$(YELLOW)No integration tests found for $$model$(RESET)"; \
		fi; \
		if [ -f "server/tests/integration/test_single_model_api.py" ]; then \
			echo "$(YELLOW)Running core single-model API tests$(RESET)"; \
			cd server && $(PYTHON) -m pytest tests/integration/test_single_model_api.py -v; \
		fi; \
	fi; \
	echo "$(GREEN)Testing completed$(RESET)"

## Clean artifacts for model
clean\:%:
	@model=$*; \
	if [ "$$model" = "all" ]; then \
		echo "$(BLUE)Cleaning all artifacts$(RESET)"; \
		rm -rf dist/*; \
		for m in $(MODELS); do \
			docker rmi $(REGISTRY)-$$m:latest $(REGISTRY)-$$m:$(VERSION) $(REGISTRY)-$$m:cpu 2>/dev/null || true; \
			docker rmi $(REGISTRY)-$$m:$(VERSION)-gpu $(REGISTRY)-$$m:gpu 2>/dev/null || true; \
			docker rmi $(REGISTRY)-$$m:$(VERSION)-rocm $(REGISTRY)-$$m:rocm 2>/dev/null || true; \
		done; \
	else \
		echo "$(BLUE)Cleaning artifacts for model: $$model$(RESET)"; \
		rm -rf dist/$$model; \
		rm -f dist/lingua-nexus-$$model-*.tar.gz; \
		docker rmi $(REGISTRY)-$$model:latest $(REGISTRY)-$$model:$(VERSION) $(REGISTRY)-$$model:cpu 2>/dev/null || true; \
		docker rmi $(REGISTRY)-$$model:$(VERSION)-gpu $(REGISTRY)-$$model:gpu 2>/dev/null || true; \
		docker rmi $(REGISTRY)-$$model:$(VERSION)-rocm $(REGISTRY)-$$model:rocm 2>/dev/null || true; \
	fi; \
	echo "$(GREEN)Cleanup completed$(RESET)"

## Validate model directory structure
validate-model:
	@if [ "$(MODELS)" = "" ]; then \
		echo "$(RED)No models found to validate$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(BLUE)Validating model structures$(RESET)"; \
	for model in $(MODELS); do \
		echo "$(YELLOW)Validating $$model...$(RESET)"; \
		error=0; \
		if [ ! -f "models/$$model/model.py" ]; then \
			echo "  $(RED)✗ Missing model.py$(RESET)"; \
			error=1; \
		else \
			echo "  $(GREEN)✓ model.py$(RESET)"; \
		fi; \
		if [ ! -f "models/$$model/config.py" ]; then \
			echo "  $(RED)✗ Missing config.py$(RESET)"; \
			error=1; \
		else \
			echo "  $(GREEN)✓ config.py$(RESET)"; \
		fi; \
		if [ ! -f "models/$$model/requirements.txt" ]; then \
			echo "  $(RED)✗ Missing requirements.txt$(RESET)"; \
			error=1; \
		else \
			echo "  $(GREEN)✓ requirements.txt$(RESET)"; \
		fi; \
		if [ ! -f "models/$$model/Dockerfile" ]; then \
			echo "  $(RED)✗ Missing Dockerfile$(RESET)"; \
			error=1; \
		else \
			echo "  $(GREEN)✓ Dockerfile$(RESET)"; \
		fi; \
		if [ $$error -eq 0 ]; then \
			echo "  $(GREEN)✓ $$model structure valid$(RESET)"; \
		else \
			echo "  $(RED)✗ $$model structure incomplete$(RESET)"; \
		fi; \
	done

## Install development dependencies
install-deps:
	@echo "$(BLUE)Installing development dependencies$(RESET)"
	$(PIP) install -r server/requirements-dev.txt
	@echo "$(GREEN)Development dependencies installed$(RESET)"

## Development targets
.PHONY: dev-setup lint format type-check

## Set up development environment
dev-setup: install-deps
	@echo "$(BLUE)Setting up development environment$(RESET)"
	@echo "$(GREEN)Development environment ready$(RESET)"

## Run linting
lint:
	@echo "$(BLUE)Running linting$(RESET)"
	cd server && flake8 app/ tests/
	@echo "$(GREEN)Linting completed$(RESET)"

## Format code
format:
	@echo "$(BLUE)Formatting code$(RESET)"
	cd server && black app/ tests/
	@echo "$(GREEN)Code formatted$(RESET)"

## Run type checking
type-check:
	@echo "$(BLUE)Running type checking$(RESET)"
	cd server && mypy app/
	@echo "$(GREEN)Type checking completed$(RESET)"

## Run all integration tests
test-integration:
	@echo "$(BLUE)Running all integration tests$(RESET)"
	cd server && $(PYTHON) -m pytest tests/integration/ -v
	@echo "$(GREEN)All integration tests completed$(RESET)"

## Run integration tests for specific model
test-integration\:%:
	@model=$*; \
	echo "$(BLUE)Running integration tests for: $$model$(RESET)"; \
	if [ "$$model" = "all" ]; then \
		cd server && $(PYTHON) -m pytest tests/integration/ -v; \
	else \
		integration_test_file=""; \
		if [ "$$model" = "aya-expanse-8b" ]; then \
			integration_test_file="test_aya_expanse_8b_integration.py"; \
		elif [ "$$model" = "nllb" ]; then \
			integration_test_file="test_nllb_integration.py"; \
		elif [ "$$model" = "api" ]; then \
			integration_test_file="test_single_model_api.py"; \
		fi; \
		if [ -n "$$integration_test_file" ] && [ -f "server/tests/integration/$$integration_test_file" ]; then \
			echo "$(YELLOW)Running $$integration_test_file$(RESET)"; \
			cd server && $(PYTHON) -m pytest tests/integration/$$integration_test_file -v; \
		else \
			echo "$(RED)Integration test file not found for $$model$(RESET)"; \
			exit 1; \
		fi; \
	fi; \
	echo "$(GREEN)Integration tests completed for $$model$(RESET)"
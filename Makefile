# Common tasks for developing against the Windows VM (see README.md).
#
#   make help
#   make vm-up | vm-restart | vm-logs | vm-health ...
#
# VM_DIR is the folder holding the Vagrantfile; override if it is elsewhere:
#   make vm-restart VM_DIR=~/somewhere/windows10-vm
VM_DIR   ?= ../windows10-vm
SERVICE  ?= vs_data_api
VM_URL   ?= http://127.0.0.1:8080
LOG_LINES ?= 40

# Run a PowerShell command in the VM
WINRM = cd "$(VM_DIR)" && vagrant winrm -c

.DEFAULT_GOAL := help
.PHONY: help vm-up vm-halt vm-status vm-restart vm-logs vm-out vm-health vm-ports vm-env run test smoke

help: ## List the available tasks
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

vm-up: ## Start the VM (vagrant up)
	cd "$(VM_DIR)" && vagrant up

vm-halt: ## Shut the VM down
	cd "$(VM_DIR)" && vagrant halt

vm-status: ## VM state and the vs-data-api service state
	cd "$(VM_DIR)" && vagrant status
	@$(WINRM) 'nssm status $(SERVICE)'

vm-restart: ## Restart the API service in the VM (do this after changing .env or dependencies)
	@$(WINRM) 'nssm restart $(SERVICE)'

vm-logs: ## Tail the uvicorn log (C:\logs\vs_data_api_err.log) in the VM
	@$(WINRM) 'Get-Content C:\logs\$(SERVICE)_err.log -Tail $(LOG_LINES)'

vm-out: ## Tail the service stdout log in the VM
	@$(WINRM) 'Get-Content C:\logs\$(SERVICE)_out.log -Tail $(LOG_LINES)'

vm-health: ## Call /health on the VM's API (FileMaker, link db and WooCommerce); non-zero if degraded
	@tmp=$$(mktemp); \
	code=$$(curl -sS -m 60 -o "$$tmp" -w '%{http_code}' "$(VM_URL)/health") || { \
	  echo "VM API not reachable at $(VM_URL) (is the VM up and the service running? make vm-status)"; rm -f "$$tmp"; exit 1; }; \
	python3 -m json.tool "$$tmp" 2>/dev/null || cat "$$tmp"; rm -f "$$tmp"; \
	[ "$$code" = "200" ] || { echo "HTTP $$code: degraded"; exit 1; }

vm-ports: ## Show the VM's forwarded ports
	@cd "$(VM_DIR)" && vagrant port

run: ## Run the API locally on :8000 (needs a working local FileMaker, see README)
	uv run uvicorn src.vs_data_api.main:app --reload

test: ## Run the tests that need no FileMaker or WooCommerce
	uv run --extra test pytest

smoke: ## Run the smoke tests (every endpoint and CLI command starts)
	uv run --extra test pytest tests/smoke

doctor: ## Run vsdata-doctor locally (Windows-only checks are skipped elsewhere)
	uv run python -m vs_doctor

VENV := $(shell echo $${VIRTUAL_ENV-.venv})
INSTALL_STAMP = $(VENV)/.install.stamp

.PHONY: help
help:
	@echo "Usage: make RULE"
	@echo ""
	@echo " clean  - clean local cache folders"
	@echo " format - run formatters (ruff, black), fix in place"
	@echo " lint   - run linters"
	@echo " test   - run test suite"
	@echo ""
	@echo " help   - see this text"

.PHONY: clean
clean:
	$(VENV)/bin/ruff clean
	find . -name "__pycache__" | xargs rm -rf
	rm -rf .pytest_cache

$(VENV):
	python3 -m venv $(VENV)
	
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): requirements.txt
	$(VENV)/bin/pip install -r requirements.txt
	touch $(INSTALL_STAMP)

.PHONY: format
format: $(INSTALL_STAMP)
	$(VENV)/bin/ruff --fix review_pr.py
	$(VENV)/bin/black review_pr.py

.PHONY: lint
lint: $(INSTALL_STAMP)
	$(VENV)/bin/black --check review_pr.py
	$(VENV)/bin/ruff review_pr.py

.PHONY: test
test: $(INSTALL_STAMP)
	$(VENV)/bin/pytest .
